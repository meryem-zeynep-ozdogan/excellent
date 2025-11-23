# qr.py
# -*- coding: utf-8 -*-

import os
import logging
import json
import re
import time
import warnings
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# QR işleme için uyarıları kapat
warnings.filterwarnings("ignore")


class FastQRProcessor:
    """HIZLI VE MİNİMAL QR İşlemci"""
    
    def __init__(self):
        # self.opencv_detector = cv2.QRCodeDetector() <-- Hata verdiği için bu da taşındı
        pass # Başlangıçta QR ile ilgili hiçbir şey yükleme
    
    def _init_qr_tools(self):
        """QR araçlarını sadece gerektiğinde yükler."""
        try:
            global cv2, pyzbar, fitz
            import cv2
            from pyzbar import pyzbar
            import fitz  # PyMuPDF
            
            # OpenCV optimizasyonları
            cv2.setNumThreads(6)  # Thread sayısını artır
            cv2.setUseOptimized(True)
            
            # QR detektörü oluştur
            self.opencv_detector = cv2.QRCodeDetector()
            
            # Başarılı yükleme için flag
            self.tools_loaded = True
            logging.info("🔧 QR araçları başarıyla yüklendi (OpenCV, PyZBar, PyMuPDF)")
            
        except ImportError as e:
            self.tools_loaded = False
            logging.error(f"❌ QR araçları yüklenemedi: {e}")
            logging.error("Lütfen şu kütüphaneleri kurun: pip install opencv-python-headless pyzbar PyMuPDF")
            raise ImportError("QR işleme kütüphaneleri eksik!")
    
    def clean_json(self, qr_text):
        """GELİŞTİRİLMİŞ JSON TEMİZLEME VE AYRIŞTIRMA"""
        if not qr_text or len(qr_text.strip()) < 5:
            logging.warning("⚠️ QR verisi çok kısa veya boş")
            return {}
        
        original_text = qr_text
        cleaned = qr_text.strip()
        
        logging.debug(f"🧹 JSON temizleme başlıyor... ({len(cleaned)} karakter)")
        
        # === 1. TEMEL TEMİZLEME ===
        # Kontrol karakterlerini temizle
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        # Hex escape karakterleri
        cleaned = re.sub(r'\\x[0-9a-fA-F]{2}', '', cleaned)
        # Fazla boşlukları temizle
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Sondaki virgülleri düzelt
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        
        # === 2. JSON PARSE DENEMELERİ ===
        parse_attempts = [
            ("Orijinal", cleaned),
            ("Tek Tırnak Dönüşümü", cleaned.replace("'", '"')),
            ("Çift Tırnak Normalizasyon", re.sub(r'("|")', '"', cleaned)),
            ("Unicode Tırnak Temizleme", re.sub(r'[''‚›‛′‵]', "'", cleaned).replace("'", '"')),
        ]
        
        for attempt_name, attempt_text in parse_attempts:
            try:
                parsed = json.loads(attempt_text)
                if isinstance(parsed, dict) and len(parsed) > 0:
                    logging.info(f"✅ JSON başarıyla ayrıştırıldı ({attempt_name}): {len(parsed)} anahtar")
                    return parsed
                elif isinstance(parsed, list) and len(parsed) > 0:
                    logging.info(f"✅ JSON array ayrıştırıldı ({attempt_name}): {len(parsed)} öğe")
                    # Array ise ilk öğeyi al (eğer dict ise)
                    if isinstance(parsed[0], dict):
                        return parsed[0]
                    else:
                        return {'array_data': parsed}
            except json.JSONDecodeError as e:
                logging.debug(f"🔍 {attempt_name} parse hatası: {str(e)[:100]}")
                continue
            except Exception as e:
                logging.debug(f"🔍 {attempt_name} genel hata: {e}")
                continue
        
        # === 3. MANUEL KEY-VALUE EXTRACTION ===
        logging.debug("🔧 Manuel key-value çıkarma başlıyor...")
        try:
            kv_pairs = {}
            
            # Gelişmiş regex pattern
            patterns = [
                r'["\']?([a-zA-Z_]\w*)["\']?\s*:\s*["\']?([^,"}\]\n]+)["\']?',  # Standard key:value
                r'([a-zA-Z_]\w*)\s*[:=]\s*([^,\n\r;]+)',  # key=value or key:value
                r'"([^"]+)"\s*:\s*"([^"]+)"',  # "key":"value"
                r"'([^']+)'\s*:\s*'([^']+)'",  # 'key':'value'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, cleaned, re.MULTILINE | re.IGNORECASE)
                for key, value in matches:
                    if key and value:
                        # Değeri temizle
                        clean_key = key.strip()
                        clean_value = value.strip().strip('"').strip("'").strip()
                        
                        if clean_key and clean_value and len(clean_value) > 0:
                            kv_pairs[clean_key] = clean_value
            
            # Sayısal değerleri tespit et ve çevir
            for key, value in kv_pairs.items():
                if re.match(r'^\d+(\.\d+)?$', str(value)):
                    try:
                        if '.' in str(value):
                            kv_pairs[key] = float(value)
                        else:
                            kv_pairs[key] = int(value)
                    except:
                        pass  # String olarak kalsın
            
            if len(kv_pairs) > 0:
                logging.info(f"⚠️ Manuel ayrıştırma başarılı: {len(kv_pairs)} anahtar")
                kv_pairs['_parse_method'] = 'manual_extraction'
                return kv_pairs
        except Exception as e:
            logging.warning(f"⚠️ Manuel ayrıştırma hatası: {e}")
        
        # === 4. URL DECODE DENEME ===
        try:
            import urllib.parse
            url_decoded = urllib.parse.unquote(cleaned)
            if url_decoded != cleaned:
                logging.debug("🔗 URL decode deneniyor...")
                parsed = json.loads(url_decoded)
                if isinstance(parsed, dict) and len(parsed) > 0:
                    logging.info("✅ URL decode ile JSON başarılı")
                    return parsed
        except Exception:
            pass
        
        # === 5. BAŞARISIZLIK DURUMU ===
        logging.error("❌ Tüm JSON ayrıştırma yöntemleri başarısız!")
        logging.error(f"📄 Ham QR verisi (ilk 200 karakter): {original_text[:200]}...")
        
        # Son çare: Ham veriyi geri döndür
        return {
            "_parse_error": "JSON ayrıştırma başarısız",
            "_raw_data": original_text,
            "_cleaned_data": cleaned[:500],
            "_data_length": len(original_text)
        }
    
    def scan_qr_fast(self, img):
        """
        PERFORMANS-BAŞARI DENGELİ QR TARAMA
        Hızlı ama kapsamlı QR okuma algoritması
        """
        # Araçları yükle
        if not hasattr(self, 'opencv_detector'):
            self._init_qr_tools()
            
        if not hasattr(self, 'tools_loaded') or not self.tools_loaded:
            logging.error("❌ QR araçları yüklenemedi!")
            return None
            
        original_img = img.copy()
        h, w = img.shape[:2]
        
        logging.debug(f"📷 Dengeli QR tarama - {w}x{h}")
        
        # === 1. FASE: GENİŞ BÖLGESEL TARAMA ===
        # Tüm köşeleri ve orta bölgeleri kontrol et
        regions = [
            ("Sağ Üst", img[0:int(h*0.4), int(w*0.6):w]),      # E-fatura standart konum
            ("Sol Üst", img[0:int(h*0.4), 0:int(w*0.4)]),       # Alternatif konum
            ("Sağ Alt", img[int(h*0.6):h, int(w*0.6):w]),       # Alt köşe
            ("Orta", img[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]), # Merkez bölge
            ("Sol Alt", img[int(h*0.6):h, 0:int(w*0.4)])        # Son köşe
        ]
        
        for region_name, region in regions:
            if region.size > 100:
                result = self._scan_region_pyzbar(region, region_name)
                if result:
                    return result
        
        # === 2. FASE: TAM GÖRÜNTÜ TARAMASI ===
        result = self._scan_full_image_pyzbar(original_img)
        if result:
            return result
        
        # === 3. FASE: GELİŞMİŞ GÖRÜNTÜ İŞLEME ===
        # Griye çevir
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Etkili görüntü işleme teknikleri
        processing_methods = [
            ("Gaussian Blur", lambda g: self._process_with_gaussian_blur(g)),
            ("Adaptive Threshold", lambda g: self._process_with_adaptive_threshold(g)),
            ("Otsu Threshold", lambda g: self._process_with_otsu_threshold(g)),
            ("Contrast", lambda g: self._process_with_contrast_enhancement(g))
        ]
        
        for method_name, method in processing_methods:
            try:
                result = method(gray)
                if result:
                    logging.info(f"✅ {method_name} ile QR bulundu: {len(result)} karakter")
                    return result
            except Exception as e:
                logging.debug(f"⚠️ {method_name} hatası: {e}")
                continue
        
        # === 4. FASE: OPENCV FALLBACK ===
        try:
            data, bbox, _ = self.opencv_detector.detectAndDecode(gray)
            if data and len(data.strip()) > 10:
                logging.info(f"✅ OpenCV ile QR bulundu: {len(data)} karakter")
                return data.strip()
        except Exception as e:
            logging.debug(f"OpenCV hatası: {e}")
        
        logging.debug("❌ QR bulunamadı - Tüm yöntemler denendi")
        return None

    
    def _scan_region_pyzbar(self, region, region_name):
        """Belirli bir bölgede PyZBar ile QR taraması"""
        try:
            codes = pyzbar.decode(region)
            if codes and len(codes) > 0:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if data and len(data.strip()) > 5:
                    logging.info(f"✅ QR bulundu ({region_name}): {len(data)} karakter")
                    return data.strip()
        except Exception as e:
            logging.debug(f"🔍 {region_name} bölge tarama hatası: {e}")
        return None
    
    def _scan_full_image_pyzbar(self, img):
        """Tam görüntüde PyZBar taraması"""
        try:
            codes = pyzbar.decode(img)
            if codes and len(codes) > 0:
                # En büyük QR'ı al (daha güvenilir)
                largest_code = max(codes, key=lambda c: c.rect.width * c.rect.height)
                data = largest_code.data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if data and len(data.strip()) > 5:
                    logging.info(f"✅ Tam görüntü PyZBar: {len(data)} karakter")
                    return data.strip()
        except Exception as e:
            logging.debug(f"🔍 Tam görüntü PyZBar hatası: {e}")
        return None
    
    def _process_with_gaussian_blur(self, gray):
        """Gaussian blur ile işleme"""
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        codes = pyzbar.decode(blurred)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ Gaussian blur ile QR bulundu")
                return data.strip()
        return None
    
    def _process_with_adaptive_threshold(self, gray):
        """Adaptive threshold ile işleme"""
        # Farklı parametrelerle dene
        params = [(11, 2), (15, 3), (9, 2), (21, 4)]
        
        for block_size, c in params:
            try:
                thresh = cv2.adaptiveThreshold(gray, 255, 
                                             cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                             cv2.THRESH_BINARY, 
                                             block_size, c)
                codes = pyzbar.decode(thresh)
                if codes:
                    data = codes[0].data
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', errors='ignore')
                    if data and len(data.strip()) > 5:
                        logging.info(f"✅ Adaptive threshold ({block_size},{c}) ile QR bulundu")
                        return data.strip()
            except Exception:
                continue
        return None
    
    def _process_with_otsu_threshold(self, gray):
        """Otsu threshold ile işleme"""
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        codes = pyzbar.decode(thresh)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ Otsu threshold ile QR bulundu")
                return data.strip()
        return None
    
    def _process_with_morphology(self, gray):
        """Morphological işlemler ile QR iyileştirme"""
        # Morphological opening ve closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # Opening (noise reduction)
        opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        codes = pyzbar.decode(opened)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ Morphological opening ile QR bulundu")
                return data.strip()
        
        # Closing (gap filling)
        closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        codes = pyzbar.decode(closed)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ Morphological closing ile QR bulundu")
                return data.strip()
                
        return None
    
    def _process_with_contrast_enhancement(self, gray):
        """Kontrast artırma ile işleme"""
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        codes = pyzbar.decode(enhanced)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ CLAHE kontrast artırma ile QR bulundu")
                return data.strip()
        
        return None
    
    def _process_with_noise_reduction(self, gray):
        """Gürültü azaltma ile işleme"""
        # Bilateral filter (edge-preserving noise reduction)
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        codes = pyzbar.decode(filtered)
        if codes:
            data = codes[0].data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 5:
                logging.info("✅ Bilateral filter ile QR bulundu")
                return data.strip()
        
        return None
    
    def process_pdf(self, pdf_path):
        """PDF dosyasından QR okuma - PERFORMANS OPTİMİZELİ"""
        
        try:
            with fitz.open(pdf_path) as pdf_doc:
                if len(pdf_doc) == 0:
                    logging.warning(f"⚠️ PDF boş: {pdf_path}")
                    return None
                
                # Sadece ilk sayfa ile çalış (performans)
                page = pdf_doc[0]
                
                # 3 ZOOM LEVELİ - DENGELİ İŞLEM
                zoom_levels = [2.5, 2.0, 1.5]  # Yüksek, orta ve düşük çözünürlük
                
                for zoom in zoom_levels:
                    try:
                        # Matris oluştur
                        mat = fitz.Matrix(zoom, zoom)
                        
                        # Görüntüyü render et
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        
                        # OpenCV formatına çevir
                        img_array = np.frombuffer(img_data, np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        if img is not None:
                            # QR tara
                            qr_data = self.scan_qr_fast(img)
                            if qr_data:
                                logging.info(f"✅ PDF QR bulundu (zoom {zoom}): {len(qr_data)} karakter")
                                return qr_data
                        
                    except Exception as e:
                        logging.debug(f"Zoom {zoom} hatası: {e}")
                        continue
                
                # Eğer birden fazla sayfa varsa ikinci sayfayı da dene
                if len(pdf_doc) > 1:
                    page = pdf_doc[1]
                    try:
                        mat = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        img_array = np.frombuffer(img_data, np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        if img is not None:
                            qr_data = self.scan_qr_fast(img)
                            if qr_data:
                                logging.info(f"✅ PDF sayfa 2'de QR bulundu")
                                return qr_data
                    except Exception as e:
                        logging.debug(f"Sayfa 2 hatası: {e}")
                
                logging.debug(f"❌ PDF'de QR bulunamadı: {pdf_path}")
                return None
                
        except Exception as e:
            logging.error(f"❌ PDF işleme hatası: {e}")
            return None
    
    def process_image(self, image_path):
        """GELİŞTİRİLMİŞ RESİM İŞLEME"""
        if not hasattr(self, 'tools_loaded'):
            self._init_qr_tools()
            
        try:
            logging.debug(f"🖼️ Resim işleniyor: {os.path.basename(image_path)}")
            
            # Farklı okuma modlarıyla dene
            read_modes = [
                (cv2.IMREAD_COLOR, "Renkli"),
                (cv2.IMREAD_GRAYSCALE, "Gri"),
                (cv2.IMREAD_UNCHANGED, "Değişmemiş")
            ]
            
            for mode, mode_name in read_modes:
                try:
                    img = cv2.imread(image_path, mode)
                    
                    if img is not None:
                        logging.debug(f"🔍 {mode_name} modda okundu: {img.shape}")
                        
                        # Gri modda ise 3 kanala çevir
                        if mode == cv2.IMREAD_GRAYSCALE:
                            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                        
                        result = self.scan_qr_fast(img)
                        if result:
                            logging.info(f"✅ Resim QR bulundu ({mode_name} mod): {os.path.basename(image_path)}")
                            return result
                except Exception as e:
                    logging.debug(f"⚠️ {mode_name} mod okuma hatası: {e}")
                    continue
            
            # Alternatif: PIL ile okuma dene (eğer mevcutsa)
            try:
                from PIL import Image
                pil_img = Image.open(image_path)
                
                # RGB'ye çevir
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                
                # NumPy array'e çevir
                img_array = np.array(pil_img)
                
                # BGR formatına çevir (OpenCV formatı)
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                result = self.scan_qr_fast(img_bgr)
                if result:
                    logging.info(f"✅ PIL ile QR bulundu: {os.path.basename(image_path)}")
                    return result
                    
            except ImportError:
                logging.debug("PIL kütüphanesi mevcut değil, atlanıyor")
            except Exception as e:
                logging.debug(f"⚠️ PIL okuma hatası: {e}")
            
            logging.warning(f"❌ Resimde QR bulunamadı: {os.path.basename(image_path)}")
            
        except Exception as e:
            logging.error(f"❌ Resim okuma hatası: {os.path.basename(image_path)} - {e}")
        
        return None
    
    def process_file(self, file_path):
        """GELİŞTİRİLMİŞ TEK DOSYA İŞLEME"""
        try:
            file_basename = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            logging.info(f"📁 Dosya işleniyor: {file_basename}")
            
            # Dosya boyutu kontrolü
            try:
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                if file_size > 50:  # 50 MB'dan büyük dosyaları uyar
                    logging.warning(f"⚠️ Büyük dosya: {file_size:.1f} MB")
            except Exception:
                pass
            
            qr_data = None
            
            # Dosya tipine göre işle
            if file_ext == '.pdf':
                qr_data = self.process_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']:
                qr_data = self.process_image(file_path)
            else:
                logging.warning(f"⚠️ Desteklenmeyen dosya tipi: {file_ext}")
                return {
                    'dosya_adi': file_basename,
                    'durum': 'DESTEKLENMEYEN FORMAT',
                    'json_data': {},
                    'hata_detay': f'Dosya tipi desteklenmiyor: {file_ext}'
                }
            
            if qr_data and len(qr_data.strip()) > 0:
                logging.info(f"🔍 QR veri uzunluğu: {len(qr_data)} karakter")
                
                # JSON temizleme ve ayrıştırma
                json_data = self.clean_json(qr_data)
                
                if json_data and len(json_data) > 0:
                    # Ham QR verisini de ekle (debug için)
                    json_data['_raw_qr_data'] = qr_data[:500]  # İlk 500 karakter
                    
                    return {
                        'dosya_adi': file_basename,
                        'durum': 'BAŞARILI',
                        'json_data': json_data,
                        'qr_uzunluk': len(qr_data),
                        'json_anahtar_sayisi': len(json_data)
                    }
                else:
                    return {
                        'dosya_adi': file_basename,
                        'durum': 'JSON HATASI',
                        'json_data': {},
                        'hata_detay': 'QR verisi JSON olarak ayrıştırılamadı',
                        '_raw_qr_data': qr_data[:200]  # Debug için
                    }
            else:
                return {
                    'dosya_adi': file_basename,
                    'durum': 'QR BULUNAMADI',
                    'json_data': {},
                    'hata_detay': 'Dosyada QR kod tespit edilemedi'
                }
            
        except Exception as e:
            logging.error(f"❌ Kritik dosya işleme hatası: {os.path.basename(file_path)} - {e}")
            return {
                'dosya_adi': os.path.basename(file_path),
                'durum': 'KRİTİK HATA',
                'json_data': {},
                'hata_detay': str(e)
            }
    
    def process_qr_files_in_folder(self, folder_path, max_workers=8, status_callback=None):
        """PERFORMANS OPTİMİZELİ - Klasördeki tüm dosyaları paralel işle"""
        
        import os
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # HATA VEREN IMPORTLAR SADECE BU FONKSİYON ÇAĞRILINCA YÜKLENECEK
        global fitz, cv2, pyzbar
        try:
            import fitz  # PyMuPDF
            import cv2
            from pyzbar import pyzbar
            logging.info("🔧 QR kütüphaneleri yüklendi.")
        except ImportError as e:
            logging.error(f"❌ QR kütüphaneleri eksik: {e}")
            if status_callback:
                status_callback("QR Kütüphaneleri Eksik!", 10000)
            return None

        if status_callback:
            status_callback("📁 Dosyalar taranıyor...", 5)
        
        start_time = time.time()
        file_paths = []
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp'}
        
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path) and os.path.splitext(file_name)[1].lower() in allowed_extensions:
                    file_paths.append(file_path)
                    
        except Exception as e:
            logging.error(f"Klasör okuma hatası: {e}")
            return []
        
        if not file_paths:
            logging.warning("⚠️ İşlenebilir dosya bulunamadı")
            return []
        
        logging.info(f"🚀 Hızlı QR işleme başlıyor: {len(file_paths)} dosya, {max_workers} thread")
        
        results = []
        completed_count = 0
        
        # PARALEL İŞLEM - YUKSEK PERFORMANS
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Tüm dosyaları kuyruğa ekle
            future_to_file = {executor.submit(self.process_file, file_path): file_path 
                             for file_path in file_paths}
            
            # Sonuçları topla
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed_count += 1
                
                # İlerleme bildirimi
                progress = int((completed_count / len(file_paths)) * 90)  # %90'a kadar
                if status_callback:
                    status_callback(f"🔍 İşleniyor... ({completed_count}/{len(file_paths)})", progress)
                
                try:
                    result = future.result(timeout=30)  # 30 saniye timeout
                    if result:
                        results.append(result)
                        logging.debug(f"✅ Tamamlandı: {os.path.basename(file_path)}")
                    
                except Exception as e:
                    logging.error(f"❌ '{os.path.basename(file_path)}' işlenirken hata: {e}")
                    results.append({
                        'dosya_adi': os.path.basename(file_path), 
                        'durum': 'HATA', 
                        'json_data': {},
                        'hata_detay': str(e)
                    })
        
        total_time = time.time() - start_time
        logging.info(f"🏁 Hızlı QR işleme bitti. Süre: {total_time:.1f}s")
        
        if status_callback:
            status_callback("✅ QR işleme tamamlandı!", 100)
        
        return results

    def parse_qr_to_invoice_fields(self, qr_json):
        """
        GELİŞTİRİLMİŞ QR JSON VERİSİNİ FATURA ALANLARINA ÇEVİRME
        """
        if not qr_json: 
            logging.warning("⚠️ Boş QR JSON verisi")
            return {}

        logging.info(f"🔍 QR JSON Anahtarları: {list(qr_json.keys())}")
        
        # Gelişmiş anahtar eşleme sözlüğü
        key_map = {
            'irsaliye_no': [
                'invoiceId', 'faturaNo', 'belgeno', 'uuid', 'id', 'no', 'invoiceNumber', 
                'belgeNo', 'seriNo', 'ettn', 'faturaid', 'documentId', 'documentNumber',
                'belge_no', 'fatura_no', 'invoice_id', 'document_id'
            ],
            'tarih': [
                'invoiceDate', 'faturaTarihi', 'tarih', 'date', 'invoicedate', 
                'faturatarihi', 'dateTime', 'issueDate', 'createDate', 'verilisTarihi',
                'invoice_date', 'fatura_tarihi', 'issue_date', 'create_date'
            ],
            'firma': [
                'sellerName', 'saticiUnvan', 'firma', 'supplier', 'company', 'companyName', 
                'firmaUnvan', 'aliciUnvan', 'buyerName', 'saticiadi', 'aliciadi', 'satici',
                'sellername', 'buyername', 'supplierName', 'vendorName', 'merchant',
                'seller_name', 'buyer_name', 'company_name', 'supplier_name'
            ],
            'malzeme': [
                'tip', 'type', 'itemName', 'description', 'malzeme', 'hizmet', 'urun', 
                'product', 'service', 'senaryo', 'productName', 'serviceName',
                'item_name', 'product_name', 'service_name', 'material', 'goods'
            ],
            'miktar': [
                'quantity', 'miktar', 'adet', 'amount', 'qty', 'quantityvalue', 
                'lineitem', 'kalem', 'itemCount', 'count', 'pieces',
                'item_count', 'piece_count', 'total_quantity'
            ],
            'toplam_tutar': [
                'payableAmount', 'odenecek', 'vergidahil', 'totalAmount', 'toplamTutar', 
                'total', 'amount', 'tutar', 'geneltoplam', 'vergidahiltoplam', 
                'payableamount', 'totalamount', 'grandTotal', 'invoiceTotal',
                'payable_amount', 'total_amount', 'grand_total', 'invoice_total'
            ],
            'matrah': [
                'taxableAmount', 'matrah', 'netAmount', 'malhizmettoplam', 'kdvmatrah', 
                'taxableamount', 'netamount', 'subTotal', 'baseAmount',
                'taxable_amount', 'net_amount', 'sub_total', 'base_amount'
            ],
            'kdv_tutari': [
                'taxAmount', 'hesaplanankdv', 'kdv', 'kdvtoplam', 'hesaplanan kdv', 
                'taxamount', 'kdvtutari', 'vatAmount', 'vatTotal',
                'tax_amount', 'vat_amount', 'vat_total', 'calculated_tax'
            ],
            'kdv_yuzdesi': [
                'taxRate', 'kdvOrani', 'vatRate', 'kdvorani', 'taxrate', 'vatrate',
                'taxPercentage', 'vatPercentage', 'tax_rate', 'vat_rate', 'tax_percentage'
            ],
            'birim': [
                'currency', 'parabirimi', 'currencyCode', 'paraBirimi', 'currencycode',
                'curr', 'unit', 'currency_code', 'para_birimi'
            ]
        }

        parsed = {}

        def get_value(keys):
            """Büyük/küçük harf duyarsız ve çok kapsamlı arama"""
            # Önce tam eşleşme ara
            for key in keys:
                if key in qr_json and qr_json[key] is not None and str(qr_json[key]).strip():
                    logging.debug(f"  ✓ Tam eşleşme: {key} = {qr_json[key]}")
                    return qr_json[key]
            
            # Küçük harf eşleşmesi
            qr_json_lower = {k.lower().replace('_', '').replace('-', ''): v 
                           for k, v in qr_json.items() if v is not None}
            
            for key in keys:
                key_normalized = key.lower().replace('_', '').replace('-', '')
                if key_normalized in qr_json_lower:
                    value = qr_json_lower[key_normalized]
                    if value is not None and str(value).strip():
                        logging.debug(f"  ✓ Normalize eşleşme: {key} = {value}")
                        return value
            
            # Kısmi eşleşme (anahtar kelime içeren)
            for key in keys:
                key_parts = key.lower().split('_')
                for orig_key, orig_value in qr_json.items():
                    if orig_value is not None and str(orig_value).strip():
                        orig_key_lower = orig_key.lower()
                        if any(part in orig_key_lower for part in key_parts):
                            logging.debug(f"  ✓ Kısmi eşleşme: {orig_key} = {orig_value}")
                            return orig_value
            
            return None

        # İrsaliye No
        parsed['irsaliye_no'] = str(get_value(key_map['irsaliye_no']) or f"QR-{int(time.time())}")
        
        # Tarih işleme
        qr_tarih = get_value(key_map['tarih'])
        if qr_tarih:
            parsed['tarih'] = self.format_date(str(qr_tarih))
        else:
            parsed['tarih'] = datetime.now().strftime("%d.%m.%Y")
        
        # Firma adı - zorunlu alan
        firma_adi = get_value(key_map['firma'])
        if not firma_adi or (isinstance(firma_adi, str) and (firma_adi.isdigit() or len(firma_adi.strip()) < 2)):
            # Alternatif firma bilgileri ara
            alternatifler = ['vkntckn', 'vkn', 'avkntckn', 'avkn', 'taxNumber', 'companyId']
            for alt_key in alternatifler:
                alt_value = get_value([alt_key])
                if alt_value and not str(alt_value).isdigit():
                    firma_adi = f"{alt_key.upper()}: {alt_value}"
                    break
            
            if not firma_adi:
                firma_adi = 'QR Faturası'  # Varsayılan isim
        
        parsed['firma'] = str(firma_adi)
        
        # Malzeme/Hizmet türü
        malzeme = get_value(key_map['malzeme'])
        if malzeme:
            malzeme_str = str(malzeme).upper()
            
            # Fatura tipi normalizasyonu
            tip_map = {
                'EARSIV': 'E-Arşiv Fatura',
                'E-ARSIV': 'E-Arşiv Fatura',
                'TICARIFATURA': 'Ticari Fatura',
                'TICARI': 'Ticari Fatura',
                'TEMEL': 'Temel Fatura',
                'ISTISNA': 'İstisna Faturası',
                'SATIS': 'Satış Faturası',
                'ALIS': 'Alış Faturası',
                'SARJANLIK': 'Şarj/Anlık Satış'
            }
            
            for key_word, display_name in tip_map.items():
                if key_word in malzeme_str:
                    malzeme_str = display_name
                    break
            
            parsed['malzeme'] = malzeme_str
        else:
            parsed['malzeme'] = 'QR Kodlu E-Fatura'
        
        # Miktar - varsayılan 1
        miktar_value = get_value(key_map['miktar'])
        if miktar_value:
            try:
                miktar_str = str(miktar_value).strip()
                # Sayısal olmayan karakterleri temizle
                miktar_clean = re.sub(r'[^\d.,]', '', miktar_str)
                if miktar_clean and float(miktar_clean.replace(',', '.')) > 0:
                    parsed['miktar'] = miktar_clean.replace(',', '.')
                else:
                    parsed['miktar'] = '1'
            except Exception:
                parsed['miktar'] = '1'
        else:
            parsed['miktar'] = '1'
        
        # Para birimi
        birim = str(get_value(key_map['birim']) or 'TRY').upper()
        if birim in ['TRY', 'TRL', 'TÜRK LİRASI', 'TURK LIRASI', 'TURKISH LIRA']:
            birim = 'TL'
        parsed['birim'] = birim
        
        logging.info(f"📝 Temel Alanlar - Miktar: {parsed['miktar']}, Birim: {parsed['birim']}, Malzeme: {parsed['malzeme'][:30]}")

        # Tutar hesaplamaları
        toplam_tutar = self._to_float(get_value(key_map['toplam_tutar']))
        matrah = self._to_float(get_value(key_map['matrah']))
        kdv_tutari = self._to_float(get_value(key_map['kdv_tutari']))
        kdv_yuzdesi = self._to_float(get_value(key_map['kdv_yuzdesi']))

        logging.info(f"💰 QR Tutar Bilgileri - Toplam: {toplam_tutar}, Matrah: {matrah}, KDV Tutarı: {kdv_tutari}, KDV%: {kdv_yuzdesi}")

        # KDV yüzdesi hesaplama
        if kdv_yuzdesi > 0 and kdv_yuzdesi <= 100:
            parsed['kdv_yuzdesi'] = kdv_yuzdesi
        elif matrah > 0 and kdv_tutari > 0:
            calculated_rate = round((kdv_tutari / matrah) * 100, 2)
            if 0 < calculated_rate <= 100:
                parsed['kdv_yuzdesi'] = calculated_rate
            else:
                parsed['kdv_yuzdesi'] = 20.0
        else:
            parsed['kdv_yuzdesi'] = 20.0  # Varsayılan %20

        # Tutar hesaplama mantığı
        if matrah > 0 and toplam_tutar > 0:
            # Hem matrah hem toplam var
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
                
            logging.info(f"✅ Matrah ve Toplam mevcut - Matrah: {matrah} TL, KDV: {parsed['kdv_tutari']} TL")
            
        elif toplam_tutar > 0:
            # Sadece toplam var
            parsed['toplam_tutar'] = toplam_tutar
            
            if kdv_tutari > 0:
                # KDV tutarı da var, KDV dahil kabul et
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = kdv_tutari
                logging.info(f"✅ Toplam ve KDV Tutarı mevcut - KDV Dahil: {toplam_tutar} TL, KDV: {kdv_tutari} TL")
            else:
                # KDV dahil varsay ve hesapla
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = toplam_tutar * (parsed['kdv_yuzdesi'] / (100 + parsed['kdv_yuzdesi']))
                logging.info(f"⚠️ Sadece Toplam mevcut - KDV Dahil varsayıldı: {toplam_tutar} TL")
                
        elif matrah > 0:
            # Sadece matrah var
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
                
            logging.info(f"✅ Sadece Matrah mevcut - KDV Hariç: {matrah} TL")
            
        else:
            # Hiçbir tutar bulunamadı - bu QR'ı atla
            logging.warning("❌ QR'da hiçbir tutar bilgisi bulunamadı - QR atlanıyor!")
            return {}  # Boş dict dönerek bu QR'ın atlanmasını sağla

        logging.info(f"📊 Final Sonuç - Tutar: {parsed.get('toplam_tutar', 0)} {parsed.get('birim', 'TL')}, KDV%: {parsed.get('kdv_yuzdesi', 0)}, KDV Tutarı: {parsed.get('kdv_tutari', 0)}")

        return parsed

    def _to_float(self, value):
        """Bir değeri güvenli bir şekilde float'a çevirir."""
        if value is None or value == '': 
            return 0.0
        
        try:
            str_value = str(value).strip()
            
            if not str_value or str_value.lower() in ['none', 'null', 'n/a']:
                return 0.0
            
            str_value = re.sub(r'[^\d.,\-+]', '', str_value)
            
            if ',' in str_value and '.' in str_value:
                last_comma = str_value.rfind(',')
                last_dot = str_value.rfind('.')
                
                if last_comma > last_dot:
                    str_value = str_value.replace('.', '').replace(',', '.')
                else:
                    str_value = str_value.replace(',', '')
            elif ',' in str_value:
                parts = str_value.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    str_value = str_value.replace(',', '.')
                else:
                    str_value = str_value.replace(',', '')
            
            return float(str_value)
            
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning(f"   ⚠️ Float dönüşüm hatası: '{value}' -> Hata: {e}")
            return 0.0

    def format_date(self, date_input):
        """Tarih formatını normalize eder."""
        if not date_input:
            return datetime.now().strftime("%d.%m.%Y")
        
        date_str = str(date_input).strip()
        
        # Yaygın formatları dene
        formats = [
            "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d",
            "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%y", "%d/%m/%y"
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        # ISO formatı dene
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        # Sadece sayı varsa (YYYYMMDD formatı)
        if date_str.isdigit() and len(date_str) == 8:
            try:
                cleaned_date = date_str.strip()
                if len(cleaned_date) == 8:
                    parsed_date = datetime(int(cleaned_date[:4]), int(cleaned_date[4:6]), int(cleaned_date[6:8]))
                    return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                pass
        
        # DDMMYYYY formatı dene
        if date_str.isdigit() and len(date_str) == 8:
            try:
                cleaned_date = date_str.strip()
                parsed_date = datetime(int(cleaned_date[4:8]), int(cleaned_date[2:4]), int(cleaned_date[:2]))
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                pass
        
        logging.warning(f"Tarih formatı tanınmadı: {date_str}")
        return datetime.now().strftime("%d.%m.%Y")
