# qr_optimized.py
# -*- coding: utf-8 -*-
"""
OPTIMIZE EDİLMİŞ QR İŞLEME SİSTEMİ
- 3 Aşamalı Akıllı Tarama (Hızlı → Orta → Derin)
- Otomatik Fatura Tipi Tespiti (SATIS/ALIS)
- Performans ve Doğruluk Dengesi
"""

import cv2
import json
import numpy as np
from pyzbar import pyzbar
import os
import re
import time
import logging
import fitz  # PyMuPDF
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OptimizedQRProcessor:
    """PERFORMANS-DOĞRULUK DENGELİ QR İŞLEMCİSİ"""
    
    def __init__(self):
        self.opencv_detector = None
        self.tools_loaded = False
        self.stats = {
            'stage1_fast': 0,      # 450 DPI, bölgesel
            'stage2_medium': 0,    # 600 DPI, 3 bölge + kontrast
            'stage3_deep': 0,      # 750 DPI, gelişmiş işleme
            'failed': 0
        }
    
    def _init_qr_tools(self):
        """QR araçlarını lazy loading ile yükle"""
        if self.tools_loaded:
            return
        
        try:
            cv2.setNumThreads(6)
            cv2.setUseOptimized(True)
            self.opencv_detector = cv2.QRCodeDetector()
            self.tools_loaded = True
            logging.info("✅ QR araçları yüklendi")
        except Exception as e:
            logging.error(f"❌ QR araçları yüklenemedi: {e}")
            raise ImportError("QR kütüphaneleri eksik! pip install opencv-python-headless pyzbar PyMuPDF")
    
    def clean_json(self, qr_text):
        """Geliştirilmiş JSON temizleme"""
        if not qr_text or len(qr_text.strip()) < 5:
            return {}
        
        cleaned = qr_text.strip()
        
        # Kontrol karakterlerini temizle
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        cleaned = re.sub(r'\\x[0-9a-fA-F]{2}', '', cleaned)
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        
        # JSON parse denemeleri
        parse_attempts = [
            cleaned,
            cleaned.replace("'", '"'),
            re.sub(r'[""‚›‛′‵]', '"', cleaned),
        ]
        
        for attempt in parse_attempts:
            try:
                return json.loads(attempt)
            except:
                continue
        
        # Manuel key-value çıkarma
        try:
            kv_pairs = {}
            pattern = r'["\']?([a-zA-Z_]\w*)["\']?\s*:\s*["\']?([^,"}\]\n]+)["\']?'
            matches = re.findall(pattern, cleaned)
            
            for key, value in matches:
                value = value.strip().strip('"').strip("'")
                try:
                    kv_pairs[key] = float(value) if '.' in value and value.replace('.', '').isdigit() else value
                except:
                    kv_pairs[key] = value
            
            if kv_pairs:
                logging.info(f"✅ Manuel parse başarılı: {len(kv_pairs)} alan")
                return kv_pairs
        except:
            pass
        
        logging.warning(f"⚠️ JSON parse başarısız: {qr_text[:100]}")
        return {"_raw_data": qr_text, "_parse_error": True}
    
    # ================== AŞAMA 1: HIZLI TARAMA ==================
    
    def _stage1_fast(self, img):
        """AŞAMA 1: Hızlı tarama - Sağ üst bölge + tam resim"""
        h, w = img.shape[:2]
        
        # 1. Sağ üst bölge (E-faturaların %70'i burada)
        try:
            region = img[0:int(h*0.4), int(w*0.6):w]
            if region.size > 0:
                codes = pyzbar.decode(region)
                if codes:
                    data = self._extract_qr_data(codes[0])
                    if data:
                        return data
        except:
            pass
        
        # 2. Tam resim PyZBar
        try:
            codes = pyzbar.decode(img)
            if codes:
                data = self._extract_qr_data(codes[0])
                if data:
                    return data
        except:
            pass
        
        return None
    
    # ================== AŞAMA 2: ORTA SEVİYE ==================
    
    def _stage2_medium(self, img):
        """AŞAMA 2: Orta seviye - 3 bölge + kontrast artırma"""
        # Gri tonlama + kontrast
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        h, w = enhanced.shape[:2]
        
        # 3 kritik bölge tara
        regions = [
            ("Sağ Üst", enhanced[0:int(h*0.5), int(w*0.6):w]),
            ("Orta Üst", enhanced[0:int(h*0.4), int(w*0.3):int(w*0.7)]),
            ("Sol Üst", enhanced[0:int(h*0.4), 0:int(w*0.4)]),
        ]
        
        for region_name, region in regions:
            if region.size > 0:
                try:
                    codes = pyzbar.decode(region)
                    if codes:
                        data = self._extract_qr_data(codes[0])
                        if data:
                            logging.debug(f"✅ {region_name} bölgede bulundu")
                            return data
                except:
                    pass
        
        # Tam resim tarama
        try:
            codes = pyzbar.decode(enhanced)
            if codes:
                data = self._extract_qr_data(codes[0])
                if data:
                    return data
        except:
            pass
        
        return None
    
    # ================== AŞAMA 3: DERİN TARAMA ==================
    
    def _stage3_deep(self, img):
        """AŞAMA 3: Derin tarama - Çoklu görüntü işleme"""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Çoklu işleme teknikleri
        processing_methods = [
            ("Gaussian Blur", lambda g: cv2.GaussianBlur(g, (5, 5), 0)),
            ("Adaptive Threshold", lambda g: cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
            ("Otsu Threshold", lambda g: cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
            ("CLAHE Enhanced", lambda g: cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8)).apply(g)),
        ]
        
        for method_name, method_func in processing_methods:
            try:
                processed = method_func(gray)
                
                # PyZBar dene
                codes = pyzbar.decode(processed)
                if codes:
                    data = self._extract_qr_data(codes[0])
                    if data:
                        logging.debug(f"✅ {method_name} ile bulundu")
                        return data
                
                # OpenCV dene
                if self.opencv_detector:
                    qr_data, _, _ = self.opencv_detector.detectAndDecode(processed)
                    if qr_data and len(qr_data.strip()) > 10:
                        logging.debug(f"✅ {method_name} + OpenCV ile bulundu")
                        return qr_data
            except:
                continue
        
        return None
    
    # ================== PDF İŞLEME - 3 DPI SEVİYESİ ==================
    
    def extract_text_from_pdf(self, pdf_path):
        """PDF'den metin çıkar (OCR alternatifi - PyMuPDF text extraction)"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            # İlk sayfa yeterli (fatura bilgileri genelde ilk sayfada)
            page = doc.load_page(0)
            text = page.get_text()
            doc.close()
            return text
        except Exception as e:
            logging.warning(f"⚠️ PDF metin çıkarma hatası ({os.path.basename(pdf_path)}): {e}")
            return ""
    
    def process_pdf(self, pdf_path):
        """PDF işleme - 3 aşamalı DPI artırma + metin çıkarma"""
        if not self.tools_loaded:
            self._init_qr_tools()
        
        # PDF'den metin çıkar (Firma ve Mal-Hizmet bilgisi için)
        pdf_text = self.extract_text_from_pdf(pdf_path)
        
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            
            # AŞAMA 1: 450 DPI (Hızlı)
            result = self._try_pdf_with_dpi(page, 450, "HIZLI")
            if result:
                doc.close()
                self.stats['stage1_fast'] += 1
                return result, pdf_text
            
            # AŞAMA 2: 600 DPI (Orta)
            result = self._try_pdf_with_dpi(page, 600, "ORTA")
            if result:
                doc.close()
                self.stats['stage2_medium'] += 1
                return result, pdf_text
            
            # AŞAMA 3: 750 DPI (Derin)
            result = self._try_pdf_with_dpi(page, 750, "DERİN")
            if result:
                doc.close()
                self.stats['stage3_deep'] += 1
                return result, pdf_text
            
            doc.close()
            self.stats['failed'] += 1
            return None, pdf_text
            
        except Exception as e:
            logging.error(f"❌ PDF hatası ({os.path.basename(pdf_path)}): {e}")
            self.stats['failed'] += 1
            return None, ""
    
    def _try_pdf_with_dpi(self, page, dpi, stage_name):
        """Belirli DPI ile PDF'den QR okumayı dene"""
        try:
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Aşamaya göre işleme
            if stage_name == "HIZLI":
                return self._stage1_fast(img)
            elif stage_name == "ORTA":
                return self._stage2_medium(img)
            elif stage_name == "DERİN":
                return self._stage3_deep(img)
            
        except:
            pass
        
        return None
    
    # ================== RESİM İŞLEME ==================
    
    def process_image(self, image_path):
        """Resim işleme - 3 aşamalı"""
        if not self.tools_loaded:
            self._init_qr_tools()
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None, ""
            
            # AŞAMA 1
            result = self._stage1_fast(img)
            if result:
                self.stats['stage1_fast'] += 1
                return result, ""
            
            # AŞAMA 2
            result = self._stage2_medium(img)
            if result:
                self.stats['stage2_medium'] += 1
                return result, ""
            
            # AŞAMA 3
            result = self._stage3_deep(img)
            if result:
                self.stats['stage3_deep'] += 1
                return result, ""
            
            self.stats['failed'] += 1
            return None, ""
            
        except Exception as e:
            logging.error(f"❌ Resim hatası ({os.path.basename(image_path)}): {e}")
            self.stats['failed'] += 1
            return None, ""
    
    # ================== YARDIMCI FONKSİYONLAR ==================
    
    def _extract_qr_data(self, code):
        """PyZBar QR code objesinden veriyi çıkar"""
        try:
            data = code.data
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if data and len(data.strip()) > 10:
                return data
        except:
            pass
        return None
    
    def extract_info_from_text(self, pdf_text, file_name):
        """PDF metninden firma, mal-hizmet ve miktar bilgisi çıkar"""
        info = {
            'firma': None,
            'malzeme': None,
            'miktar': None
        }
        
        if not pdf_text:
            return info
        
        lines = pdf_text.split('\n')
        
        # ========== FİRMA ADI TESPİTİ - "SAYIN" KELİMESİNİN ALTINDA ==========
        # "SAYIN" kelimesini bul (koyu yazılı olabilir, regex ile case-insensitive ara)
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # "SAYIN" kelimesini içeren satırı bul
            if re.search(r'\bSAYIN\b', line_stripped, re.IGNORECASE):
                logging.debug(f"   🔍 'SAYIN' kelimesi bulundu: {line_stripped}")
                
                # Hemen altındaki satırı firma adı olarak al
                for j in range(i+1, min(i+4, len(lines))):
                    candidate = lines[j].strip()
                    
                    # Boş satırları atla
                    if not candidate or len(candidate) < 3:
                        continue
                    
                    # Sadece sayılardan oluşan satırları atla (VKN/TCKN olabilir)
                    if re.match(r'^[\d\s\-]+$', candidate):
                        continue
                    
                    # Telefon numarası formatını atla
                    if re.match(r'^[\d\s\-\+\(\)]{10,}$', candidate):
                        continue
                    
                    # Tarih formatını atla
                    if re.match(r'\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4}', candidate):
                        continue
                    
                    # E-posta adreslerini atla
                    if '@' in candidate and '.' in candidate:
                        continue
                    
                    # Geçerli firma adı bulundu
                    info['firma'] = candidate
                    logging.debug(f"   🏢 Firma adı (SAYIN altında): {candidate}")
                    break
                
                if info['firma']:
                    break
        
        # Eğer SAYIN ile bulunamadıysa, klasik yöntemle dene
        if not info['firma']:
            firma_keywords = [
                'alıcı unvan', 'alici unvan', 'satıcı unvan', 'satici unvan',
                'müşteri', 'musteri', 'firma adı', 'firma adi',
                'unvan', 'şirket', 'sirket', 'company name'
            ]
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                if any(keyword in line_lower for keyword in firma_keywords):
                    for j in range(i+1, min(i+5, len(lines))):
                        candidate = lines[j].strip()
                        if candidate and len(candidate) > 3:
                            if re.match(r'^\d{10,11}$', candidate):
                                continue
                            if re.match(r'^[\d\s\-\+\(\)]{10,}$', candidate):
                                continue
                            if re.match(r'\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4}', candidate):
                                continue
                            
                            info['firma'] = candidate
                            logging.debug(f"   🏢 Firma adı (keyword): {candidate}")
                            break
                    if info['firma']:
                        break
        
        # ========== MALZEME ADI TESPİTİ - TABLO İÇİNDEN ==========
        # Tablo başlık satırlarını bul
        malzeme_header_patterns = [
            r'mal\s+hizmet',  # "Mal Hizmet" (boşluklu)
            r'mal.*hizmet', 
            r'hizmet.*açıklama', 
            r'açıklama', 
            r'ürün.*ad',
            r'malzeme.*ad', 
            r'description', 
            r'item.*name', 
            r'product'
        ]
        
        table_start_idx = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Tablo başlığını tespit et
            if any(re.search(pattern, line_lower) for pattern in malzeme_header_patterns):
                table_start_idx = i
                logging.debug(f"   📊 Tablo başlığı bulundu (satır {i}): {line_lower}")
                break
        
        # Tablo bulunduysa, içeriği analiz et
        if table_start_idx is not None:
            # Başlıktan sonraki 30 satırı tara (tablo içeriği)
            for i in range(table_start_idx + 1, min(table_start_idx + 30, len(lines))):
                candidate = lines[i].strip()
                
                # Boş satırları atla
                if not candidate or len(candidate) < 3:
                    continue
                
                # Sadece sayı/noktalama/birim içeren satırları atla
                if re.match(r'^[\d\s\.\,\-\%\:]+$', candidate):
                    continue
                
                # Sadece birim olan satırları atla (M2, KG, ADET vb.)
                if re.match(r'^[A-Z]{1,4}\d?$', candidate):
                    continue
                
                # Para birimi satırlarını atla (EUR, TL, USD vb.)
                if candidate.upper() in ['EUR', 'TL', 'USD', 'GBP', 'TRY']:
                    continue
                
                # Tarih formatını atla
                if re.match(r'\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4}', candidate):
                    continue
                
                # Çok kısa satırları atla (sıra numarası olabilir)
                if len(candidate) <= 3:
                    continue
                
                # "Fiyat", "Tutar", "Vergi" gibi başlıkları atla
                if any(keyword in candidate.lower() for keyword in ['fiyat', 'tutar', 'vergi', 'kdv', 'birim']):
                    continue
                
                # Tablo bitiş göstergelerinde dur
                if any(keyword in candidate.lower() for keyword in ['toplam', 'genel', 'ara toplam', 'total']):
                    break
                
                # Geçerli malzeme adı (en az 5 karakter, harf içermeli)
                if len(candidate) >= 5 and re.search(r'[a-zA-ZğüşıöçĞÜŞİÖÇ]', candidate):
                    info['malzeme'] = candidate
                    logging.debug(f"   📦 Malzeme adı (tablodan): {candidate}")
                    break
        
        # ========== MİKTAR TESPİTİ - TABLO İÇİNDEN ==========
        # Miktar sütun başlığını bul
        miktar_header_patterns = [
            r'\bmiktar\b', r'\badet\b', r'\bquantity\b', 
            r'\bqty\b', r'\bamount\b', r'\bmkt\b'
        ]
        
        miktar_column_idx = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Miktar başlığını tespit et
            if any(re.search(pattern, line_lower) for pattern in miktar_header_patterns):
                miktar_column_idx = i
                logging.debug(f"   📊 Miktar başlığı bulundu (satır {i}): {line_lower}")
                break
        
        # Miktar başlığı bulunduysa
        if miktar_column_idx is not None:
            # Başlıktan sonraki 20 satırı tara
            for i in range(miktar_column_idx + 1, min(miktar_column_idx + 20, len(lines))):
                line_stripped = lines[i].strip()
                
                # Boş satırları atla
                if not line_stripped:
                    continue
                
                # Para birimi satırlarını atla
                if line_stripped.upper() in ['EUR', 'TL', 'USD', 'GBP', 'TRY']:
                    continue
                
                # Sadece birim olan satırları atla (M2, KG, ADET vb.)
                if re.match(r'^[A-Z]{1,4}\d?$', line_stripped):
                    continue
                
                # Sadece sayı içeren satır (miktar değeri)
                # 54.000 veya 54,000 gibi formatları yakala
                if re.match(r'^[\d\.\,\s]+$', line_stripped):
                    # Nokta ve virgülleri temizle, sayıyı normalize et
                    cleaned_number = line_stripped.replace('.', '').replace(',', '.').replace(' ', '')
                    
                    # Geçerli bir sayı mı?
                    try:
                        float_value = float(cleaned_number)
                        if float_value > 0:
                            info['miktar'] = cleaned_number
                            logging.debug(f"   🔢 Miktar (tablodan): {cleaned_number} (orijinal: {line_stripped})")
                            break
                    except ValueError:
                        continue
        
        # Alternatif: Malzeme satırından hemen sonraki sayısal satırı bul
        if not info['miktar'] and table_start_idx is not None and info['malzeme']:
            # Malzeme adının hangi satırda olduğunu bul
            malzeme_line_idx = None
            for i in range(table_start_idx + 1, min(table_start_idx + 30, len(lines))):
                if lines[i].strip() == info['malzeme']:
                    malzeme_line_idx = i
                    break
            
            # Malzeme satırından sonraki 3 satırı kontrol et
            if malzeme_line_idx:
                for i in range(malzeme_line_idx + 1, min(malzeme_line_idx + 4, len(lines))):
                    line_stripped = lines[i].strip()
                    
                    # Sadece sayı içeren satır
                    if re.match(r'^[\d\.\,\s]+$', line_stripped):
                        cleaned_number = line_stripped.replace('.', '').replace(',', '.').replace(' ', '')
                        try:
                            float_value = float(cleaned_number)
                            if float_value > 0:
                                info['miktar'] = cleaned_number
                                logging.debug(f"   🔢 Miktar (malzeme altında): {cleaned_number}")
                                break
                        except ValueError:
                            continue
        
        return info
    
    def process_file(self, file_path):
        """Tek dosya işleme - Ana giriş noktası (QR bulunamadığında da PDF tarama)"""
        try:
            file_basename = os.path.basename(file_path)
            # Dosya adından uzantıyı çıkar (fatura_no için)
            file_name_without_ext = os.path.splitext(file_basename)[0]
            
            # Dosya tipine göre işleme
            if file_path.lower().endswith('.pdf'):
                qr_data, pdf_text = self.process_pdf(file_path)
            else:
                qr_data, pdf_text = self.process_image(file_path)
            
            # PDF metninden ek bilgiler çıkar (her durumda)
            extracted_info = self.extract_info_from_text(pdf_text, file_name_without_ext)
            
            # ⭐ QR KOD BULUNDU ⭐
            if qr_data:
                json_data = self.clean_json(qr_data)
                
                if json_data and not json_data.get('_parse_error'):
                    return {
                        'dosya_adi': file_basename,
                        'dosya_yolu': file_path,
                        'fatura_no_from_filename': file_name_without_ext,
                        'durum': 'BAŞARILI',
                        'json_data': json_data,
                        'extracted_info': extracted_info
                    }
                else:
                    return {
                        'dosya_adi': file_basename,
                        'dosya_yolu': file_path,
                        'fatura_no_from_filename': file_name_without_ext,
                        'durum': 'JSON HATASI',
                        'json_data': json_data,
                        'extracted_info': extracted_info
                    }
            
            # ⭐ QR KOD BULUNAMADI - GELİŞMİŞ PDF METİN TARAMA DEVREDE ⭐
            logging.info(f"   🔍 QR bulunamadı, PDF metin taraması devrede: {file_basename}")
            
            # PDF'den tüm bilgileri çıkar
            if pdf_text:
                # Tarih
                tarih = self._extract_date_from_text(pdf_text)
                
                # Fatura No (PDF'den veya dosya adından)
                fatura_no_pdf = self._extract_invoice_number_from_text(pdf_text)
                fatura_no = fatura_no_pdf if fatura_no_pdf else file_name_without_ext
                
                # Tutarlar (toplam, matrah, KDV)
                amounts = self._extract_amount_from_text(pdf_text)
                
                # Firma, malzeme, miktar (extracted_info'dan)
                firma = extracted_info.get('firma')
                malzeme = extracted_info.get('malzeme')
                miktar = extracted_info.get('miktar')
                
                # En az firma bilgisi olmalı
                if firma or amounts['toplam'] > 0:
                    # Gelişmiş JSON oluştur
                    fallback_json = {
                        'faturaNo': fatura_no,
                        'invoiceDate': tarih,
                        'firma': firma or 'Bilinmeyen Firma',
                        'tip': malzeme or 'Fatura',
                        'miktar': miktar or '',
                        'payableAmount': amounts['toplam'],
                        'taxableAmount': amounts['matrah'],
                        'hesaplanankdv': amounts['kdv'],
                        'kdvOrani': amounts['kdv_yuzdesi'],
                        'currency': 'TRY',
                        '_source': 'PDF_TEXT_EXTRACTION'
                    }
                    
                    logging.info(f"   ✅ PDF'den bilgi çıkarıldı:")
                    logging.info(f"      - Firma: {firma or 'Yok'}")
                    logging.info(f"      - Fatura No: {fatura_no}")
                    logging.info(f"      - Tarih: {tarih}")
                    logging.info(f"      - Toplam: {amounts['toplam']}")
                    logging.info(f"      - Matrah: {amounts['matrah']}")
                    logging.info(f"      - KDV: {amounts['kdv']} ({amounts['kdv_yuzdesi']}%)")
                    
                    return {
                        'dosya_adi': file_basename,
                        'dosya_yolu': file_path,
                        'fatura_no_from_filename': file_name_without_ext,
                        'durum': 'BAŞARILI',
                        'json_data': fallback_json,
                        'extracted_info': extracted_info
                    }
                else:
                    logging.warning(f"   ⚠️ PDF'den yeterli bilgi çıkarılamadı (firma veya tutar yok)")
            
            # Hiçbir bilgi çıkarılamadı
            return {
                'dosya_adi': file_basename,
                'dosya_yolu': file_path,
                'fatura_no_from_filename': file_name_without_ext,
                'durum': 'QR BULUNAMADI',
                'json_data': {},
                'extracted_info': extracted_info
            }
            
        except Exception as e:
            logging.error(f"❌ Dosya işleme hatası ({file_path}): {e}")
            return {
                'dosya_adi': os.path.basename(file_path),
                'dosya_yolu': file_path,
                'fatura_no_from_filename': os.path.splitext(os.path.basename(file_path))[0],
                'durum': 'KRİTİK HATA',
                'json_data': {},
                'extracted_info': {'firma': None, 'malzeme': None, 'miktar': None},
                'hata': str(e)
            }
    
    def process_qr_files_in_folder(self, folder_path, max_workers=6, status_callback=None):
        """Klasördeki tüm dosyaları paralel işle"""
        if not self.tools_loaded:
            self._init_qr_tools()
        
        logging.info(f"🚀 QR klasör işleme başlıyor: {folder_path}")
        
        if status_callback:
            status_callback("📁 Dosyalar taranıyor...", 5)
        
        # Dosyaları topla
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp'}
        file_paths = []
        
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_name)
                    if ext.lower() in allowed_extensions:
                        file_paths.append(file_path)
        except Exception as e:
            logging.error(f"❌ Klasör okuma hatası: {e}")
            return []
        
        if not file_paths:
            logging.warning("⚠️ İşlenebilir dosya bulunamadı")
            return []
        
        logging.info(f"📁 {len(file_paths)} dosya bulundu, {max_workers} thread kullanılacak")
        
        results = []
        completed_count = 0
        start_time = time.time()
        
        # Paralel işleme
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(self.process_file, path): path for path in file_paths}
            
            for future in as_completed(future_to_path):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                    completed_count += 1
                    
                    # İlerleme bildirimi
                    if status_callback and completed_count % 3 == 0:
                        progress = int((completed_count / len(file_paths)) * 95)
                        elapsed = time.time() - start_time
                        rate = completed_count / elapsed if elapsed > 0 else 0
                        
                        if not status_callback(f"İşleniyor: {completed_count}/{len(file_paths)} ({rate:.1f} dosya/s)", progress):
                            # İptal edildi
                            logging.warning("⚠️ Kullanıcı işlemi iptal etti")
                            break
                    
                except Exception as e:
                    file_path = future_to_path[future]
                    logging.error(f"❌ Timeout/Hata: {os.path.basename(file_path)}")
                    results.append({
                        'dosya_adi': os.path.basename(file_path),
                        'durum': 'TIMEOUT',
                        'json_data': {}
                    })
                    completed_count += 1
        
        total_time = time.time() - start_time
        success_count = len([r for r in results if r.get('durum') == 'BAŞARILI'])
        
        # İstatistikler
        logging.info(f"🏁 QR işleme bitti!")
        logging.info(f"📊 Başarılı: {success_count}/{len(results)} (%{(success_count/len(results)*100):.0f})")
        logging.info(f"⏱️  Süre: {total_time:.1f}s, Hız: {len(results)/total_time:.1f} dosya/s")
        logging.info(f"📈 Aşama İstatistikleri:")
        logging.info(f"   • Hızlı (450 DPI): {self.stats['stage1_fast']}")
        logging.info(f"   • Orta (600 DPI): {self.stats['stage2_medium']}")
        logging.info(f"   • Derin (750 DPI): {self.stats['stage3_deep']}")
        logging.info(f"   • Başarısız: {self.stats['failed']}")
        
        if status_callback:
            status_callback("✅ QR işleme tamamlandı!", 100)
        
        return results


# ============================================================================
# QRInvoiceIntegrator - Backend Entegrasyonu + Otomatik Tip Tespiti
# ============================================================================

class QRInvoiceIntegrator:
    """
    QR İŞLEME VE BACKEND ENTEGRASYONU
    - Otomatik fatura tipi tespiti (SATIS/ALIS)
    - Backend ile senkronizasyon
    """
    
    def __init__(self, backend_instance):
        self.backend = backend_instance
        self.qr_processor = OptimizedQRProcessor()
        logging.info("🔗 QRInvoiceIntegrator başlatıldı (optimize edilmiş)")
    
    def process_qr_files_in_folder(self, folder_path, max_workers=6, status_callback=None):
        """Klasördeki dosyaları işle"""
        return self.qr_processor.process_qr_files_in_folder(
            folder_path, 
            max_workers=max_workers,
            status_callback=status_callback
        )
    
    def add_invoices_from_qr_data(self, qr_results, invoice_type):
        """
        QR sonuçlarını veritabanına ekle - MANUEL TİP SEÇİMİ + DUPLICATE KONTROL
        
        Args:
            qr_results: QR işleme sonuçları
            invoice_type: 'outgoing' (gelir) veya 'incoming' (gider) - KULLANICI SEÇİMİ
        
        Returns:
            dict: {
                'success': True,
                'added': int,
                'failed': int,
                'skipped_duplicates': int,
                'total': int,
                'invoice_type': str,
                'processing_details': list,
                'failed_files': list
            }
        """
        if not qr_results:
            logging.warning("QR sonuçları boş!")
            return {
                'success': False,
                'added': 0,
                'failed': 0,
                'skipped_duplicates': 0,
                'total': 0,
                'invoice_type': invoice_type,
                'processing_details': [],
                'failed_files': []
            }
        
        successful_imports = 0
        failed_imports = 0
        skipped_duplicates = 0
        processing_details = []
        failed_files = []
        
        type_text = "GELİR (Satış)" if invoice_type == 'outgoing' else "GİDER (Alış)"
        logging.info(f"🔄 {len(qr_results)} QR sonucu işlenecek (TİP: {type_text} + DUPLICATE KONTROL)")
        
        for i, result in enumerate(qr_results, 1):
            dosya_adi = result.get('dosya_adi', 'Bilinmeyen')
            dosya_yolu = result.get('dosya_yolu', '')
            
            if result.get('durum') == 'BAŞARILI':
                qr_json = result.get('json_data', {})
                extracted_info = result.get('extracted_info', {})
                fatura_no_from_filename = result.get('fatura_no_from_filename', '')
                
                # Fatura alanlarına dönüştür
                parsed_fields = self._parse_qr_to_invoice_fields(qr_json, extracted_info, fatura_no_from_filename)
                
                if not parsed_fields or not parsed_fields.get('firma'):
                    logging.warning(f"   ⚠️ {dosya_adi}: Eksik fatura bilgisi")
                    failed_imports += 1
                    failed_files.append(dosya_yolu)
                    processing_details.append({
                        'file': dosya_adi,
                        'status': 'BAŞARISIZ',
                        'error': 'Firma bilgisi eksik'
                    })
                    continue
                
                # ⭐ DUPLICATE KONTROL ⭐
                fatura_no = parsed_fields.get('fatura_no', '')
                if self._is_duplicate_invoice(fatura_no):
                    skipped_duplicates += 1
                    logging.info(f"   ⏭️  {dosya_adi} -> ATLANDI (Duplicate: {fatura_no})")
                    processing_details.append({
                        'file': dosya_adi,
                        'status': 'ATLANDI (DUPLICATE)',
                        'fatura_no': fatura_no,
                        'error': None
                    })
                    continue
                
                # Backend'e ekle (manuel seçilen tip ile)
                try:
                    logging.info(f"   📝 {dosya_adi} kaydediliyor -> Tip: {invoice_type}, Firma: {parsed_fields.get('firma', 'N/A')[:30]}")
                    
                    result = self.backend.handle_invoice_operation(
                        operation='add',
                        invoice_type=invoice_type,
                        data=parsed_fields
                    )
                    
                    if result:
                        successful_imports += 1
                        logging.info(f"   ✅ {dosya_adi} -> {invoice_type.upper()} olarak KAYDEDİLDİ (Firma: {parsed_fields.get('firma', 'N/A')[:30]})")
                    else:
                        failed_imports += 1
                        failed_files.append(dosya_yolu)
                        logging.error(f"   ❌ {dosya_adi} -> Kaydedilemedi (Backend False döndü)")
                        processing_details.append({
                            'file': dosya_adi,
                            'status': 'BAŞARISIZ',
                            'error': 'Backend False döndü'
                        })
                        continue
                    processing_details.append({
                        'file': dosya_adi,
                        'status': 'BAŞARILI',
                        'type': invoice_type,
                        'fatura_no': fatura_no,
                        'error': None
                    })
                    
                except Exception as e:
                    logging.error(f"   ❌ {dosya_adi}: Veritabanı hatası - {e}")
                    failed_imports += 1
                    failed_files.append(dosya_yolu)
                    processing_details.append({
                        'file': dosya_adi,
                        'status': 'BAŞARISIZ',
                        'error': f'DB hatası: {e}'
                    })
            else:
                failed_imports += 1
                failed_files.append(dosya_yolu)
                processing_details.append({
                    'file': dosya_adi,
                    'status': 'BAŞARISIZ',
                    'error': result.get('durum', 'Bilinmeyen hata')
                })
        
        logging.info(f"\n{'='*60}")
        logging.info(f"✅ İşlem Tamamlandı!")
        logging.info(f"📊 Başarılı: {successful_imports}, Başarısız: {failed_imports}, Duplicate: {skipped_duplicates}")
        logging.info(f"📋 Tip: {invoice_type.upper()}")
        logging.info(f"{'='*60}\n")
        
        # Backend sinyalini tetikle
        self.backend.data_updated.emit()
        
        return {
            'success': True,
            'added': successful_imports,
            'failed': failed_imports,
            'skipped_duplicates': skipped_duplicates,
            'total': len(qr_results),
            'invoice_type': invoice_type,
            'processing_details': processing_details,
            'failed_files': failed_files
        }
    
    def _is_duplicate_invoice(self, fatura_no):
        """Veritabanında aynı fatura no var mı kontrol et"""
        if not fatura_no:
            return False
        
        try:
            # Hem gelir hem gider veritabanında kontrol et
            for db_type in ['outgoing', 'incoming']:
                invoices = self.backend.handle_invoice_operation(
                    operation='get',
                    invoice_type=db_type,
                    limit=None
                )
                
                if invoices:
                    for invoice in invoices:
                        existing_fatura_no = invoice.get('fatura_no', '')
                        if existing_fatura_no and existing_fatura_no == fatura_no:
                            return True
            
            return False
        except Exception as e:
            logging.warning(f"⚠️ Duplicate kontrol hatası: {e}")
            return False
    
    def _detect_invoice_type(self, qr_json, parsed_fields):
        """
        ⭐ OTOMATİK FATURA TİPİ TESPİTİ ⭐
        
        SATIS -> outgoing (gelir)
        ALIS -> incoming (gider)
        """
        # TİP alanına bak (öncelikli)
        tip_field = self._get_value_case_insensitive(qr_json, ['tip', 'type', 'senaryo', 'invoiceType'])
        
        if tip_field:
            tip_upper = str(tip_field).upper()
            
            # SATIS -> GELİR
            if any(keyword in tip_upper for keyword in ['SATIS', 'SATŞ', 'SALE', 'SELLING', 'TEMEL', 'TICARIFATURA']):
                logging.info(f"      🔍 Tip tespiti: SATIS -> GELİR (tip='{tip_field}')")
                return 'outgoing'
            
            # ALIS -> GİDER
            if any(keyword in tip_upper for keyword in ['ALIS', 'ALIŞ', 'PURCHASE', 'BUYING', 'ALIM']):
                logging.info(f"      🔍 Tip tespiti: ALIS -> GİDER (tip='{tip_field}')")
                return 'incoming'
        
        # Malzeme/Açıklama alanına bak
        malzeme = parsed_fields.get('malzeme', '').upper()
        if 'SATIS' in malzeme or 'SATŞ' in malzeme:
            logging.info(f"      🔍 Malzeme tespiti: SATIS -> GELİR")
            return 'outgoing'
        if 'ALIS' in malzeme or 'ALIŞ' in malzeme:
            logging.info(f"      🔍 Malzeme tespiti: ALIS -> GİDER")
            return 'incoming'
        
        # Varsayılan: E-faturalar genelde satış (gelir)
        logging.info(f"      ⚠️ Tip tespit edilemedi, varsayılan: GELİR")
        return 'outgoing'
    
    def _parse_qr_to_invoice_fields(self, qr_json, extracted_info=None, fatura_no_from_filename=''):
        """QR JSON'ını fatura alanlarına dönüştür + OCR bilgisi ekle"""
        if not qr_json:
            return {}
        
        if extracted_info is None:
            extracted_info = {}
        
        # ⭐ DEBUG: QR JSON yapısını logla ⭐
        logging.info(f"   🔍 QR JSON İÇERİĞİ:")
        logging.info(f"      Tüm anahtarlar: {list(qr_json.keys())}")
        
        # Tutar ile ilgili tüm alanları bul
        tutar_related = {}
        for key, value in qr_json.items():
            key_lower = key.lower()
            if any(word in key_lower for word in ['tutar', 'amount', 'total', 'pay', 'matrah', 'tax', 'kdv']):
                tutar_related[key] = value
        
        if tutar_related:
            logging.info(f"      💰 Tutar ile ilgili alanlar: {tutar_related}")
        else:
            logging.warning(f"      ⚠️ Tutar ile ilgili hiçbir alan bulunamadı!")
        
        # Anahtar eşleme sözlüğü
        key_map = {
            'fatura_no': ['faturaNo', 'invoiceNumber', 'faturanumarasi', 'belgeNo', 'documentNo', 'seriNo', 'faturaid', 'belge_no'],
            'irsaliye_no': ['invoiceId', 'irsaliyeNo', 'uuid', 'id', 'no', 'ettn', 'ETTN'],
            'tarih': ['invoiceDate', 'faturaTarihi', 'tarih', 'date', 'issueDate', 'belge_tarihi', 'belgeTarihi'],
            'firma': ['sellerName', 'saticiUnvan', 'firma', 'supplier', 'company', 'companyName', 'buyerName', 'aliciUnvan', 'satici_unvan', 'alici_unvan'],
            'malzeme': ['tip', 'type', 'itemName', 'description', 'malzeme', 'hizmet', 'urun', 'product', 'senaryo', 'aciklama'],
            'miktar': ['quantity', 'miktar', 'adet', 'amount', 'qty', 'mal_hizmet_toplam_tutari'],
            'toplam_tutar': ['payableAmount', 'odenecek', 'totalAmount', 'toplamTutar', 'total', 'tutar', 
                            'odenecekTutar', 'odenecek_tutar', 'toplam', 'hesaplanan_odenecek_tutar',
                            'vergilerDahilToplamTutar', 'vergiler_dahil_toplam_tutar', 'genel_toplam'],
            'matrah': ['taxableAmount', 'matrah', 'netAmount', 'malhizmettoplam', 'mal_hizmet_toplam_tutari',
                      'hesaplanan_kdv_matrah', 'kdv_matrah', 'matrah_toplam'],
            'kdv_tutari': ['taxAmount', 'hesaplanankdv', 'kdv', 'kdvtoplam', 'hesaplanan_kdv', 'kdv_tutari',
                          'toplam_kdv', 'vergi_tutari', 'hesaplanan_kdv_tutari'],
            'kdv_yuzdesi': ['taxRate', 'kdvOrani', 'vatRate', 'kdv_orani', 'oran'],
            'birim': ['currency', 'parabirimi', 'currencyCode', 'para_birimi']
        }
        
        parsed = {}
        
        # ⭐ Fatura No - DOSYA ADINDAN AL (ÖNCELİKLİ) ⭐
        qr_fatura_no = self._get_value_case_insensitive(qr_json, key_map['fatura_no'])
        if fatura_no_from_filename:
            parsed['fatura_no'] = str(fatura_no_from_filename)
            logging.debug(f"   📄 Fatura No dosya adından alındı: {fatura_no_from_filename}")
        elif qr_fatura_no:
            parsed['fatura_no'] = str(qr_fatura_no)
        else:
            parsed['fatura_no'] = ''
        
        # İrsaliye No (zorunlu)
        parsed['irsaliye_no'] = str(self._get_value_case_insensitive(qr_json, key_map['irsaliye_no']) or f"QR-{int(time.time())}")
        
        # Tarih
        qr_tarih = self._get_value_case_insensitive(qr_json, key_map['tarih'])
        parsed['tarih'] = self.backend.format_date(str(qr_tarih)) if qr_tarih else datetime.now().strftime("%d.%m.%Y")
        
        # ⭐ Firma - OCR'DAN AL (QR'da yoksa) ⭐
        firma = self._get_value_case_insensitive(qr_json, key_map['firma'])
        if not firma or (isinstance(firma, str) and firma.isdigit()):
            # QR'da yoksa OCR'dan al
            if extracted_info.get('firma'):
                firma = extracted_info['firma']
                logging.debug(f"   🔍 Firma OCR'dan alındı: {firma}")
            else:
                # Alternatif alanlar
                firma = self._get_value_case_insensitive(qr_json, ['satici', 'alici', 'vkn', 'unvan']) or 'Firma Bilgisi Yok'
        parsed['firma'] = str(firma)
        
        # ⭐ Malzeme - HER ZAMAN OCR'DAN AL (PDF Tablosundan) ⭐
        malzeme = None
        if extracted_info.get('malzeme'):
            malzeme = extracted_info['malzeme']
            logging.debug(f"   🔍 Malzeme OCR'dan alındı: {malzeme}")
        else:
            # OCR'da bulunamadıysa QR'dan deneme yap
            qr_malzeme = self._get_value_case_insensitive(qr_json, key_map['malzeme'])
            if qr_malzeme and qr_malzeme not in ['SATIS', 'ALIS', 'EARSIV', 'TICARIFATURA']:
                malzeme = qr_malzeme
                logging.debug(f"   🔍 Malzeme QR'dan alındı: {malzeme}")
            else:
                malzeme = 'QR Kodlu E-Fatura'
                logging.debug(f"   ⚠️ Malzeme bulunamadı, default kullanıldı")
        parsed['malzeme'] = str(malzeme)
        
        # ⭐ MİKTAR MANTIK GÜNCELLEMESİ ⭐
        # JSON'dan fatura türünü kontrol et
        qr_malzeme_type = self._get_value_case_insensitive(qr_json, key_map['malzeme'])
        is_material_sale = False
        
        if qr_malzeme_type:
            type_upper = str(qr_malzeme_type).upper()
            # Eğer "SATIS" geçiyorsa ve malzeme varsa, bu malzeme satışıdır
            if 'SATIS' in type_upper and extracted_info.get('malzeme'):
                is_material_sale = True
                logging.debug(f"   💡 Fatura türü: Malzeme satışı tespit edildi")
            # "HİZMET" veya "HESAPLANAN" gibi kelimeler varsa hizmet faturası
            elif any(keyword in type_upper for keyword in ['HIZMET', 'HESAPLANAN', 'SERVICE']):
                is_material_sale = False
                logging.debug(f"   💡 Fatura türü: Hizmet faturası tespit edildi")
        
        # Miktar tespiti
        miktar = None
        if is_material_sale:
            # Malzeme satışı - OCR'dan miktar al
            if extracted_info.get('miktar'):
                miktar = extracted_info['miktar']
                logging.debug(f"   🔍 Miktar OCR'dan alındı (malzeme satışı): {miktar}")
            else:
                # OCR'da yoksa QR'dan dene
                qr_miktar = self._get_value_case_insensitive(qr_json, key_map['miktar'])
                if qr_miktar and qr_miktar != '0' and qr_miktar != 0:
                    miktar = qr_miktar
                    logging.debug(f"   🔍 Miktar QR'dan alındı: {miktar}")
        else:
            # Hizmet faturası - miktar boş kalacak
            miktar = ''
            logging.debug(f"   ⚠️ Hizmet faturası - miktar boş bırakıldı")
        
        parsed['miktar'] = str(miktar) if miktar else ''
        
        # Para birimi
        birim = str(self._get_value_case_insensitive(qr_json, key_map['birim']) or 'TRY').upper()
        parsed['birim'] = 'TL' if birim in ['TRY', 'TRL'] else birim
        
        # Tutar hesaplamaları
        toplam = self._to_float(self._get_value_case_insensitive(qr_json, key_map['toplam_tutar']))
        matrah = self._to_float(self._get_value_case_insensitive(qr_json, key_map['matrah']))
        kdv_tutari = self._to_float(self._get_value_case_insensitive(qr_json, key_map['kdv_tutari']))
        kdv_yuzdesi = self._to_float(self._get_value_case_insensitive(qr_json, key_map['kdv_yuzdesi']))
        
        logging.info(f"      📊 Parse edilen değerler:")
        logging.info(f"         - Toplam: {toplam}")
        logging.info(f"         - Matrah: {matrah}")
        logging.info(f"         - KDV Tutarı: {kdv_tutari}")
        logging.info(f"         - KDV %: {kdv_yuzdesi}")
        
        # KDV yüzdesi
        if kdv_yuzdesi > 0:
            parsed['kdv_yuzdesi'] = kdv_yuzdesi
        elif matrah > 0 and kdv_tutari > 0:
            parsed['kdv_yuzdesi'] = round((kdv_tutari / matrah) * 100, 2)
        else:
            parsed['kdv_yuzdesi'] = self.backend.settings.get('kdv_yuzdesi', 20.0)
        
        # Tutar ve KDV hesaplama
        if matrah > 0 and toplam > 0:
            # Hem matrah hem toplam var
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            parsed['kdv_tutari'] = kdv_tutari if kdv_tutari > 0 else round(matrah * parsed['kdv_yuzdesi'] / 100, 2)
            logging.info(f"      ✅ Durum 1: Hem matrah hem toplam var (matrah={matrah}, toplam={toplam})")
        elif toplam > 0:
            # Sadece toplam var
            parsed['toplam_tutar'] = toplam
            if kdv_tutari > 0:
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_dahil'] = False
                parsed['kdv_tutari'] = round(toplam * parsed['kdv_yuzdesi'] / 100, 2)
            logging.info(f"      ✅ Durum 2: Sadece toplam var (toplam={toplam})")
        elif matrah > 0:
            # Sadece matrah var
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            parsed['kdv_tutari'] = kdv_tutari if kdv_tutari > 0 else round(matrah * parsed['kdv_yuzdesi'] / 100, 2)
            logging.info(f"      ✅ Durum 3: Sadece matrah var (matrah={matrah})")
        else:
            # Hiçbiri yok - KRİTİK HATA - QR JSON'u tamamen logla
            logging.error(f"      ❌❌❌ KRİTİK: QR'da hiçbir tutar bilgisi bulunamadı!")
            logging.error(f"      📋 QR JSON tüm içeriği: {json.dumps(qr_json, indent=2, ensure_ascii=False)}")
            # HATA FIRLATMA - Bu fatura atlanacak
            parsed['toplam_tutar'] = None  # Backend bunu reddedecek
            parsed['kdv_dahil'] = False
            parsed['kdv_tutari'] = 0.0
        
        logging.info(f"      💎 Final: Firma={parsed.get('firma', 'N/A')[:30]}, Tutar={parsed.get('toplam_tutar')}, Malzeme={parsed.get('malzeme', 'N/A')[:30]}")
        return parsed
    
    def _get_value_case_insensitive(self, data_dict, keys):
        """Büyük/küçük harf duyarsız anahtar arama"""
        for key in keys:
            if key in data_dict:
                return data_dict[key]
        
        # Lowercase karşılaştırma
        data_lower = {k.lower(): v for k, v in data_dict.items()}
        for key in keys:
            if key.lower() in data_lower:
                return data_lower[key.lower()]
        
        return None
    
    def _to_float(self, value):
        """Güvenli float dönüşümü"""
        if value is None or value == '':
            return 0.0
        
        try:
            # String ise temizle
            if isinstance(value, str):
                value = value.replace(',', '.').replace(' ', '').strip()
                # TL, USD gibi para birimi sembollerini kaldır
                value = re.sub(r'[^\d.-]', '', value)
            
            return float(value)
        except:
            return 0.0
    
    def _extract_date_from_text(self, pdf_text):
        """PDF metninden tarih çıkar - Gelişmiş"""
        if not pdf_text:
            return datetime.now().strftime("%d.%m.%Y")
        
        lines = pdf_text.split('\n')
        
        # Fatura tarihi anahtar kelimeleri
        date_keywords = [
            r'fatura\s*tarih[i]?',
            r'tarih',
            r'date',
            r'düzenlenme\s*tarih[i]?',
            r'belge\s*tarih[i]?'
        ]
        
        # Tarih formatları
        date_patterns = [
            r'(\d{2})[./-](\d{2})[./-](\d{4})',
            r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})'
        ]
        
        # Önce anahtar kelimelerin yakınında ara
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(re.search(keyword, line_lower) for keyword in date_keywords):
                # Bu satır ve sonraki 3 satırda tarih ara
                for j in range(i, min(i+4, len(lines))):
                    for pattern in date_patterns:
                        match = re.search(pattern, lines[j])
                        if match:
                            if len(match.groups()) == 3 and match.group(1).isdigit():
                                date_str = f"{match.group(1).zfill(2)}.{match.group(2).zfill(2)}.{match.group(3)}"
                                logging.debug(f"   📅 Tarih bulundu: {date_str}")
                                return date_str
        
        # Genel tarama
        for pattern in date_patterns:
            match = re.search(pattern, pdf_text)
            if match:
                if len(match.groups()) == 3 and match.group(1).isdigit():
                    date_str = f"{match.group(1).zfill(2)}.{match.group(2).zfill(2)}.{match.group(3)}"
                    logging.debug(f"   📅 Tarih bulundu (genel): {date_str}")
                    return date_str
        
        # Bulunamadıysa bugünün tarihi
        logging.warning(f"   ⚠️ PDF'de tarih bulunamadı, bugün kullanılacak")
        return datetime.now().strftime("%d.%m.%Y")
    
    def _extract_invoice_number_from_text(self, pdf_text):
        """PDF metninden fatura numarası çıkar"""
        if not pdf_text:
            return None
        
        lines = pdf_text.split('\n')
        
        # Fatura no anahtar kelimeleri
        invoice_keywords = [
            r'fatura\s*no',
            r'fatura\s*numaras[ıi]',
            r'invoice\s*number',
            r'belge\s*no',
            r'seri\s*no'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in invoice_keywords:
                if re.search(keyword, line_lower):
                    # Bu satırda veya sonraki 2 satırda fatura no ara
                    for j in range(i, min(i+3, len(lines))):
                        # Fatura no pattern: Harfler ve sayılar
                        invoice_match = re.search(r'([A-Z]{3}\d{12,}|[A-Z0-9]{10,})', lines[j])
                        if invoice_match:
                            invoice_no = invoice_match.group(1)
                            logging.debug(f"   📄 Fatura No: {invoice_no}")
                            return invoice_no
        
        return None
    
    def _extract_amount_from_text(self, pdf_text):
        """PDF metninden tutar çıkar - Gelişmiş (Toplam, Matrah, KDV)"""
        if not pdf_text:
            return {'toplam': 0.0, 'matrah': 0.0, 'kdv': 0.0, 'kdv_yuzdesi': 0.0}
        
        lines = pdf_text.split('\n')
        amounts = {
            'toplam': 0.0,
            'matrah': 0.0,
            'kdv': 0.0,
            'kdv_yuzdesi': 0.0
        }
        
        # TOPLAM TUTAR (Ödenecek, Genel Toplam)
        toplam_keywords = [
            r'ödenecek\s*tutar',
            r'genel\s*toplam',
            r'toplam\s*tutar',
            r'vergiler\s*dahil\s*toplam',
            r'total\s*amount',
            r'payable\s*amount'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in toplam_keywords:
                if re.search(keyword, line_lower):
                    # Bu satırda veya sonraki 2 satırda tutar ara
                    for j in range(i, min(i+3, len(lines))):
                        # Tutar pattern: sayılar, nokta, virgül
                        amount_match = re.search(r'([\d.,]+)\s*(?:TL|₺|EUR|USD)?', lines[j])
                        if amount_match:
                            try:
                                amount_str = amount_match.group(1).replace('.', '').replace(',', '.')
                                amount = float(amount_str)
                                if amount > 10:  # Mantıklı bir tutar
                                    amounts['toplam'] = amount
                                    logging.debug(f"   💰 Toplam tutar: {amount}")
                                    break
                            except:
                                continue
                    if amounts['toplam'] > 0:
                        break
            if amounts['toplam'] > 0:
                break
        
        # MATRAH (KDV Matrahı)
        matrah_keywords = [
            r'kdv\s*matrah[ıi]?',
            r'matrah',
            r'mal\s*hizmet\s*toplam',
            r'vergiden\s*önceki\s*toplam',
            r'net\s*tutar'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in matrah_keywords:
                if re.search(keyword, line_lower):
                    for j in range(i, min(i+3, len(lines))):
                        amount_match = re.search(r'([\d.,]+)\s*(?:TL|₺|EUR|USD)?', lines[j])
                        if amount_match:
                            try:
                                amount_str = amount_match.group(1).replace('.', '').replace(',', '.')
                                amount = float(amount_str)
                                if amount > 0:
                                    amounts['matrah'] = amount
                                    logging.debug(f"   📊 Matrah: {amount}")
                                    break
                            except:
                                continue
                    if amounts['matrah'] > 0:
                        break
            if amounts['matrah'] > 0:
                break
        
        # KDV TUTARI
        kdv_keywords = [
            r'hesaplanan\s*kdv',
            r'kdv\s*tutar[ıi]?',
            r'kdv\s*toplam[ıi]?',
            r'vergi\s*tutar[ıi]?',
            r'tax\s*amount'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in kdv_keywords:
                if re.search(keyword, line_lower):
                    for j in range(i, min(i+3, len(lines))):
                        amount_match = re.search(r'([\d.,]+)\s*(?:TL|₺|EUR|USD)?', lines[j])
                        if amount_match:
                            try:
                                amount_str = amount_match.group(1).replace('.', '').replace(',', '.')
                                amount = float(amount_str)
                                if amount > 0:
                                    amounts['kdv'] = amount
                                    logging.debug(f"   🧾 KDV tutarı: {amount}")
                                    break
                            except:
                                continue
                    if amounts['kdv'] > 0:
                        break
            if amounts['kdv'] > 0:
                break
        
        # KDV YÜZDESİ
        kdv_percent_match = re.search(r'%\s*(\d+)', pdf_text)
        if kdv_percent_match:
            amounts['kdv_yuzdesi'] = float(kdv_percent_match.group(1))
            logging.debug(f"   📈 KDV %: {amounts['kdv_yuzdesi']}")
        elif amounts['matrah'] > 0 and amounts['kdv'] > 0:
            amounts['kdv_yuzdesi'] = round((amounts['kdv'] / amounts['matrah']) * 100, 2)
            logging.debug(f"   📈 KDV % (hesaplanan): {amounts['kdv_yuzdesi']}")
        
        # Tutarları doğrula ve düzelt
        if amounts['toplam'] == 0 and amounts['matrah'] > 0 and amounts['kdv'] > 0:
            amounts['toplam'] = amounts['matrah'] + amounts['kdv']
            logging.debug(f"   ✅ Toplam hesaplandı: {amounts['toplam']}")
        
        if amounts['matrah'] == 0 and amounts['toplam'] > 0 and amounts['kdv'] > 0:
            amounts['matrah'] = amounts['toplam'] - amounts['kdv']
            logging.debug(f"   ✅ Matrah hesaplandı: {amounts['matrah']}")
        
        return amounts


# ============================================================================
# TEST ve STANDALONE KULLANIM
# ============================================================================

if __name__ == "__main__":
    print("🚀 OPTİMİZE EDİLMİŞ QR SİSTEMİ")
    print("=" * 50)
    
    # Standalone test
    processor = OptimizedQRProcessor()
    
    klasor = input("📁 Klasör yolu (boş=mevcut): ").strip() or "."
    
    results = processor.process_qr_files_in_folder(klasor, max_workers=6)
    
    if results:
        successful = len([r for r in results if r.get('durum') == 'BAŞARILI'])
        print(f"\n🎉 İşlem tamamlandı!")
        print(f"📊 Başarılı: {successful}/{len(results)}")
        print(f"📈 İstatistikler:")
        print(f"   • Hızlı: {processor.stats['stage1_fast']}")
        print(f"   • Orta: {processor.stats['stage2_medium']}")
        print(f"   • Derin: {processor.stats['stage3_deep']}")
        print(f"   • Başarısız: {processor.stats['failed']}")
    else:
        print("❌ İşlem başarısız")
