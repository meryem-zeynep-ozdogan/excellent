# backend.py
# -*- coding: utf-8 -*-

import os
import logging
import sqlite3
import time
import json
import re
import warnings
import fitz  # PyMuPDF
import cv2
import numpy as np
from pyzbar import pyzbar
from datetime import datetime
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# QR işleme için uyarıları kapat
warnings.filterwarnings("ignore")
cv2.setNumThreads(4)
# OpenCV'nin optimize edilmiş fonksiyonlarını kullan
cv2.setUseOptimized(True)

class FastQRProcessor:
    """HIZLI VE MİNİMAL QR İşlemci"""
    
    def __init__(self):
        self.opencv_detector = cv2.QRCodeDetector()
    
    def clean_json(self, qr_text):
        """Geliştirilmiş JSON temizleme ve ayrıştırma"""
        if not qr_text or len(qr_text) < 10:
            return {}
        
        cleaned = qr_text.strip()
        
        # Yaygın JSON hatalarını düzelt
        cleaned = re.sub(r',(\s*\n?\s*[}\]])', r'\1', cleaned)  # Sonda kalan virgülleri sil
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)  # Kontrol karakterlerini sil
        cleaned = re.sub(r'\\x[0-9a-fA-F]{2}', '', cleaned)  # Hex escape karakterlerini sil
        
        # JSON parse dene
        try:
            parsed = json.loads(cleaned)
            logging.info(f"  ✅ JSON başarıyla ayrıştırıldı. Anahtar sayısı: {len(parsed) if isinstance(parsed, dict) else 'Liste'}")
            return parsed
        except json.JSONDecodeError as e:
            logging.warning(f"  ⚠️ JSON Parse Hatası (1. deneme): {e}")
            
            # İkinci deneme: Tek tırnak -> Çift tırnak dönüşümü
            try:
                cleaned_v2 = cleaned.replace("'", '"')
                parsed = json.loads(cleaned_v2)
                logging.info(f"  ✅ JSON 2. denemede ayrıştırıldı (tek tırnak dönüşümü).")
                return parsed
            except:
                pass
            
            # Üçüncü deneme: Key-value çiftlerini manuel parse et
            try:
                kv_pairs = {}
                # Basit key:value eşleşmelerini bul
                pattern = r'["\']?(\w+)["\']?\s*:\s*["\']?([^,"}\]]+)["\']?'
                matches = re.findall(pattern, cleaned)
                for key, value in matches:
                    kv_pairs[key] = value.strip().strip('"').strip("'")
                
                if kv_pairs:
                    logging.info(f"  ⚠️ JSON manuel olarak ayrıştırıldı. {len(kv_pairs)} anahtar bulundu.")
                    return kv_pairs
            except Exception as e2:
                logging.error(f"  ❌ Manuel parse de başarısız: {e2}")
            
            # Hiçbiri işe yaramadıysa ham veriyi döndür
            logging.error(f"  ❌ JSON TEMİZLEME BAŞARISIZ - Ham veri: {cleaned[:100]}...")
            return {"raw_data": cleaned}
    
    def scan_qr_fast(self, img):
        """
        SAĞLAMLAŞTIRILMIŞ QR tarama.
        Düşük kontrast, renkli zemin ve gölgelenme sorunları için
        Adaptif ve Otsu's Eşikleme adımları eklendi.
        """
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
                logging.warning(f"   HATA (pyzbar-bölge): {e}")

        # 2. Tam resim pyzbar (Renkli hali)
        try:
            codes = pyzbar.decode(img)
            if codes:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if len(data) > 10:
                    return data
        except Exception as e:
            logging.warning(f"   HATA (pyzbar-tam): {e}")

        # --- Gelişmiş Ön İşleme Adımları ---
        gray = None
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy() # Zaten gri ise kopyala
            
            codes = pyzbar.decode(gray)
            if codes:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if len(data) > 10:
                    return data
        except Exception as e:
            logging.warning(f"   HATA (pyzbar-gri): {e}")
            try:
                data, _, _ = self.opencv_detector.detectAndDecode(img) # Orijinal resimle dene
                if data and len(data) > 10:
                    return data
            except Exception:
                pass 
            return None

        if gray is None: # Griye çevirme başarısız olduysa devam etme
            return None

        # 4. YENİ ADIM: Adaptif Eşikleme (Düşük kontrast/renkli zemin için ALTIN VURUŞ)
        try:
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            adapt_thresh = cv2.adaptiveThreshold(blur, 255, 
                                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY, 
                                               11, 2)
            
            codes = pyzbar.decode(adapt_thresh)
            if codes:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if len(data) > 10:
                    return data
        except Exception as e:
            logging.warning(f"   HATA (pyzbar-adaptif): {e}")

        # 5. YENİ ADIM: Otsu's Eşikleme (İyi bir genel ikili ayırıcı)
        try:
            _, otsu_thresh = cv2.threshold(gray, 0, 255, 
                                           cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            codes = pyzbar.decode(otsu_thresh)
            if codes:
                data = codes[0].data
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                if len(data) > 10:
                    return data
        except Exception as e:
            logging.warning(f"   HATA (pyzbar-otsu): {e}")

        # 6. OpenCV son deneme
        try:
            data, _, _ = self.opencv_detector.detectAndDecode(gray)
            if data and len(data) > 10:
                return data
        except Exception as e:
            logging.warning(f"   HATA (OpenCV): {e}")

        return None
    
    def process_pdf(self, pdf_path):
        """HIZLI PDF işleme"""
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            # DPI'yı artırarak daha yüksek çözünürlüklü resim elde et
            zoom = 300 / 72.0  # 300 DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            doc.close()
            
            if img is not None:
                return self.scan_qr_fast(img)
            
        except Exception as e:
            logging.error(f"  ❌ HATA (PDF): {os.path.basename(pdf_path)} işlenemedi. Sebep: {e}")
        
        return None
    
    def process_image(self, image_path):
        """HIZLI resim işleme"""
        try:
            img = cv2.imread(image_path)
            if img is not None:
                return self.scan_qr_fast(img)
            else:
                logging.warning(f"  ❌ HATA (Resim): {os.path.basename(image_path)} dosyası okunamadı.")
        except Exception as e:
            logging.error(f"  ❌ HATA (Resim): {os.path.basename(image_path)} işlenemedi. Sebep: {e}")
        
        return None
    
    def process_file(self, file_path):
        """Tek dosya işleme"""
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
            logging.error(f"  ❌ KRİTİK HATA (process_file): {os.path.basename(file_path)}. Sebep: {e}")
            return {
                'dosya_adi': os.path.basename(file_path),
                'durum': 'KRİTİK HATA',
                'json_data': {}
            }

class Database:
    """Veritabanı işlemleri için sınıf."""
    def __init__(self, db_name='excellent_mvp.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Gerekli veritabanı tablolarını oluşturur."""
        try:
            cursor = self.conn.cursor()
            # Giden Faturalar (Gelir)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outgoing_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    irsaliye_no TEXT,
                    tarih TEXT,
                    firma TEXT,
                    malzeme TEXT,
                    miktar TEXT,
                    toplam_tutar_tl REAL,
                    toplam_tutar_usd REAL,
                    toplam_tutar_eur REAL,
                    birim TEXT,
                    kdv_yuzdesi REAL,
                    kdv_tutari REAL,
                    kdv_dahil INTEGER DEFAULT 0
                )
            """)
            # Gelen Faturalar (Gider)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incoming_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    irsaliye_no TEXT,
                    tarih TEXT,
                    firma TEXT,
                    malzeme TEXT,
                    miktar TEXT,
                    toplam_tutar_tl REAL,
                    toplam_tutar_usd REAL,
                    toplam_tutar_eur REAL,
                    birim TEXT,
                    kdv_yuzdesi REAL,
                    kdv_tutari REAL,
                    kdv_dahil INTEGER DEFAULT 0
                )
            """)
            # YENİ: Ayarlar tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # YENİ: Döviz kurları tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    currency TEXT PRIMARY KEY,
                    rate REAL,
                    updated_at TEXT
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Tablo oluşturma hatası: {e}")

    def _execute_query(self, query, params=()):
        """Veritabanı sorgularını çalıştırmak için yardımcı metod."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except sqlite3.Error as e:
            logging.error(f"Sorgu hatası: {e} - Sorgu: {query} - Parametreler: {params}")
            return None

    def add_invoice(self, table_name, data):
        """Belirtilen tabloya fatura ekler."""
        query = f"""
            INSERT INTO {table_name} (irsaliye_no, tarih, firma, malzeme, miktar, toplam_tutar_tl, toplam_tutar_usd, toplam_tutar_eur, birim, kdv_yuzdesi, kdv_tutari, kdv_dahil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get('irsaliye_no'), data.get('tarih'), data.get('firma'),
            data.get('malzeme'), data.get('miktar'), data.get('toplam_tutar_tl'),
            data.get('toplam_tutar_usd'), data.get('toplam_tutar_eur'), data.get('birim'),
            data.get('kdv_yuzdesi', 0), data.get('kdv_tutari', 0), data.get('kdv_dahil', 0)
        )
        cursor = self._execute_query(query, params)
        return cursor.lastrowid if cursor else None

    def update_invoice(self, table_name, invoice_id, data):
        """Belirtilen tablodaki faturayı günceller."""
        query = f"""
            UPDATE {table_name} SET
            irsaliye_no = ?, tarih = ?, firma = ?, malzeme = ?, miktar = ?, 
            toplam_tutar_tl = ?, toplam_tutar_usd = ?, toplam_tutar_eur = ?, birim = ?, kdv_yuzdesi = ?, kdv_tutari = ?, kdv_dahil = ?
            WHERE id = ?
        """
        params = (
            data.get('irsaliye_no'), data.get('tarih'), data.get('firma'), 
            data.get('malzeme'), data.get('miktar'), data.get('toplam_tutar_tl'),
            data.get('toplam_tutar_usd'), data.get('toplam_tutar_eur'), data.get('birim'),
            data.get('kdv_yuzdesi', 0), data.get('kdv_tutari', 0), data.get('kdv_dahil', 0), invoice_id
        )
        self._execute_query(query, params)
        return True # Başarı durumu

    def delete_invoice(self, table_name, invoice_id):
        """Belirtilen tablodan fatura siler."""
        query = f"DELETE FROM {table_name} WHERE id = ?"
        cursor = self._execute_query(query, (invoice_id,))
        return cursor.rowcount if cursor else 0

    def delete_multiple_invoices(self, table_name, invoice_ids):
        """Belirtilen tablodan çoklu fatura siler."""
        if not invoice_ids:
            return 0
        
        placeholders = ','.join(['?' for _ in invoice_ids])
        query = f"DELETE FROM {table_name} WHERE id IN ({placeholders})"
        cursor = self._execute_query(query, invoice_ids)
        
        return cursor.rowcount if cursor else 0

    def get_all_invoices(self, table_name, limit=None, offset=0):
        """Belirtilen tablodaki tüm faturaları getirir (sayfalama destekli)."""
        if limit:
            query = f"SELECT * FROM {table_name} ORDER BY tarih DESC LIMIT {limit} OFFSET {offset}"
        else:
            query = f"SELECT * FROM {table_name} ORDER BY tarih DESC"
        cursor = self._execute_query(query)
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
    
    def get_invoice_count(self, table_name):
        """Tablodaki toplam fatura sayısını döndürür."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        cursor = self._execute_query(query)
        if cursor:
            return cursor.fetchone()[0]
        return 0

    def get_invoice_by_id(self, table_name, invoice_id):
        """Belirtilen tablodan ID'ye göre tek bir fatura getirir."""
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        cursor = self._execute_query(query, (invoice_id,))
        if cursor:
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None

    # --- Ayarlar ve Kur Yönetimi ---
    def get_setting(self, key):
        query = "SELECT value FROM settings WHERE key = ?"
        cursor = self._execute_query(query, (key,))
        if cursor:
            result = cursor.fetchone()
            return result[0] if result else None
        return None

    def save_setting(self, key, value):
        query = "REPLACE INTO settings (key, value) VALUES (?, ?)"
        self._execute_query(query, (key, str(value)))
        return True

    def get_all_settings(self):
        query = "SELECT key, value FROM settings"
        cursor = self._execute_query(query)
        return dict(cursor.fetchall()) if cursor else {}

    def save_exchange_rates(self, rates):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for currency, rate in rates.items():
            query = "REPLACE INTO exchange_rates (currency, rate, updated_at) VALUES (?, ?, ?)"
            self._execute_query(query, (currency, rate, current_time))
        return True

    def load_exchange_rates(self):
        query = "SELECT currency, rate FROM exchange_rates"
        cursor = self._execute_query(query)
        return dict(cursor.fetchall()) if cursor else {}


class Backend(QObject):
    """Uygulamanın ana iş mantığını yöneten sınıf."""
    data_updated = pyqtSignal()
    status_updated = pyqtSignal(str, int)

    def __init__(self, parent=None):
        """
        Backend başlatıcısı.
        QTimer gibi Qt bileşenlerinin doğru çalışması için bir 'parent' alabilir.
        """
        super().__init__(parent)
        self.db = Database()
        self.settings = self.db.get_all_settings()
        self.exchange_rates = {}
        self.qr_processor = FastQRProcessor()
        
        # Kurları başlangıçta bir kez çek, zamanlayıcıyı daha sonra başlat.
        self.update_exchange_rates()

    def start_timers(self):
        """
        Uygulama döngüsü başladıktan sonra çağrılacak zamanlayıcıları başlatır.
        Bu, QTimer'ın QApplication örneği oluşturulduktan sonra başlamasını garanti eder.
        """
        # Ayarları 5 dakikada bir güncelle
        self.rate_update_timer = QTimer(self) # self'i parent olarak ata
        self.rate_update_timer.timeout.connect(self.update_exchange_rates)
        self.rate_update_timer.start(300000) # 5 dakika
        print("INFO: Kur güncelleme zamanlayıcısı başlatıldı.")

    def update_exchange_rates(self):
        """Döviz kurlarını birden fazla kaynaktan çekmeye çalışır."""
        
        # Önce TCMB'den deneyelim
        if self._fetch_from_tcmb():
            return
        
        # TCMB başarısız olursa alternatif API'leri deneyelim
        if self._fetch_from_exchangerate_api():
            return
        
        # Tüm kaynaklar başarısız olursa son güncelleme tarihli kurları veritabanından yükle
        if self._load_rates_from_db():
            self.status_updated.emit("Son kaydedilen döviz kurları kullanılıyor.", 4000)
            return
        
        # Hiçbir kaynak yoksa gerçekçi varsayılan değerleri kullan
        logging.warning("Tüm döviz kuru kaynakları başarısız. Varsayılan kurlar kullanılıyor.")
        self.exchange_rates = {'USD': 0.030, 'EUR': 0.028}  # Yaklaşık güncel kurlar (2024 sonu)
        self.status_updated.emit("İnternet bağlantısı yok! Varsayılan kurlar kullanılıyor.", 5000)
    
    def _fetch_from_tcmb(self):
        """TCMB'den döviz kurlarını çeker."""
        try:
            url = "https://www.tcmb.gov.tr/kurlar/today.xml"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            tree = ET.fromstring(response.content)
            
            usd_sell = None
            eur_sell = None
            
            for currency in tree.findall('./Currency'):
                currency_code = currency.get('Kod')
                if currency_code == 'USD':
                    # Önce BanknoteSelling, yoksa ForexSelling dene
                    usd_sell_node = currency.find('BanknoteSelling') or currency.find('ForexSelling')
                    usd_sell = float(usd_sell_node.text.replace(',', '.'))
                elif currency_code == 'EUR':
                    eur_sell_node = currency.find('BanknoteSelling') or currency.find('ForexSelling')
                    eur_sell = float(eur_sell_node.text.replace(',', '.'))
            
            if usd_sell and eur_sell:
                usd_rate = 1.0 / usd_sell
                eur_rate = 1.0 / eur_sell
                self.exchange_rates = {'USD': usd_rate, 'EUR': eur_rate}
                self._save_rates_to_db()  # Kurları veritabanına kaydet
                self.status_updated.emit("TCMB döviz kurları güncellendi.", 3000)
                logging.info(f"TCMB kurları: 1 USD = {usd_sell:.4f} TL, 1 EUR = {eur_sell:.4f} TL")
                return True
        except Exception as e:
            logging.error(f"TCMB'den kur alınamadı: {e}")
        return False
    
    def _fetch_from_exchangerate_api(self):
        """ExchangeRate-API'den döviz kurlarını çeker (ücretsiz, API key gerektirmez)."""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/TRY"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if 'rates' in data:
                usd_rate = data['rates'].get('USD', 0)
                eur_rate = data['rates'].get('EUR', 0)
                
                if usd_rate > 0 and eur_rate > 0:
                    self.exchange_rates = {'USD': usd_rate, 'EUR': eur_rate}
                    self._save_rates_to_db()
                    self.status_updated.emit("Döviz kurları alternatif kaynaktan güncellendi.", 3000)
                    logging.info(f"ExchangeRate-API kurları: 1 TRY = {usd_rate:.6f} USD, 1 TRY = {eur_rate:.6f} EUR")
                    return True
        except Exception as e:
            logging.error(f"ExchangeRate-API'den kur alınamadı: {e}")
        return False
    
    def _save_rates_to_db(self):
        """Güncel döviz kurlarını veritabanına kaydeder."""
        try:
            self.db.save_exchange_rates(self.exchange_rates)
        except Exception as e:
            logging.error(f"Kurları veritabanına kaydetme hatası: {e}")
    
    def _load_rates_from_db(self):
        """Veritabanından son kaydedilen kurları yükler."""
        try:
            rates = self.db.load_exchange_rates()
            if rates:
                self.exchange_rates = rates
                logging.info(f"Veritabanından yüklenen kurlar: {self.exchange_rates}")
                return True
        except Exception as e:
            logging.error(f"Veritabanından kur yükleme hatası: {e}")
        return False

    def convert_currency(self, amount, from_currency, to_currency):
        """
        Para birimleri arasında dönüşüm yapar.
        TL ve TRY'yi eşdeğer kabul eder.
        """
        if not amount:
            return 0.0
        
        # Para birimlerini normalize et (TL -> TRY)
        from_currency = self._normalize_currency(from_currency)
        to_currency = self._normalize_currency(to_currency)
        
        # Aynı para birimleri
        if from_currency == to_currency:
            return amount
        
        # TRY'den diğerlerine
        if from_currency == 'TRY':
            rate = self.exchange_rates.get(to_currency)
            return amount * rate if rate else 0.0
        
        # Diğerlerinden TRY'ye
        if to_currency == 'TRY':
            rate = self.exchange_rates.get(from_currency)
            return amount / rate if rate else 0.0
        
        # USD <-> EUR gibi çapraz kur dönüşümleri
        try_amount = self.convert_currency(amount, from_currency, 'TRY')
        return self.convert_currency(try_amount, 'TRY', to_currency)
    
    def _normalize_currency(self, currency):
        """Para birimi kodunu normalize eder (TL -> TRY)."""
        if not currency:
            return 'TRY'
        
        currency = str(currency).upper().strip()
        
        # Türk Lirası varyasyonlarını TRY'ye çevir
        if currency in ['TL', 'TRL', 'TÜRK LİRASI', 'TURK LIRASI', 'TURKISH LIRA']:
            return 'TRY'
        
        return currency

    def format_date(self, date_str):
        """Tarih string'ini 'dd.mm.yyyy' formatına çevirir."""
        if not date_str or not isinstance(date_str, str):
             return datetime.now().strftime("%d.%m.%Y")
        
        # Olası ayırıcıları temizle
        cleaned_date = re.sub(r'[^0-9]', '', date_str)
        
        if len(cleaned_date) == 8: # ggmmyyyy formatı
            return f"{cleaned_date[:2]}.{cleaned_date[2:4]}.{cleaned_date[4:]}"

        # Diğer formatları dene
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        # Hiçbiri uymuyorsa bugünün tarihini döndür
        return datetime.now().strftime("%d.%m.%Y")

    def _process_invoice_data(self, invoice_data):
        """
        Fatura verilerini işler, doğrular ve KDV/kur hesaplamalarını yapar.
        GELİŞTİRİLMİŞ KDV HESAPLAMA LOJİĞİ ile manuel ve QR entegrasyonu.
        """
        required_fields = ['irsaliye_no', 'firma', 'malzeme']
        if not all(invoice_data.get(field, '').strip() for field in required_fields):
            logging.warning(f"Eksik zorunlu alanlar: {invoice_data}")
            return None
        
        try:            
            processed = invoice_data.copy()
            processed['tarih'] = self.format_date(processed.get('tarih', ''))
            processed['miktar'] = str(processed.get('miktar', '')).strip()
            
            # Güvenli float dönüşümü
            toplam_tutar = self._to_float(processed.get('toplam_tutar', 0))
            kdv_yuzdesi = self._to_float(processed.get('kdv_yuzdesi', 0))
            kdv_tutari_input = self._to_float(processed.get('kdv_tutari', 0))  # Kullanıcı KDV tutarı girdiyse
            kdv_dahil = 1 if processed.get('kdv_dahil', False) else 0
            birim = processed.get('birim', 'TL')
            
            logging.info(f"\n  💼 MANUEL FATURA İŞLEME BAŞLADI")
            logging.info(f"  📥 Giriş Verileri:")
            logging.info(f"     - Toplam Tutar: {toplam_tutar} {birim}")
            logging.info(f"     - KDV %: {kdv_yuzdesi}")
            logging.info(f"     - KDV Tutarı (input): {kdv_tutari_input} {birim}")
            logging.info(f"     - KDV Dahil: {'EVET' if kdv_dahil else 'HAYIR'}")
            
            # KDV yüzdesi kontrolü
            if kdv_yuzdesi <= 0:
                kdv_yuzdesi = self.settings.get('kdv_yuzdesi', 20.0)
                logging.info(f"  ⚙️ KDV yüzdesi girilmedi, varsayılan kullanılıyor: {kdv_yuzdesi}%")
            
            # === GELİŞTİRİLMİŞ KDV HESAPLAMA LOJİĞİ ===
            matrah = 0.0
            kdv_tutari = 0.0
            
            # SENARYO 1: Kullanıcı hem tutar hem de KDV tutarı girdiyse
            if toplam_tutar > 0 and kdv_tutari_input > 0:
                if kdv_dahil:
                    # KDV dahil tutar ve KDV tutarı verilmiş → Matrah = Toplam - KDV
                    matrah = toplam_tutar - kdv_tutari_input
                    kdv_tutari = kdv_tutari_input
                    
                    # KDV yüzdesini kontrol et ve gerekirse güncelle
                    hesaplanan_kdv_yuzdesi = (kdv_tutari / matrah) * 100 if matrah > 0 else kdv_yuzdesi
                    if abs(hesaplanan_kdv_yuzdesi - kdv_yuzdesi) > 0.5:  # %0.5'ten fazla fark varsa
                        logging.warning(f"  ⚠️ KDV yüzdesi tutarsızlığı! Girilen: {kdv_yuzdesi}%, Hesaplanan: {hesaplanan_kdv_yuzdesi:.2f}%")
                        kdv_yuzdesi = round(hesaplanan_kdv_yuzdesi, 2)
                    
                    logging.info(f"  ✅ SENARYO 1a: KDV Dahil + KDV Tutarı Girildi")
                    logging.info(f"     - Matrah: {matrah:.2f} {birim}")
                    logging.info(f"     - KDV Tutarı: {kdv_tutari:.2f} {birim}")
                    logging.info(f"     - Toplam (KDV Dahil): {toplam_tutar:.2f} {birim}")
                else:
                    # KDV hariç tutar (matrah) ve KDV tutarı verilmiş
                    matrah = toplam_tutar
                    kdv_tutari = kdv_tutari_input
                    
                    # KDV yüzdesini kontrol et
                    hesaplanan_kdv_yuzdesi = (kdv_tutari / matrah) * 100 if matrah > 0 else kdv_yuzdesi
                    if abs(hesaplanan_kdv_yuzdesi - kdv_yuzdesi) > 0.5:
                        logging.warning(f"  ⚠️ KDV yüzdesi tutarsızlığı! Girilen: {kdv_yuzdesi}%, Hesaplanan: {hesaplanan_kdv_yuzdesi:.2f}%")
                        kdv_yuzdesi = round(hesaplanan_kdv_yuzdesi, 2)
                    
                    logging.info(f"  ✅ SENARYO 1b: KDV Hariç + KDV Tutarı Girildi")
                    logging.info(f"     - Matrah: {matrah:.2f} {birim}")
                    logging.info(f"     - KDV Tutarı: {kdv_tutari:.2f} {birim}")
                    logging.info(f"     - Toplam (KDV Dahil): {(matrah + kdv_tutari):.2f} {birim}")
            
            # SENARYO 2: Sadece toplam tutar girildi (KDV tutarı yok)
            elif toplam_tutar > 0:
                if kdv_dahil:
                    # Girilen tutar KDV dahildir, matrah ve KDV'yi ayır
                    kdv_katsayisi = 1 + (kdv_yuzdesi / 100)
                    matrah = toplam_tutar / kdv_katsayisi
                    kdv_tutari = toplam_tutar - matrah
                    
                    logging.info(f"  ✅ SENARYO 2a: Sadece KDV Dahil Tutar Girildi")
                    logging.info(f"     - Girilen (KDV Dahil): {toplam_tutar:.2f} {birim}")
                    logging.info(f"     - Hesaplanan Matrah: {matrah:.2f} {birim}")
                    logging.info(f"     - Hesaplanan KDV: {kdv_tutari:.2f} {birim} (%{kdv_yuzdesi})")
                else:
                    # Girilen tutar matrah (KDV hariç), KDV'yi hesapla
                    matrah = toplam_tutar
                    kdv_tutari = matrah * (kdv_yuzdesi / 100)
                    
                    logging.info(f"  ✅ SENARYO 2b: Sadece KDV Hariç Tutar (Matrah) Girildi")
                    logging.info(f"     - Matrah: {matrah:.2f} {birim}")
                    logging.info(f"     - Hesaplanan KDV: {kdv_tutari:.2f} {birim} (%{kdv_yuzdesi})")
                    logging.info(f"     - Toplam (KDV Dahil): {(matrah + kdv_tutari):.2f} {birim}")
            
            # SENARYO 3: Tutar girilmedi (hata durumu)
            else:
                logging.error(f"  ❌ HATA: Toplam tutar girilmemiş!")
                return None
            
            # Para birimi dönüşümleri (Matrah üzerinden)
            matrah_tl = self.convert_currency(matrah, birim, 'TRY')
            kdv_tutari_tl = self.convert_currency(kdv_tutari, birim, 'TRY')

            # İşlenmiş veriyi hazırla
            processed['toplam_tutar_tl'] = matrah_tl  # Veritabanına matrah (KDV hariç) kaydedilir
            processed['toplam_tutar_usd'] = self.convert_currency(matrah_tl, 'TRY', 'USD')
            processed['toplam_tutar_eur'] = self.convert_currency(matrah_tl, 'TRY', 'EUR')
            
            processed['birim'] = birim  # Para birimini koru
            processed['kdv_yuzdesi'] = kdv_yuzdesi
            processed['kdv_dahil'] = kdv_dahil
            processed['kdv_tutari'] = kdv_tutari_tl  # KDV tutarı TL cinsinden
            
            # Sonuç özeti
            logging.info(f"  📊 İŞLEME SONUCU:")
            logging.info(f"     - Matrah (TL): {matrah_tl:.2f} TL")
            logging.info(f"     - KDV Tutarı (TL): {kdv_tutari_tl:.2f} TL")
            logging.info(f"     - KDV Yüzdesi: %{kdv_yuzdesi}")
            logging.info(f"     - Genel Toplam (KDV Dahil): {(matrah_tl + kdv_tutari_tl):.2f} TL")
            logging.info(f"  ✅ İşlem başarılı!\n")
            
            return processed

        except (ValueError, TypeError) as e:
            logging.error(f"❌ Fatura veri işleme hatası: {e} - Veri: {invoice_data}")
            return None

    def handle_invoice_operation(self, operation, invoice_type, data=None, record_id=None, limit=None, offset=None):
        """Frontend için tekil fatura işlem merkezi."""
        table_name = f"{invoice_type}_invoices"
        
        if operation == 'add':
            processed_data = self._process_invoice_data(data)
            if processed_data and self.db.add_invoice(table_name, processed_data):
                self.status_updated.emit("Fatura başarıyla eklendi.", 3000)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'update':
            processed_data = self._process_invoice_data(data)
            if processed_data and self.db.update_invoice(table_name, record_id, processed_data):
                self.status_updated.emit("Fatura başarıyla güncellendi.", 3000)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'delete':
            if self.db.delete_invoice(table_name, record_id):
                self.status_updated.emit("Fatura silindi.", 3000)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'get':
            return self.db.get_all_invoices(table_name, limit=limit, offset=offset)
        
        elif operation == 'count':
            return self.db.get_invoice_count(table_name)
        
        elif operation == 'get_by_id':
            return self.db.get_invoice_by_id(table_name, record_id)
        
        logging.warning(f"Geçersiz fatura operasyonu: {operation}")
        return False

    def delete_multiple_invoices(self, invoice_type, invoice_ids):
        """Çoklu fatura silme işlemi."""
        table_name = f"{invoice_type}_invoices"
        try:
            deleted_count = self.db.delete_multiple_invoices(table_name, invoice_ids)
            if deleted_count > 0:
                self.status_updated.emit(f"{deleted_count} fatura silindi.", 3000)
                self.data_updated.emit()
            return deleted_count
        except Exception as e:
            logging.error(f"Çoklu {invoice_type} faturası silme hatası: {e}")
            return 0

    def get_summary_data(self):
        """Gelir, gider ve kar/zarar özetini hesaplar (SQL ile optimize edildi)."""
        # SQL ile toplam hesapla (çok daha hızlı!)
        cursor = self.db.conn.cursor()
        
        # Toplam gelir
        cursor.execute("SELECT SUM(toplam_tutar_tl) FROM outgoing_invoices")
        total_revenue = cursor.fetchone()[0] or 0
        
        # Toplam gider
        cursor.execute("SELECT SUM(toplam_tutar_tl) FROM incoming_invoices")
        total_expense = cursor.fetchone()[0] or 0
        
        # Aylık dağılım için SQL kullan
        monthly_income = [0] * 12
        monthly_expenses = [0] * 12
        current_year = datetime.now().year
        
        # Gelir aylık dağılım (sadece bu yıl)
        cursor.execute("""
            SELECT tarih, toplam_tutar_tl FROM outgoing_invoices 
            WHERE tarih LIKE ?
        """, (f"%.{current_year}",))
        
        for row in cursor.fetchall():
            try:
                parts = row[0].split('.')
                if len(parts) == 3:
                    month = int(parts[1]) - 1
                    monthly_income[month] += row[1]
            except:
                continue
        
        # Gider aylık dağılım (sadece bu yıl)
        cursor.execute("""
            SELECT tarih, toplam_tutar_tl FROM incoming_invoices 
            WHERE tarih LIKE ?
        """, (f"%.{current_year}",))
        
        for row in cursor.fetchall():
            try:
                parts = row[0].split('.')
                if len(parts) == 3:
                    month = int(parts[1]) - 1
                    monthly_expenses[month] += row[1]
            except:
                continue
        
        # Aylık ortalama
        active_income_months = sum(1 for income in monthly_income if income > 0)
        total_income_this_year = sum(monthly_income)
        monthly_average = total_income_this_year / active_income_months if active_income_months > 0 else 0
        
        # Net kar
        net_profit = total_revenue - total_expense

        return {
            "son_gelirler": total_revenue,
            "toplam_giderler": total_expense,
            "net_kar": net_profit,
            "aylik_ortalama": monthly_average,
        }, {
            "income": monthly_income,
            "expenses": monthly_expenses
        }
        
    def get_year_range(self):
        """Fatura verilerinde bulunan tüm yılların listesini döndürür."""
        years_set = set()
        current_year = datetime.now().year
        
        # Varsayılan olarak en az içinde bulunduğumuz yılı ekle
        years_set.add(str(current_year))
        
        # Tüm fatura tablolarından tarih verilerini topla
        for invoice_type in ['outgoing', 'incoming']:
            invoices = self.db.get_all_invoices(f"{invoice_type}_invoices")
            for inv in invoices:
                try:
                    if 'tarih' in inv and inv['tarih']:
                        date_obj = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                        years_set.add(str(date_obj.year))
                except (ValueError, KeyError):
                    continue
        
        # Yılları sıralayıp liste olarak döndür
        return sorted(list(years_set), reverse=True)

    def get_calculations_for_year(self, year):
        """Belirli bir yıl için aylık ve çeyrek dönem hesaplamaları (SQL ile optimize edildi)."""
        cursor = self.db.conn.cursor()
        tax_rate = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0) / 100.0
        
        # Aylık sonuçlar - SQL ile topla
        monthly_results = []
        for month in range(1, 13):
            # Gelir
            cursor.execute("""
                SELECT SUM(toplam_tutar_tl), SUM(kdv_tutari) 
                FROM outgoing_invoices 
                WHERE tarih LIKE ?
            """, (f"%.{month:02d}.{year}",))
            out_row = cursor.fetchone()
            kesilen = out_row[0] or 0
            kesilen_kdv = out_row[1] or 0
            
            # Gider
            cursor.execute("""
                SELECT SUM(toplam_tutar_tl), SUM(kdv_tutari) 
                FROM incoming_invoices 
                WHERE tarih LIKE ?
            """, (f"%.{month:02d}.{year}",))
            in_row = cursor.fetchone()
            gelen = in_row[0] or 0
            gelen_kdv = in_row[1] or 0
            
            monthly_results.append({
                'kesilen': kesilen,
                'gelen': gelen,
                'kdv': kesilen_kdv - gelen_kdv
            })
        
        # Çeyrek dönem sonuçları
        quarterly_results = []
        cumulative_profit = 0
        for quarter in range(4):
            start_month_idx = quarter * 3
            end_month_idx = start_month_idx + 3
            
            period_income = sum(m['kesilen'] for m in monthly_results[start_month_idx:end_month_idx])
            period_expense = sum(m['gelen'] for m in monthly_results[start_month_idx:end_month_idx])
            
            cumulative_profit += (period_income - period_expense)
            
            # Geçici vergi, kümülatif kâr üzerinden hesaplanır
            tax_for_period = cumulative_profit * tax_rate if cumulative_profit > 0 else 0
            
            # Önceki dönemlerde ödenen vergiyi düş
            paid_tax_in_previous_quarters = sum(q.get('vergi', 0) for q in quarterly_results)
            payable_tax = tax_for_period - paid_tax_in_previous_quarters
            
            quarterly_results.append({
                'kar': cumulative_profit, 
                'vergi': tax_for_period,
                'odenecek_kv': payable_tax if payable_tax > 0 else 0
            })
        
        return monthly_results, quarterly_results
    
    def get_yearly_summary(self, year):
        """Belirli bir yıl için yıllık özet (SQL ile optimize edildi)."""
        cursor = self.db.conn.cursor()
        
        # Gelir toplamı
        cursor.execute("""
            SELECT SUM(toplam_tutar_tl) FROM outgoing_invoices 
            WHERE tarih LIKE ?
        """, (f"%.{year}",))
        gelir = cursor.fetchone()[0] or 0
        
        # Gider toplamı
        cursor.execute("""
            SELECT SUM(toplam_tutar_tl) FROM incoming_invoices 
            WHERE tarih LIKE ?
        """, (f"%.{year}",))
        gider = cursor.fetchone()[0] or 0
        
        brut_kar = gelir - gider
        
        # Vergi hesapla
        tax_rate = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0) / 100
        vergi = brut_kar * tax_rate if brut_kar > 0 else 0
        
        return {
            'toplam_gelir': gelir,
            'toplam_gider': gider,
            'yillik_kar': brut_kar - vergi, # Net kar
            'vergi_tutari': vergi,
            'vergi_yuzdesi': tax_rate * 100
        }
    
    def _is_in_month_year(self, date_str, month, year):
        """Tarihin belirtilen ay ve yılda olup olmadığını kontrol eder."""
        try:
            if not date_str: return False
            # Manuel parse (locale sorunu önleme)
            parts = date_str.split('.')
            if len(parts) == 3:
                return int(parts[1]) == month and int(parts[2]) == year
            return False
        except (ValueError, IndexError):
            return False
    
    def _is_in_year(self, date_str, year):
        """Tarihin belirtilen yılda olup olmadığını kontrol eder."""
        try:
            if not date_str: return False
            # Manuel parse (locale sorunu önleme)
            parts = date_str.split('.')
            if len(parts) == 3:
                return int(parts[2]) == year
            return False
        except (ValueError, IndexError):
            return False
    
    def export_to_excel(self, file_path, sheets_data):
        """Verilen verileri bir Excel dosyasına aktarır."""
        try:
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                for sheet_name, content in sheets_data.items():
                    df = pd.DataFrame(content.get("data", []))
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            self.status_updated.emit(f"Veriler '{os.path.basename(file_path)}' dosyasına aktarıldı.", 5000)
            return True
        except Exception as e:
            logging.error(f"Excel'e aktarma hatası: {e}")
            self.status_updated.emit("Excel'e aktarma başarısız oldu!", 5000)
            return False

    # --- QR KOD İŞLEME VE ENTEGRASYON ---
    def process_qr_files_in_folder(self, folder_path, max_workers=6):
        """
        Bir klasördeki dosyaları paralel olarak işler ve QR kod verilerini döndürür.
        Bu fonksiyon artık veritabanına yazma işlemi yapmaz, sadece okur ve sonuçları döner.
        """
        logging.info(f"🚀 QR Klasör İşleme Başlatılıyor: {folder_path}")
        
        file_paths = []
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.pdf'}
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path) and os.path.splitext(file_name)[1].lower() in allowed_extensions:
                    file_paths.append(file_path)
        except Exception as e:
            logging.error(f"❌ Klasör okunurken hata oluştu: {e}")
            return None
        
        if not file_paths:
            logging.warning("❌ Klasörde işlenecek dosya bulunamadı.")
            return []

        logging.info(f"📁 Bulunan dosya sayısı: {len(file_paths)}, Thread sayısı: {max_workers}")
        
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(self.qr_processor.process_file, path): path for path in file_paths}
            
            for i, future in enumerate(as_completed(future_to_path), 1):
                try:
                    result = future.result(timeout=45) # Timeout artırıldı
                    results.append(result)
                    if i % 5 == 0 or i == len(file_paths):
                        elapsed = time.time() - start_time
                        rate = i / elapsed if elapsed > 0 else 0
                        logging.info(f"📈 İlerleme: {i}/{len(file_paths)} | Hız: {rate:.1f} dosya/s")
                except Exception as e:
                    file_path = future_to_path[future]
                    logging.error(f"❌ '{os.path.basename(file_path)}' işlenirken ciddi hata: {e}")
                    results.append({'dosya_adi': os.path.basename(file_path), 'durum': 'KRİTİK HATA', 'json_data': {}})
        
        logging.info(f"🏁 QR İşleme Tamamlandı. Toplam süre: {time.time() - start_time:.2f}s")
        return results

    def add_invoices_from_qr_data(self, qr_results, invoice_type):
        """
        İşlenmiş QR sonuç listesini alır ve fatura olarak veritabanına ekler.
        """
        if not qr_results:
            logging.warning("QR sonuçları boş!")
            return 0, 0

        successful_imports = 0
        failed_imports = 0
        
        logging.info(f"🔄 {len(qr_results)} adet QR sonucu işlenecek ({invoice_type} tipi)")
        
        for i, result in enumerate(qr_results, 1):
            dosya_adi = result.get('dosya_adi', 'Bilinmeyen')
            if result.get('durum') == 'BAŞARILI':
                # QR verisini fatura alanlarına haritala
                json_data = result.get('json_data', {})
                logging.info(f"\n  📄 [{i}/{len(qr_results)}] {dosya_adi}")
                logging.info(f"  🔑 JSON Anahtarları: {list(json_data.keys())}")
                
                # Önemli alanları logla
                if 'payableAmount' in json_data or 'totalAmount' in json_data:
                    logging.info(f"  💰 Tutar alanları bulundu: {[(k, v) for k, v in json_data.items() if 'amount' in k.lower() or 'tutar' in k.lower() or 'matrah' in k.lower()]}")
                
                parsed_data = self._parse_qr_to_invoice_fields(json_data)
                
                # Parse sonuçlarını detaylı logla
                logging.info(f"  ✏️ Parse Sonucu:")
                logging.info(f"     - Firma: {parsed_data.get('firma', 'YOK')}")
                logging.info(f"     - Malzeme: {parsed_data.get('malzeme', 'YOK')}")
                logging.info(f"     - Toplam Tutar: {parsed_data.get('toplam_tutar', 0)} {parsed_data.get('birim', 'TL')}")
                logging.info(f"     - KDV %: {parsed_data.get('kdv_yuzdesi', 0)}")
                logging.info(f"     - KDV Tutarı: {parsed_data.get('kdv_tutari', 0)} TL")
                logging.info(f"     - KDV Dahil: {parsed_data.get('kdv_dahil', False)}")
                
                # Veritabanına ekle
                if self.handle_invoice_operation('add', invoice_type, data=parsed_data):
                    successful_imports += 1
                    logging.info(f"  ✅ Veritabanına başarıyla eklendi\n")
                else:
                    failed_imports += 1
                    logging.error(f"  ❌ Veritabanına EKLENEMEDİ!\n")
            else:
                failed_imports += 1
                logging.warning(f"  ⚠️ [{i}/{len(qr_results)}] {dosya_adi} - QR Okunamadı: {result.get('durum', 'Bilinmiyor')}\n")
        
        logging.info(f"\n{'='*50}")
        logging.info(f"✅ İşlem Tamamlandı: {successful_imports} başarılı, {failed_imports} başarısız")
        logging.info(f"{'='*50}\n")
        
        self.data_updated.emit() # Toplu ekleme sonrası sinyal gönder
        return successful_imports, failed_imports

    def _parse_qr_to_invoice_fields(self, qr_json):
        """
        Tek bir QR JSON verisini, handle_invoice_operation'ın beklediği
        sözlük formatına dönüştürür.
        """
        if not qr_json: return {}

        # QR JSON içeriğini logla
        logging.info(f"  🔍 QR JSON Anahtarları: {list(qr_json.keys())}")
        
        # Olası anahtar isimlerini ve öncelik sırasını tanımla (BÜYÜK/küçük harf duyarsız)
        key_map = {
            'irsaliye_no': ['invoiceId', 'faturaNo', 'belgeno', 'uuid', 'id', 'no', 'invoiceNumber', 'belgeNo', 'seriNo', 'ettn', 'faturaid'],
            'tarih': ['invoiceDate', 'faturaTarihi', 'tarih', 'date', 'invoicedate', 'faturatarihi'],
            'firma': ['sellerName', 'saticiUnvan', 'firma', 'supplier', 'company', 'companyName', 'firmaUnvan', 'aliciUnvan', 'buyerName', 'saticiadi', 'aliciadi', 'satici', 'sellername', 'buyername'],
            'malzeme': ['tip', 'type', 'itemName', 'description', 'malzeme', 'hizmet', 'urun', 'product', 'service', 'senaryo'],
            'miktar': ['quantity', 'miktar', 'adet', 'amount', 'qty', 'quantityvalue', 'lineitem', 'kalem'],
            'toplam_tutar': ['payableAmount', 'odenecek', 'vergidahil', 'totalAmount', 'toplamTutar', 'total', 'amount', 'tutar', 'geneltoplam', 'vergidahiltoplam', 'payableamount', 'totalamount'],
            'matrah': ['taxableAmount', 'matrah', 'netAmount', 'malhizmettoplam', 'kdvmatrah', 'kdvmatrah(20)', 'kdvmatrah(18)', 'kdvmatrah(10)', 'kdvmatrah(8)', 'kdvmatrah(1)', 'taxableamount', 'netamount'],
            'kdv_tutari': ['taxAmount', 'hesaplanankdv', 'kdv', 'kdvtoplam', 'hesaplanan kdv', 'hesaplanankdv(20)', 'hesaplanankdv(18)', 'taxamount', 'kdvtutari'],
            'kdv_yuzdesi': ['taxRate', 'kdvOrani', 'vatRate', 'kdvorani', 'taxrate', 'vatrate'],
            'birim': ['currency', 'parabirimi', 'currencyCode', 'paraBirimi', 'currencycode']
        }

        parsed = {}

        def get_value(keys):
            """Büyük/küçük harf duyarsız arama yapar"""
            # Önce direkt eşleşme dene
            for key in keys:
                if key in qr_json and qr_json[key]:
                    return qr_json[key]
            
            # Bulamazsa case-insensitive arama yap
            qr_json_lower = {k.lower(): v for k, v in qr_json.items()}
            for key in keys:
                key_lower = key.lower()
                if key_lower in qr_json_lower and qr_json_lower[key_lower]:
                    return qr_json_lower[key_lower]
            
            return None

        # Değerleri haritala
        parsed['irsaliye_no'] = str(get_value(key_map['irsaliye_no']) or f"QR-{int(time.time())}")
        parsed['tarih'] = str(get_value(key_map['tarih']) or datetime.now().strftime("%Y-%m-%d"))
        
        # Firma adını bul - önce standart alanlar, yoksa VKN numarasını kullan
        firma_adi = get_value(key_map['firma'])
        if not firma_adi or (isinstance(firma_adi, str) and firma_adi.isdigit()):
            # Firma adı yok veya sadece numara - VKN'yi firma adı yap
            vkn = get_value(['vkntckn', 'vkn'])
            avkn = get_value(['avkntckn', 'avkn'])
            satici = get_value(['satici', 'saticiadi', 'sellerName'])
            
            if satici and not (isinstance(satici, str) and satici.isdigit()):
                # Satıcı adı var ve numara değil
                firma_adi = satici
            elif vkn:
                firma_adi = f"VKN: {vkn}"
            elif avkn:
                firma_adi = f"Alıcı VKN: {avkn}"
            else:
                firma_adi = 'Bilinmeyen Firma'
        
        parsed['firma'] = str(firma_adi)
        
        # Malzeme/Hizmet bilgisini bul
        malzeme = get_value(key_map['malzeme'])
        if malzeme:
            # Tip/Senaryo bilgisini okunaklı hale getir
            malzeme_str = str(malzeme).upper()
            
            # Fatura türü düzenlemeleri
            if 'EARSIV' in malzeme_str or 'E-ARSIV' in malzeme_str:
                malzeme_str = 'E-Arşiv Fatura'
            elif 'TICARIFATURA' in malzeme_str or 'TICARI' in malzeme_str:
                malzeme_str = 'Ticari Fatura'
            elif 'TEMEL' in malzeme_str:
                malzeme_str = 'Temel Fatura'
            elif 'ISTISNA' in malzeme_str:
                malzeme_str = 'İstisna Faturası'
            elif malzeme_str in ['SATIS', 'SATŞ', 'SALE']:
                malzeme_str = 'Satış Faturası'
            elif malzeme_str in ['ALIS', 'ALIŞ', 'PURCHASE']:
                malzeme_str = 'Alış Faturası'
            elif malzeme_str == 'SARJANLIK':
                malzeme_str = 'Şarj/Anlık Satış'
            # Eğer düzenleme yapılmadıysa olduğu gibi kullan
            
            parsed['malzeme'] = malzeme_str
        else:
            parsed['malzeme'] = 'QR Kodlu E-Fatura'
        
        # Miktar bilgisini al (QR'dan gelmişse kullan, yoksa 1)
        miktar_value = get_value(key_map['miktar'])
        if miktar_value:
            # Miktar string içinde olabilir, temizle
            try:
                miktar_str = str(miktar_value).strip()
                # Sadece sayıyı al (örn: "5 Adet" -> "5")
                miktar_clean = re.sub(r'[^\d.,]', '', miktar_str)
                if miktar_clean:
                    parsed['miktar'] = miktar_clean.replace(',', '.')
                else:
                    parsed['miktar'] = '1'
            except:
                parsed['miktar'] = '1'
        else:
            parsed['miktar'] = '1'
        
        # Para birimi - TRY'yi TL'ye çevir
        birim = str(get_value(key_map['birim']) or 'TRY').upper()
        # TRY, TRL gibi Türk Lirası varyasyonlarını TL'ye çevir
        if birim in ['TRY', 'TRL', 'TÜRK LİRASI', 'TURK LIRASI']:
            birim = 'TL'
        parsed['birim'] = birim
        
        logging.info(f"  📝 Temel Alanlar - Miktar: {parsed['miktar']}, Birim: {parsed['birim']}, Malzeme: {parsed['malzeme'][:30]}")

        # Tutar ve KDV hesaplaması - GELİŞTİRİLMİŞ LOJİK
        toplam_tutar = self._to_float(get_value(key_map['toplam_tutar']))
        matrah = self._to_float(get_value(key_map['matrah']))
        kdv_tutari = self._to_float(get_value(key_map['kdv_tutari']))
        kdv_yuzdesi = self._to_float(get_value(key_map['kdv_yuzdesi']))

        logging.info(f"  💰 QR Tutar Bilgileri - Toplam: {toplam_tutar}, Matrah: {matrah}, KDV Tutarı: {kdv_tutari}, KDV%: {kdv_yuzdesi}")

        # 1. KDV yüzdesini belirle
        if kdv_yuzdesi > 0:
            parsed['kdv_yuzdesi'] = kdv_yuzdesi
        elif matrah > 0 and kdv_tutari > 0:
            # KDV yüzdesi yoksa matrah ve KDV tutarından hesapla
            parsed['kdv_yuzdesi'] = round((kdv_tutari / matrah) * 100, 2)
        else:
            # Hiçbiri yoksa varsayılan
            parsed['kdv_yuzdesi'] = self.settings.get('kdv_yuzdesi', 20.0)

        # 2. Ana tutarı ve KDV dahil durumunu belirle
        if toplam_tutar > 0 and matrah > 0:
            # Her iki tutar da varsa, toplam KDV dahil, matrah KDV hariçtir
            parsed['toplam_tutar'] = matrah  # Sisteme matrahı (KDV hariç) gönder
            parsed['kdv_dahil'] = False
            # KDV tutarını hesapla veya doğrula
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
            
            logging.info(f"  ✅ Matrah ve Toplam var - Matrah kullanılıyor: {matrah} TL, KDV: {parsed['kdv_tutari']} TL")
            
        elif toplam_tutar > 0:
            # Sadece toplam tutar varsa (KDV dahil olabilir)
            parsed['toplam_tutar'] = toplam_tutar
            
            # KDV tutarı verilmişse, bu KDV dahil demektir
            if kdv_tutari > 0:
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = kdv_tutari
                # Matrahı ters hesapla
                matrah_calculated = toplam_tutar - kdv_tutari
                logging.info(f"  ✅ Toplam ve KDV Tutarı var - KDV Dahil: {toplam_tutar} TL, KDV: {kdv_tutari} TL, Hesaplanan Matrah: {matrah_calculated} TL")
            else:
                # KDV tutarı yok, toplam tutarın KDV dahil olup olmadığını anlamak zor
                # Güvenli taraf: KDV dahil kabul et ve matrahı hesapla
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = toplam_tutar * (parsed['kdv_yuzdesi'] / (100 + parsed['kdv_yuzdesi']))
                matrah_calculated = toplam_tutar - parsed['kdv_tutari']
                logging.info(f"  ⚠️ Sadece Toplam var - KDV Dahil varsayıldı: {toplam_tutar} TL, Hesaplanan KDV: {parsed['kdv_tutari']:.2f} TL")
            
        elif matrah > 0:
            # Sadece matrah varsa (KDV hariç)
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
            
            logging.info(f"  ✅ Sadece Matrah var - KDV Hariç: {matrah} TL, Hesaplanan KDV: {parsed['kdv_tutari']:.2f} TL")
            
        else:
            # Hiçbir tutar bilgisi yok
            parsed['toplam_tutar'] = 0
            parsed['kdv_dahil'] = False
            parsed['kdv_tutari'] = 0
            logging.warning(f"  ❌ QR'da hiçbir tutar bilgisi bulunamadı!")

        logging.info(f"  📊 Sonuç - Tutar: {parsed.get('toplam_tutar', 0)} {parsed.get('birim', 'TL')}, KDV%: {parsed.get('kdv_yuzdesi', 0)}, KDV Tutarı: {parsed.get('kdv_tutari', 0)}, KDV Dahil: {parsed.get('kdv_dahil', False)}")
        logging.info(f"  📦 Diğer Alanlar - Miktar: {parsed.get('miktar', 'YOK')}, Birim: {parsed.get('birim', 'YOK')}, Firma: {parsed.get('firma', 'YOK')[:30]}")

        return parsed

    def _to_float(self, value):
        """Bir değeri güvenli bir şekilde float'a çevirir."""
        if value is None or value == '': 
            return 0.0
        
        try:
            # String'e çevir ve temizle
            str_value = str(value).strip()
            
            # Boş string kontrolü
            if not str_value or str_value.lower() in ['none', 'null', 'n/a']:
                return 0.0
            
            # Para birimi sembollerini ve diğer karakterleri temizle
            str_value = re.sub(r'[^\d.,\-+]', '', str_value)
            
            # Binlik ayırıcıları kaldır (1.234,56 veya 1,234.56 formatları)
            if ',' in str_value and '.' in str_value:
                # Her iki ayırıcı da varsa, sonuncusu ondalık ayırıcıdır
                last_comma = str_value.rfind(',')
                last_dot = str_value.rfind('.')
                
                if last_comma > last_dot:
                    # Virgül ondalık ayırıcı (Türk formatı: 1.234,56)
                    str_value = str_value.replace('.', '').replace(',', '.')
                else:
                    # Nokta ondalık ayırıcı (US formatı: 1,234.56)
                    str_value = str_value.replace(',', '')
            elif ',' in str_value:
                # Sadece virgül var - ondalık ayırıcı olabilir
                # Eğer virgülden sonra 2 hane varsa, ondalık ayırıcıdır
                parts = str_value.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    str_value = str_value.replace(',', '.')
                else:
                    # Binlik ayırıcı
                    str_value = str_value.replace(',', '')
            
            return float(str_value)
            
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning(f"  ⚠️ Float dönüşüm hatası: '{value}' -> Hata: {e}")
            return 0.0