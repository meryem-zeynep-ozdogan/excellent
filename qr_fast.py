import cv2
import json
import pandas as pd
import numpy as np
from pyzbar import pyzbar
import os
from datetime import datetime
import glob
import fitz  # PyMuPDF
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

# Uyarıları kapat - hızlı çalışma için
warnings.filterwarnings("ignore")
cv2.setNumThreads(4)

class FastQRProcessor:
    """HIZLI VE MİNİMAL QR İşlemci (Hata ayıklama eklendi)"""
    
    def __init__(self):
        self.opencv_detector = cv2.QRCodeDetector()
    
    def clean_json(self, qr_text):
        """Hızlı JSON temizleme"""
        if not qr_text or len(qr_text) < 10:
            return {}
        
        import re
        cleaned = qr_text.strip()
        cleaned = re.sub(r',(\s*\n?\s*})', r'\1', cleaned)
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        
        try:
            return json.loads(cleaned)
        except Exception as e:
            print(f"  JSON TEMİZLEME HATASI: {e} - Veri: {cleaned[:50]}...")
            return {"raw_data": cleaned}
    
    def scan_qr_fast(self, img):
        """HIZLI QR tarama - sadece temel yöntemler"""
        h, w = img.shape[:2]
        
        # 1. Sağ üst bölge önce (E-faturaların %70'i burada)
        top_right = img[0:int(h*0.4), int(w*0.6):w]
        if top_right.size > 0:
            try:
                codes = pyzbar.decode(top_right)
                if codes:
                    data = codes[0].data
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', errors='ignore')
                    if len(data) > 10:
                        return data
            except Exception as e:
                print(f"  HATA (pyzbar-bölge): {e}")
        
        # 2. Tam resim pyzbar
        try:
            codes = pyzbar.decode(img)
            if codes:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if len(data) > 10:
                    return data
        except Exception as e:
            print(f"  HATA (pyzbar-tam): {e}")
        
        # 3. Gri ton deneme
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                codes = pyzbar.decode(gray)
                if codes:
                    data = codes[0].data
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', errors='ignore')
                    if len(data) > 10:
                        return data
        except Exception as e:
            print(f"  HATA (pyzbar-gri): {e}")
        
        # 4. OpenCV son deneme
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            data, _, _ = self.opencv_detector.detectAndDecode(gray)
            if data and len(data) > 10:
                return data
        except Exception as e:
            print(f"  HATA (OpenCV): {e}")
        
        return None
    
    def process_pdf(self, pdf_path):
        """HIZLI PDF işleme (Hata ayıklama eklendi)"""
        try:
            doc = fitz.open(pdf_path)
            
            # Sadece ilk sayfa, tek DPI
            page = doc.load_page(0)
            zoom = 450 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            doc.close()
            
            if img is not None:
                return self.scan_qr_fast(img)
            
        except Exception as e:
            # HATAYI GİZLEME, YAZDIR!
            print(f"  ❌ HATA (PDF): {os.path.basename(pdf_path)} işlenemedi. Sebep: {e}")
        
        return None
    
    def process_image(self, image_path):
        """HIZLI resim işleme (Hata ayıklama eklendi)"""
        try:
            img = cv2.imread(image_path)
            if img is not None:
                return self.scan_qr_fast(img)
            else:
                print(f"  ❌ HATA (Resim): {os.path.basename(image_path)} dosyası okunamadı (img is None).")
        except Exception as e:
            # HATAYI GİZLEME, YAZDIR!
            print(f"  ❌ HATA (Resim): {os.path.basename(image_path)} işlenemedi. Sebep: {e}")
        
        return None
    
    def process_file(self, file_path):
        """Tek dosya işleme (Hata ayıklama eklendi)"""
        try:
            file_basename = os.path.basename(file_path)
            
            if file_path.lower().endswith('.pdf'):
                qr_data = self.process_pdf(file_path)
            else:
                qr_data = self.process_image(file_path)
            
            if qr_data:
                json_data = self.clean_json(qr_data)
                if json_data:
                    return {
                        'dosya_adi': file_basename,
                        'durum': 'BAŞARILI',
                        'json_data': json_data
                    }
            
            return {
                'dosya_adi': file_basename,
                'durum': 'HATALI (QR Bulunamadı)',
                'json_data': {}
            }
            
        except Exception as e:
            # KRİTİK HATAYI YAZDIR
            print(f"  ❌ KRİTİK HATA (process_file): {os.path.basename(file_path)}. Sebep: {e}")
            return {
                'dosya_adi': os.path.basename(file_path),
                'durum': 'KRİTİK HATA',
                'json_data': {}
            }

def fatura_bilgilerini_isle_hizli(klasor_yolu=".", cikti_dosyasi="fatura_sonuclari.xlsx", max_workers=6):
    """
    HIZLI fatura işleme - %60 başarı hedefi
    (os.listdir kullanan GÜVENLİ versiyon)
    """
    
    print(f"🚀 HIZLI İŞLEME BAŞLATIYOR")
    print(f"📁 Taranan Klasör: {klasor_yolu}")
    
    # Dosyaları topla (Güvenli yöntem)
    file_paths = []
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.pdf'}
    
    try:
        for file_name in os.listdir(klasor_yolu):
            file_path = os.path.join(klasor_yolu, file_name)
            
            # Sadece dosya olduğundan emin ol (klasörleri atla)
            if os.path.isfile(file_path):
                # Dosya uzantısını al ve küçük harfe çevir
                file_ext_lower = os.path.splitext(file_name)[1].lower()
                
                # İzin verilen uzantılarda mı diye control et
                if file_ext_lower in allowed_extensions:
                    file_paths.append(file_path)
    except Exception as e:
        print(f"❌ Klasör okunurken hata oluştu: {e}")
        return None
        
    file_paths = sorted(list(file_paths))
    
    if not file_paths:
        print("❌ Klasörde izin verilen uzantılara (.pdf, .jpg, .png...) sahip dosya bulunamadı.")
        return None
    
    print(f"📁 Bulunan dosya sayısı: {len(file_paths)}")
    print(f"⚡ Thread: {max_workers}")
    
    processor = FastQRProcessor()
    results = []
    
    start_time = time.time()
    
    # Paralel işleme
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(processor.process_file, path): path 
            for path in file_paths
        }
        
        for i, future in enumerate(as_completed(future_to_path), 1):
            try:
                result = future.result(timeout=30)  # 30 sn timeout
                results.append(result)
                
                if i % 5 == 0 or i == len(file_paths):
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    print(f"📈 {i}/{len(file_paths)} | Hız: {rate:.1f} dosya/s")
                    
            except Exception as e:
                # Timeout veya beklenmedik hata
                file_path = future_to_path[future]
                print(f"❌ '{os.path.basename(file_path)}' işlenirken ciddi hata: {e}")
                results.append({
                    'dosya_adi': os.path.basename(file_path),
                    'durum': 'ÇOK HATALI',
                    'json_data': {}
                })
    
    # --- DÜZELTİLMİŞ EXCEL KAYDETME BÖLÜMÜ ---
    if results:
        # 1. Ana veriyi (json_data hariç) DataFrame'e dönüştür
        #    ve json verisini ayrı bir listede tut
        main_data_list = []
        json_data_list = []
        
        for res in results:
            if 'json_data' in res:
                json_data_list.append(res['json_data'])
                del res['json_data'] # Ana listeden json'ı çıkar
            else:
                json_data_list.append({}) # Eşleşmesi için boş dict ekle
            main_data_list.append(res)

        try:
            df_main = pd.DataFrame(main_data_list)
            
            # 2. JSON verisini ayrı olarak normalize et
            df_json = pd.json_normalize(json_data_list)
            
            # 3. İki DataFrame'i yatay olarak birleştir
            df_final = pd.concat([df_main, df_json], axis=1)

        except Exception as e:
            print(f"❌ Excel verisi birleştirilirken hata (muhtemelen bozuk QR data): {e}")
            print("--- Hata Raporu ---")
            print("JSON verisi (ilk 5 satır):", json_data_list[:5])
            print("--- Rapor Sonu ---")
            # Sadece ana veriyi kaydetmeyi dene
            df_final = pd.DataFrame(main_data_list)
            
        output_path = cikti_dosyasi if cikti_dosyasi.endswith('.xlsx') else f"{cikti_dosyasi}.xlsx"
        try:
            df_final.to_excel(output_path, index=False, engine='openpyxl')
        except Exception as e:
            print(f"❌ Excel dosyasına yazma hatası: {e}")
            return None

        # Sonuç raporu
        total_time = time.time() - start_time
        successful = len(df_final[df_final['durum'] == 'BAŞARILI'])
        accuracy = (successful / len(file_paths)) * 100
        
        print(f"\n✅ İŞLEM BİTTİ!")
        print(f"📊 Başarılı: {successful}/{len(file_paths)} (%{accuracy:.0f})")
        print(f"⏱️ Süre: {total_time:.1f}s")
        print(f"🚀 Hız: {len(file_paths)/total_time:.1f} dosya/s")
        print(f"💾 Dosya: {output_path}")
        
        return df_final
    # --- DÜZELTME SONU ---
    
    return None

if __name__ == "__main__":
    print("🚀 HIZLI QR FATURA SİSTEMİ")
    print("=" * 40)
    
    klasor = input("📁 Klasör (boş=mevcut): ").strip() or "."
    excel = input("💾 Excel dosyası (boş=fatura_sonuclari.xlsx): ").strip() or "fatura_sonuclari.xlsx"
    
    result = fatura_bilgilerini_isle_hizli(klasor, excel)
    
    if result is not None:
        print(f"\n🎉 {len(result)} dosya işlendi!")
    else:
        print("❌ İşlem başarısız")