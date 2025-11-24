# backend.py
# -*- coding: utf-8 -*-

import os
import logging
import sqlite3
import time
import json
import re
import warnings
# import fitz  # PyMuPDF  <-- HATA VEREN SATIR BURADAN TAŞINDI
# import cv2             <-- HATA VEREN SATIR BURADAN TAŞINDI
import numpy as np
# from pyzbar import pyzbar <-- HATA VEREN SATIR BURADAN TAŞINDI
from datetime import datetime, timedelta
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# QR işleme için uyarıları kapat
warnings.filterwarnings("ignore")
# cv2.setNumThreads(4) <-- Hata verdiği için bu da kapatıldı
# cv2.setUseOptimized(True) <-- Hata verdiği için bu da kapatıldı


class FastQRProcessor:
    """HIZLI VE MİNİMAL QR İşlemci"""
    
    def __init__(self):
        # self.opencv_detector = cv2.QRCodeDetector() <-- Hata verdiği için bu da taşındı
        pass # Başlangıçta QR ile ilgili hiçbir şey yükleme
    
    def _init_qr_tools(self):
        """QR araçlarını sadece gerektiğinde yükler."""
        global cv2, pyzbar
        import cv2
        from pyzbar import pyzbar
        cv2.setNumThreads(4)
        cv2.setUseOptimized(True)
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
        """
        # Araçları yükle
        if not hasattr(self, 'opencv_detector'):
            self._init_qr_tools()
            
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

        # 4. YENİ ADIM: Adaptif Eşikleme
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

        # 5. YENİ ADIM: Otsu's Eşikleme
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
        import fitz  # PyMuPDF <-- GEREKTİĞİNDE BURADA IMPORT EDİLECEK
        
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            # DPI'yı artırarak daha yüksek çözünürlüklü resim elde et
            zoom = 300 / 72.0  # 300 DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            
            if not 'cv2' in globals(): # cv2 yüklenmemişse yükle
                 self._init_qr_tools()
                 
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
            if not 'cv2' in globals(): # cv2 yüklenmemişse yükle
                 self._init_qr_tools()
                 
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
    """6 Ayrı Veritabanı ile Çalışan Sınıf - Database Dizininde."""
    def __init__(self):
        # Database dizinini oluştur
        self.db_dir = os.path.join(os.getcwd(), 'Database')
        os.makedirs(self.db_dir, exist_ok=True)
        
        # 6 ayrı veritabanı bağlantısı
        self.gelir_conn = sqlite3.connect(os.path.join(self.db_dir, 'gelir.db'), check_same_thread=False)
        self.gider_conn = sqlite3.connect(os.path.join(self.db_dir, 'gider.db'), check_same_thread=False)
        self.genel_gider_conn = sqlite3.connect(os.path.join(self.db_dir, 'genel_gider.db'), check_same_thread=False)
        self.settings_conn = sqlite3.connect(os.path.join(self.db_dir, 'settings.db'), check_same_thread=False)
        self.exchange_rates_conn = sqlite3.connect(os.path.join(self.db_dir, 'exchange_rates.db'), check_same_thread=False)
        self.history_conn = sqlite3.connect(os.path.join(self.db_dir, 'history.db'), check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Her veritabanında gerekli tabloları oluşturur."""
        try:
            # GELİR VERİTABANI
            gelir_cursor = self.gelir_conn.cursor()
            gelir_cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fatura_no TEXT,
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
            
            # Add fatura_no column if it doesn't exist (for existing databases)
            try:
                gelir_cursor.execute("ALTER TABLE invoices ADD COLUMN fatura_no TEXT")
                logging.info("Added fatura_no column to gelir invoices table")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # GİDER VERİTABANI
            gider_cursor = self.gider_conn.cursor()
            gider_cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fatura_no TEXT,
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
            
            # Add fatura_no column if it doesn't exist (for existing databases)
            try:
                gider_cursor.execute("ALTER TABLE invoices ADD COLUMN fatura_no TEXT")
                logging.info("Added fatura_no column to gider invoices table")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # GENEL GİDER VERİTABANI
            genel_gider_cursor = self.genel_gider_conn.cursor()
            genel_gider_cursor.execute("""
                CREATE TABLE IF NOT EXISTS general_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tarih TEXT,
                    tur TEXT,
                    miktar REAL,
                    aciklama TEXT
                )
            """)
            
            # SETTINGS VERİTABANI
            settings_cursor = self.settings_conn.cursor()
            settings_cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # EXCHANGE RATES VERİTABANI
            exchange_rates_cursor = self.exchange_rates_conn.cursor()
            exchange_rates_cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    currency TEXT PRIMARY KEY,
                    rate REAL,
                    updated_at TEXT
                )
            """)
            
            # HISTORY VERİTABANI
            history_cursor = self.history_conn.cursor()
            history_cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoice_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    invoice_type TEXT NOT NULL,
                    invoice_date TEXT,
                    firma TEXT,
                    amount REAL,
                    operation_date TEXT,
                    operation_time TEXT,
                    details TEXT
                )
            """)
            
            # Değişiklikleri kaydet
            self.gelir_conn.commit()
            self.gider_conn.commit()
            self.genel_gider_conn.commit()
            self.settings_conn.commit()
            self.exchange_rates_conn.commit()
            self.history_conn.commit()
            
        except sqlite3.Error as e:
            logging.error(f"Tablo oluşturma hatası: {e}")

    def _get_connection(self, db_type):
        """Veritabanı tipine göre bağlantı döndürür."""
        if db_type == 'gelir':
            return self.gelir_conn
        elif db_type == 'gider':
            return self.gider_conn
        elif db_type == 'genel_gider':
            return self.genel_gider_conn
        elif db_type == 'settings':
            return self.settings_conn
        elif db_type == 'exchange_rates':
            return self.exchange_rates_conn
        elif db_type == 'history':
            return self.history_conn
        else:
            logging.error(f"Geçersiz veritabanı tipi: {db_type}")
            return None

    def _execute_query(self, db_type, query, params=()):
        """Belirtilen veritabanında sorgu çalıştırmak için yardımcı metod."""
        try:
            conn = self._get_connection(db_type)
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            logging.error(f"Sorgu hatası ({db_type}): {e} - Sorgu: {query} - Parametreler: {params}")
            return None

    # GELİR İŞLEMLERİ
    def add_gelir_invoice(self, data):
        """Gelir veritabanına fatura ekler."""
        query = """
            INSERT INTO invoices (fatura_no, irsaliye_no, tarih, firma, malzeme, miktar, toplam_tutar_tl, toplam_tutar_usd, toplam_tutar_eur, birim, kdv_yuzdesi, kdv_tutari, kdv_dahil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get('fatura_no'), data.get('irsaliye_no'), data.get('tarih'), data.get('firma'),
            data.get('malzeme'), data.get('miktar'), data.get('toplam_tutar_tl'),
            data.get('toplam_tutar_usd'), data.get('toplam_tutar_eur'), data.get('birim'),
            data.get('kdv_yuzdesi', 0), data.get('kdv_tutari', 0), data.get('kdv_dahil', 0)
        )
        cursor = self._execute_query('gelir', query, params)
        return cursor.lastrowid if cursor else None

    def update_gelir_invoice(self, invoice_id, data):
        """Gelir veritabanındaki faturayı günceller."""
        query = """
            UPDATE invoices SET
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
        cursor = self._execute_query('gelir', query, params)
        return cursor is not None

    def delete_gelir_invoice(self, invoice_id):
        """Gelir veritabanından fatura siler."""
        query = "DELETE FROM invoices WHERE id = ?"
        cursor = self._execute_query('gelir', query, (invoice_id,))
        return cursor.rowcount if cursor else 0

    def delete_multiple_gelir_invoices(self, invoice_ids):
        """Gelir veritabanından çoklu fatura siler."""
        if not invoice_ids:
            return 0
        
        placeholders = ','.join(['?' for _ in invoice_ids])
        query = f"DELETE FROM invoices WHERE id IN ({placeholders})"
        cursor = self._execute_query('gelir', query, invoice_ids)
        return cursor.rowcount if cursor else 0

    def get_all_gelir_invoices(self, limit=None, offset=0, order_by=None):
        """Gelir veritabanındaki tüm faturaları getirir."""
        if not order_by:
            order_by = "tarih DESC"
        
        # Limit ve offset güvenli değerler kullan
        if limit is not None:
            query = f"SELECT * FROM invoices ORDER BY {order_by} LIMIT {int(limit)} OFFSET {int(offset or 0)}"
        else:
            query = f"SELECT * FROM invoices ORDER BY {order_by}"
        
        cursor = self._execute_query('gelir', query)
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
    
    def get_gelir_invoice_count(self):
        """Gelir tablosundaki toplam fatura sayısını döndürür."""
        query = "SELECT COUNT(*) FROM invoices"
        cursor = self._execute_query('gelir', query)
        if cursor:
            return cursor.fetchone()[0]
        return 0

    def get_gelir_invoice_by_id(self, invoice_id):
        """Gelir veritabanından ID'ye göre tek bir fatura getirir."""
        query = "SELECT * FROM invoices WHERE id = ?"
        cursor = self._execute_query('gelir', query, (invoice_id,))
        if cursor:
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None

    # GİDER İŞLEMLERİ
    def add_gider_invoice(self, data):
        """Gider veritabanına fatura ekler."""
        query = """
            INSERT INTO invoices (fatura_no, irsaliye_no, tarih, firma, malzeme, miktar, toplam_tutar_tl, toplam_tutar_usd, toplam_tutar_eur, birim, kdv_yuzdesi, kdv_tutari, kdv_dahil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get('fatura_no'), data.get('irsaliye_no'), data.get('tarih'), data.get('firma'),
            data.get('malzeme'), data.get('miktar'), data.get('toplam_tutar_tl'),
            data.get('toplam_tutar_usd'), data.get('toplam_tutar_eur'), data.get('birim'),
            data.get('kdv_yuzdesi', 0), data.get('kdv_tutari', 0), data.get('kdv_dahil', 0)
        )
        cursor = self._execute_query('gider', query, params)
        return cursor.lastrowid if cursor else None

    def update_gider_invoice(self, invoice_id, data):
        """Gider veritabanındaki faturayı günceller."""
        query = """
            UPDATE invoices SET
            fatura_no = ?, irsaliye_no = ?, tarih = ?, firma = ?, malzeme = ?, miktar = ?, 
            toplam_tutar_tl = ?, toplam_tutar_usd = ?, toplam_tutar_eur = ?, birim = ?, kdv_yuzdesi = ?, kdv_tutari = ?, kdv_dahil = ?
            WHERE id = ?
        """
        params = (
            data.get('fatura_no'), data.get('irsaliye_no'), data.get('tarih'), data.get('firma'), 
            data.get('malzeme'), data.get('miktar'), data.get('toplam_tutar_tl'),
            data.get('toplam_tutar_usd'), data.get('toplam_tutar_eur'), data.get('birim'),
            data.get('kdv_yuzdesi', 0), data.get('kdv_tutari', 0), data.get('kdv_dahil', 0), invoice_id
        )
        cursor = self._execute_query('gider', query, params)
        return cursor is not None

    def delete_gider_invoice(self, invoice_id):
        """Gider veritabanından fatura siler."""
        query = "DELETE FROM invoices WHERE id = ?"
        cursor = self._execute_query('gider', query, (invoice_id,))
        return cursor.rowcount if cursor else 0

    def delete_multiple_gider_invoices(self, invoice_ids):
        """Gider veritabanından çoklu fatura siler."""
        if not invoice_ids:
            return 0
        
        placeholders = ','.join(['?' for _ in invoice_ids])
        query = f"DELETE FROM invoices WHERE id IN ({placeholders})"
        cursor = self._execute_query('gider', query, invoice_ids)
        return cursor.rowcount if cursor else 0

    def get_all_gider_invoices(self, limit=None, offset=0, order_by=None):
        """Gider veritabanındaki tüm faturaları getirir."""
        if not order_by:
            order_by = "tarih DESC"
        
        # Limit ve offset güvenli değerler kullan
        if limit is not None:
            query = f"SELECT * FROM invoices ORDER BY {order_by} LIMIT {int(limit)} OFFSET {int(offset or 0)}"
        else:
            query = f"SELECT * FROM invoices ORDER BY {order_by}"
        
        cursor = self._execute_query('gider', query)
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
    
    def get_gider_invoice_count(self):
        """Gider tablosundaki toplam fatura sayısını döndürür."""
        query = "SELECT COUNT(*) FROM invoices"
        cursor = self._execute_query('gider', query)
        if cursor:
            return cursor.fetchone()[0]
        return 0

    def get_gider_invoice_by_id(self, invoice_id):
        """Gider veritabanından ID'ye göre tek bir fatura getirir."""
        query = "SELECT * FROM invoices WHERE id = ?"
        cursor = self._execute_query('gider', query, (invoice_id,))
        if cursor:
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None

    # GENEL GİDER İŞLEMLERİ
    def add_genel_gider(self, data):
        """Genel gider veritabanına kayıt ekler."""
        query = """
            INSERT INTO general_expenses (tarih, tur, miktar, aciklama)
            VALUES (?, ?, ?, ?)
        """
        params = (
            data.get('tarih'), data.get('tur'), 
            data.get('miktar'), data.get('aciklama', '')
        )
        cursor = self._execute_query('genel_gider', query, params)
        return cursor.lastrowid if cursor else None

    def update_genel_gider(self, gider_id, data):
        """Genel gider veritabanındaki kaydı günceller."""
        query = """
            UPDATE general_expenses SET
            tarih = ?, tur = ?, miktar = ?, aciklama = ?
            WHERE id = ?
        """
        params = (
            data.get('tarih'), data.get('tur'), 
            data.get('miktar'), data.get('aciklama', ''), gider_id
        )
        cursor = self._execute_query('genel_gider', query, params)
        return cursor is not None

    def delete_genel_gider(self, gider_id):
        """Genel gider veritabanından kayıt siler."""
        query = "DELETE FROM general_expenses WHERE id = ?"
        cursor = self._execute_query('genel_gider', query, (gider_id,))
        return cursor.rowcount if cursor else 0

    def delete_multiple_genel_gider(self, gider_ids):
        """Genel gider veritabanından çoklu kayıt siler."""
        if not gider_ids:
            return 0
        
        placeholders = ','.join(['?' for _ in gider_ids])
        query = f"DELETE FROM general_expenses WHERE id IN ({placeholders})"
        cursor = self._execute_query('genel_gider', query, gider_ids)
        return cursor.rowcount if cursor else 0

    def get_all_genel_gider(self, limit=None, offset=0, order_by=None):
        """Genel gider veritabanındaki tüm kayıtları getirir."""
        if not order_by:
            order_by = "tarih DESC"
        
        # Limit ve offset güvenli değerler kullan
        if limit is not None:
            query = f"SELECT * FROM general_expenses ORDER BY {order_by} LIMIT {int(limit)} OFFSET {int(offset or 0)}"
        else:
            query = f"SELECT * FROM general_expenses ORDER BY {order_by}"
        
        cursor = self._execute_query('genel_gider', query)
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
    
    def get_genel_gider_count(self):
        """Genel gider tablosundaki toplam kayıt sayısını döndürür."""
        query = "SELECT COUNT(*) FROM general_expenses"
        cursor = self._execute_query('genel_gider', query)
        if cursor:
            return cursor.fetchone()[0]
        return 0

    def get_genel_gider_by_id(self, gider_id):
        """Genel gider veritabanından ID'ye göre tek bir kayıt getirir."""
        query = "SELECT * FROM general_expenses WHERE id = ?"
        cursor = self._execute_query('genel_gider', query, (gider_id,))
        if cursor:
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None

    # --- Ayarlar ve Kur Yönetimi (Ayrı veritabanları) ---
    def get_setting(self, key):
        query = "SELECT value FROM settings WHERE key = ?"
        cursor = self._execute_query('settings', query, (key,))
        if cursor:
            result = cursor.fetchone()
            return result[0] if result else None
        return None

    def save_setting(self, key, value):
        query = "REPLACE INTO settings (key, value) VALUES (?, ?)"
        self._execute_query('settings', query, (key, str(value)))
        return True

    def get_all_settings(self):
        query = "SELECT key, value FROM settings"
        cursor = self._execute_query('settings', query)
        return dict(cursor.fetchall()) if cursor else {}

    def save_exchange_rates(self, rates):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for currency, rate in rates.items():
            query = "REPLACE INTO exchange_rates (currency, rate, updated_at) VALUES (?, ?, ?)"
            self._execute_query('exchange_rates', query, (currency, rate, current_time))
        return True

    def load_exchange_rates(self):
        query = "SELECT currency, rate FROM exchange_rates"
        cursor = self._execute_query('exchange_rates', query)
        return dict(cursor.fetchall()) if cursor else {}

    # --- İşlem Geçmişi Yönetimi ---
    def add_history_record(self, operation_type, invoice_type, invoice_date=None, firma=None, amount=None, details=None):
        """İşlem geçmişi kaydı ekler."""
        current_time = datetime.now()
        operation_date = current_time.strftime("%d.%m.%Y")
        operation_time = current_time.strftime("%H:%M:%S")
        
        query = """
            INSERT INTO invoice_history (operation_type, invoice_type, invoice_date, firma, amount, operation_date, operation_time, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (operation_type, invoice_type, invoice_date, firma, amount, operation_date, operation_time, details)
        cursor = self._execute_query('history', query, params)
        return cursor.lastrowid if cursor else None

    def get_recent_history(self, limit=20):
        """Son işlem geçmişini getirir."""
        query = """
            SELECT * FROM invoice_history 
            ORDER BY id DESC 
            LIMIT ?
        """
        cursor = self._execute_query('history', query, (limit,))
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []

    def get_history_by_date_range(self, start_date, end_date, limit=100):
        """Tarih aralığına göre işlem geçmişini getirir."""
        query = """
            SELECT * FROM invoice_history 
            WHERE operation_date BETWEEN ? AND ?
            ORDER BY id DESC 
            LIMIT ?
        """
        cursor = self._execute_query('history', query, (start_date, end_date, limit))
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []

    def clear_old_history(self, days_to_keep=90):
        """Eski geçmiş kayıtlarını temizler (varsayılan 90 gün)."""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%d.%m.%Y")
        query = "DELETE FROM invoice_history WHERE operation_date < ?"
        cursor = self._execute_query('history', query, (cutoff_date,))
        return cursor.rowcount if cursor else 0


class Backend(QObject):
    """Uygulamanın ana iş mantığını yöneten sınıf."""
    data_updated = pyqtSignal()
    status_updated = pyqtSignal(str, int)

    def __init__(self, parent=None):
        """
        Backend başlatıcısı.
        """
        super().__init__(parent)
        self.db = Database()
        self.settings = self.db.get_all_settings()
        # Vergi oranını float'a dönüştür
        if 'kurumlar_vergisi_yuzdesi' in self.settings:
            try:
                self.settings['kurumlar_vergisi_yuzdesi'] = float(self.settings['kurumlar_vergisi_yuzdesi'])
            except (ValueError, TypeError):
                self.settings['kurumlar_vergisi_yuzdesi'] = 22.0
        else:
            self.settings['kurumlar_vergisi_yuzdesi'] = 22.0
        self.exchange_rates = {}
        self.qr_processor = FastQRProcessor() # QR işlemciyi oluştur
        
        # Kurları başlangıçta bir kez çek
        self.update_exchange_rates()

    def start_timers(self):
        """
        Uygulama döngüsü başladıktan sonra çağrılacak zamanlayıcıları başlatır.
        """
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
        self.exchange_rates = {'USD': 0.030, 'EUR': 0.028} 
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
        """ExchangeRate-API'den döviz kurlarını çeker."""
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
        """
        if not amount:
            return 0.0
        
        from_currency = self._normalize_currency(from_currency)
        to_currency = self._normalize_currency(to_currency)
        
        if from_currency == to_currency:
            return amount
        
        if from_currency == 'TRY':
            rate = self.exchange_rates.get(to_currency)
            return amount * rate if rate else 0.0
        
        if to_currency == 'TRY':
            rate = self.exchange_rates.get(from_currency)
            return amount / rate if rate else 0.0
        
        try_amount = self.convert_currency(amount, from_currency, 'TRY')
        return self.convert_currency(try_amount, 'TRY', to_currency)
    
    def _normalize_currency(self, currency):
        """Para birimi kodunu normalize eder (TL -> TRY)."""
        if not currency:
            return 'TRY'
        
        currency = str(currency).upper().strip()
        
        if currency in ['TL', 'TRL', 'TÜRK LİRASI', 'TURK LIRASI', 'TURKISH LIRA']:
            return 'TRY'
        
        return currency

    def format_date(self, date_str):
        """Tarih string'ini 'dd.mm.yyyy' formatına çevirir."""
        # Boş string veya None ise None döndür (bugünün tarihi değil)
        if not date_str or (isinstance(date_str, str) and not date_str.strip()):
            return None
        
        # String değilse string'e çevir
        if not isinstance(date_str, str):
            date_str = str(date_str)
        
        date_str = date_str.strip()
        
        # Yaygın tarih formatlarını dene
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        # Sadece rakamları al
        cleaned_date = re.sub(r'[^0-9]', '', date_str)
        
        if len(cleaned_date) == 8:
            # İlk 4 karakter yıl gibi görünüyorsa (2000-2099 arası)
            if cleaned_date[:4] in [str(y) for y in range(2000, 2100)]:
                # YYYYaag formatı
                yil = cleaned_date[:4]
                ay = cleaned_date[4:6]
                gun = cleaned_date[6:8]
                try:
                    parsed_date = datetime(int(yil), int(ay), int(gun))
                    return parsed_date.strftime("%d.%m.%Y")
                except ValueError:
                    pass
            else:
                # ggaaYYYY formatı (12112025 gibi)
                gun = cleaned_date[:2]
                ay = cleaned_date[2:4]
                yil = cleaned_date[4:8]
                try:
                    parsed_date = datetime(int(yil), int(ay), int(gun))
                    return parsed_date.strftime("%d.%m.%Y")
                except ValueError:
                    pass
        elif len(cleaned_date) == 6:
            # ggaayy formatı (121125 -> 12.11.2025)
            gun = cleaned_date[:2]
            ay = cleaned_date[2:4]
            yil_short = cleaned_date[4:6]
            # 2000'li yıllara çevir
            yil = "20" + yil_short
            try:
                parsed_date = datetime(int(yil), int(ay), int(gun))
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                pass
        
        # Geçersiz tarih ise bugünün tarihini döndür
        return datetime.now().strftime("%d.%m.%Y")

    def _process_invoice_data(self, invoice_data):
        """
        Fatura verilerini işler, doğrular ve KDV/kur hesaplamalarını yapar.
        """
        # Sadece toplam tutar zorunlu olsun, diğer alanlar boş kalabilir
        toplam_tutar = self._to_float(invoice_data.get('toplam_tutar', 0))
        if toplam_tutar <= 0:
            logging.warning(f"Toplam tutar girilmemiş veya geçersiz: {invoice_data}")
            return None
        
        try:            
            processed = invoice_data.copy()
            
            # Boş alanları olduğu gibi bırak
            processed['fatura_no'] = processed.get('fatura_no', '').strip()
            processed['irsaliye_no'] = processed.get('irsaliye_no', '').strip()
            processed['firma'] = processed.get('firma', '').strip()
            processed['malzeme'] = processed.get('malzeme', '').strip()
            
            # Tarih işleme - kullanıcı girişi varsa onu kullan, yoksa bugünün tarihini kullan
            input_date = processed.get('tarih', '')
            if input_date and input_date.strip():
                formatted_date = self.format_date(input_date)
                processed['tarih'] = formatted_date if formatted_date else datetime.now().strftime("%d.%m.%Y")
            else:
                processed['tarih'] = datetime.now().strftime("%d.%m.%Y")
            
            processed['miktar'] = str(processed.get('miktar', '')).strip()
            
            toplam_tutar = self._to_float(processed.get('toplam_tutar', 0))
            kdv_yuzdesi = self._to_float(processed.get('kdv_yuzdesi', 0))
            kdv_tutari_input = self._to_float(processed.get('kdv_tutari', 0)) 
            birim = processed.get('birim', 'TL')
            
            logging.info(f"\n   🧾 FATURA İŞLEME BAŞLADI (KDV DAHİL SİSTEM)")
            logging.info(f"   📋 Giriş Verileri:")
            logging.info(f"     - Toplam Tutar (KDV DAHİL): {toplam_tutar} {birim}")
            logging.info(f"     - KDV Yüzdesi: {kdv_yuzdesi}%")
            
            # KDV yüzdesi kontrolü
            if kdv_yuzdesi <= 0:
                kdv_yuzdesi = self.settings.get('kdv_yuzdesi', 20.0)
                logging.info(f"   ⚙️ KDV yüzdesi girilmedi, varsayılan kullanılıyor: {kdv_yuzdesi}%")
            
            # KDV DAHİL SİSTEM - Tüm girilen tutarlar KDV dahildir
            if toplam_tutar > 0:
                # KDV dahil tutardan matrahı ve KDV tutarını hesapla
                kdv_katsayisi = 1 + (kdv_yuzdesi / 100)
                matrah = toplam_tutar / kdv_katsayisi
                kdv_tutari = toplam_tutar - matrah
                
                logging.info(f"   ✅ KDV DAHİL HESAPLAMA:")
                logging.info(f"     - KDV Dahil Tutar: {toplam_tutar:.2f} {birim}")
                logging.info(f"     - KDV Katsayısı: {kdv_katsayisi:.4f}")
                logging.info(f"     - Matrah (KDV Hariç): {matrah:.2f} {birim}")
                logging.info(f"     - KDV Tutarı: {kdv_tutari:.2f} {birim}")
            else:
                logging.error(f"   ❌ HATA: Toplam tutar girilmemiş!")
                return None
            
            # Para birimi dönüşümü (TL'ye çevir)
            matrah_tl = self.convert_currency(matrah, birim, 'TRY')
            kdv_tutari_tl = self.convert_currency(kdv_tutari, birim, 'TRY')
            toplam_kdv_dahil_tl = matrah_tl + kdv_tutari_tl

            # Sonuç verilerini hazırla
            processed['toplam_tutar_tl'] = matrah_tl  # Ana tutar hala matrah olarak saklanıyor (geriye uyumluluk)
            processed['toplam_tutar_usd'] = self.convert_currency(matrah_tl, 'TRY', 'USD')
            processed['toplam_tutar_eur'] = self.convert_currency(matrah_tl, 'TRY', 'EUR')
            
            processed['birim'] = birim 
            processed['kdv_yuzdesi'] = kdv_yuzdesi
            processed['kdv_dahil'] = 1  # Her zaman KDV dahil
            processed['kdv_tutari'] = kdv_tutari_tl 
            
            logging.info(f"   📊 SONUÇ (TL CİNSİNDEN):")
            logging.info(f"     - Matrah: {matrah_tl:.2f} TL")
            logging.info(f"     - KDV Tutarı: {kdv_tutari_tl:.2f} TL") 
            logging.info(f"     - TOPLAM (KDV DAHİL): {toplam_kdv_dahil_tl:.2f} TL")
            logging.info(f"   ✅ İşlem başarılı!\n")
            
            return processed

        except (ValueError, TypeError) as e:
            logging.error(f"❌ Fatura veri işleme hatası: {e} - Veri: {invoice_data}")
            return None

    def handle_invoice_operation(self, operation, invoice_type, data=None, record_id=None, limit=None, offset=None, order_by=None):
        """Frontend için fatura işlem merkezi - 3 ayrı veritabanı ile."""
        
        if operation == 'add':
            processed_data = self._process_invoice_data(data)
            if not processed_data:
                return False
            
            if invoice_type == 'outgoing':
                result = self.db.add_gelir_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gelir', processed_data)
            elif invoice_type == 'incoming':
                result = self.db.add_gider_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gider', processed_data)
            else:
                return False
                
            if result:
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'update':
            processed_data = self._process_invoice_data(data)
            if not processed_data:
                return False
            
            if invoice_type == 'outgoing':
                result = self.db.update_gelir_invoice(record_id, processed_data)
                if result:
                    self._add_history_record('GÜNCELLEME', 'gelir', processed_data)
            elif invoice_type == 'incoming':
                result = self.db.update_gider_invoice(record_id, processed_data)
                if result:
                    self._add_history_record('GÜNCELLEME', 'gider', processed_data)
            else:
                return False
                
            if result:
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'delete':
            # Silmeden önce fatura bilgilerini al
            if invoice_type == 'outgoing':
                invoice_data = self.db.get_gelir_invoice_by_id(record_id)
                result = self.db.delete_gelir_invoice(record_id)
                if result and invoice_data:
                    self._add_history_record('SİLME', 'gelir', invoice_data)
            elif invoice_type == 'incoming':
                invoice_data = self.db.get_gider_invoice_by_id(record_id)
                result = self.db.delete_gider_invoice(record_id)
                if result and invoice_data:
                    self._add_history_record('SİLME', 'gider', invoice_data)
            else:
                return False
                
            if result:
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'get':
            if invoice_type == 'outgoing':
                return self.db.get_all_gelir_invoices(limit=limit, offset=offset, order_by=order_by)
            elif invoice_type == 'incoming':
                return self.db.get_all_gider_invoices(limit=limit, offset=offset, order_by=order_by)
            else:
                return []
        
        elif operation == 'count':
            if invoice_type == 'outgoing':
                return self.db.get_gelir_invoice_count()
            elif invoice_type == 'incoming':
                return self.db.get_gider_invoice_count()
            else:
                return 0
        
        elif operation == 'get_by_id':
            if invoice_type == 'outgoing':
                return self.db.get_gelir_invoice_by_id(record_id)
            elif invoice_type == 'incoming':
                return self.db.get_gider_invoice_by_id(record_id)
            else:
                return None
        
        logging.warning(f"Geçersiz fatura operasyonu: {operation}")
        return False

    def handle_genel_gider_operation(self, operation, data=None, record_id=None, limit=None, offset=None):
        """Genel gider işlemleri için özel metod - ayrı veritabanı ile."""
        
        if operation == 'add':
            processed_data = self._process_genel_gider_data(data)
            if processed_data and self.db.add_genel_gider(processed_data):
                self._add_history_record('EKLEME', 'genel_gider', processed_data)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'update':
            processed_data = self._process_genel_gider_data(data)
            if processed_data and self.db.update_genel_gider(record_id, processed_data):
                self._add_history_record('GÜNCELLEME', 'genel_gider', processed_data)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'delete':
            # Silmeden önce genel gider bilgilerini al
            gider_data = self.db.get_genel_gider_by_id(record_id)
            if self.db.delete_genel_gider(record_id):
                if gider_data:
                    self._add_history_record('SİLME', 'genel_gider', gider_data)
                self.data_updated.emit()
                return True
            return False
        
        elif operation == 'get':
            return self.db.get_all_genel_gider(limit=limit, offset=offset)
        
        elif operation == 'count':
            return self.db.get_genel_gider_count()
        
        elif operation == 'get_by_id':
            return self.db.get_genel_gider_by_id(record_id)
        
        return None

    def _process_genel_gider_data(self, gider_data):
        """Genel gider verilerini genel_gider.db formatına çevirir."""
        if not gider_data:
            return None
        
        # Miktar alanını hem sayı hem metin olarak kabul et
        miktar_input = gider_data.get('miktar', '')
        if not miktar_input or str(miktar_input).strip() == '':
            logging.warning(f"Genel gider miktarı girilmemiş: {gider_data}")
            return None
        
        # Eğer sayısal bir değer ise float'a çevir, değilse string olarak bırak
        try:
            miktar = self._to_float(miktar_input)
        except:
            # Sayısal olmayan miktar değerlerini string olarak sakla
            miktar = str(miktar_input).strip()
        
        # Genel gider verilerini direkt format
        input_date = gider_data.get('tarih', '')
        if input_date and input_date.strip():
            formatted_date = self.format_date(input_date)
            tarih = formatted_date if formatted_date else datetime.now().strftime("%d.%m.%Y")
        else:
            tarih = datetime.now().strftime("%d.%m.%Y")
            
        processed = {
            'tarih': tarih,
            'tur': gider_data.get('tur', 'Genel Gider'),
            'miktar': miktar,
            'aciklama': gider_data.get('aciklama', '')
        }
        
        return processed

    # --- İşlem Geçmişi Yönetimi ---
    def get_recent_history(self, limit=20):
        """Son işlem geçmişini getirir."""
        return self.db.get_recent_history(limit)

    def get_history_by_date_range(self, start_date, end_date, limit=100):
        """Tarih aralığına göre işlem geçmişini getirir."""
        return self.db.get_history_by_date_range(start_date, end_date, limit)

    def clear_old_history(self, days_to_keep=90):
        """Eski geçmiş kayıtlarını temizler."""
        deleted_count = self.db.clear_old_history(days_to_keep)
        return deleted_count

    def _add_history_record(self, operation_type, invoice_type, invoice_data=None, details=None):
        """Fatura işlemlerinde geçmiş kaydı ekler."""
        try:
            invoice_date = None
            firma = None
            amount = None
            
            if invoice_data:
                invoice_date = invoice_data.get('tarih')
                firma = invoice_data.get('firma') or invoice_data.get('tur')
                amount = invoice_data.get('toplam_tutar_tl') or invoice_data.get('miktar')
            
            # İşlem tipine göre detay mesajı oluştur
            if not details:
                if operation_type == 'EKLEME':
                    details = f"{invoice_type.title()} fatura eklendi"
                elif operation_type == 'GÜNCELLEME':
                    details = f"{invoice_type.title()} fatura güncellendi"
                elif operation_type == 'SİLME':
                    details = f"{invoice_type.title()} fatura silindi"
                else:
                    details = f"{operation_type} işlemi"
            
            self.db.add_history_record(operation_type, invoice_type, invoice_date, firma, amount, details)
            
        except Exception as e:
            logging.error(f"Geçmiş kaydı ekleme hatası: {e}")

    def delete_multiple_invoices(self, invoice_type, invoice_ids):
        """Çoklu fatura silme işlemi - 3 ayrı veritabanı ile."""
        try:
            if invoice_type == 'outgoing':
                deleted_count = self.db.delete_multiple_gelir_invoices(invoice_ids)
            elif invoice_type == 'incoming':
                deleted_count = self.db.delete_multiple_gider_invoices(invoice_ids)
            else:
                return 0
                
            if deleted_count > 0:
                self.data_updated.emit()
            return deleted_count
        except Exception as e:
            logging.error(f"Çoklu {invoice_type} faturası silme hatası: {e}")
            return 0

    def delete_multiple_genel_gider(self, gider_ids):
        """Çoklu genel gider silme işlemi."""
        try:
            deleted_count = self.db.delete_multiple_genel_gider(gider_ids)
            if deleted_count > 0:
                self.data_updated.emit()
            return deleted_count
        except Exception as e:
            logging.error(f"Çoklu genel gider silme hatası: {e}")
            return 0

    def get_summary_data(self):
        """Gelir, gider ve kar/zarar özetini hesaplar - 3 ayrı veritabanı ile."""
        # Gelir toplamı
        gelir_cursor = self.db.gelir_conn.cursor()
        gelir_cursor.execute("SELECT SUM(toplam_tutar_tl) FROM invoices")
        total_revenue = gelir_cursor.fetchone()[0] or 0
        
        # Fatura giderleri toplamı
        gider_cursor = self.db.gider_conn.cursor()
        gider_cursor.execute("SELECT SUM(toplam_tutar_tl) FROM invoices")
        invoice_expenses = gider_cursor.fetchone()[0] or 0
        
        # Genel giderler toplamı
        genel_gider_cursor = self.db.genel_gider_conn.cursor()
        genel_gider_cursor.execute("SELECT SUM(miktar) FROM general_expenses")
        general_expenses = genel_gider_cursor.fetchone()[0] or 0
        
        # Toplam gider
        total_expense = invoice_expenses + general_expenses
        
        # Aylık veriler
        monthly_income = [0] * 12
        monthly_expenses = [0] * 12
        current_year = datetime.now().year
        
        # Gelir aylık dağılım
        gelir_cursor.execute("""
            SELECT tarih, toplam_tutar_tl FROM invoices 
            WHERE tarih LIKE ?
        """, (f"%.{current_year}",))
        
        for row in gelir_cursor.fetchall():
            try:
                parts = row[0].split('.')
                if len(parts) == 3:
                    month = int(parts[1]) - 1
                    monthly_income[month] += row[1]
            except:
                continue
        
        # Fatura giderleri aylık dağılım
        gider_cursor.execute("""
            SELECT tarih, toplam_tutar_tl FROM invoices 
            WHERE tarih LIKE ?
        """, (f"%.{current_year}",))
        
        for row in gider_cursor.fetchall():
            try:
                parts = row[0].split('.')
                if len(parts) == 3:
                    month = int(parts[1]) - 1
                    monthly_expenses[month] += row[1]
            except:
                continue
                
        # Genel giderler aylık dağılım
        genel_gider_cursor.execute("""
            SELECT tarih, miktar FROM general_expenses 
            WHERE tarih LIKE ?
        """, (f"%.{current_year}",))
        
        for row in genel_gider_cursor.fetchall():
            try:
                parts = row[0].split('.')
                if len(parts) == 3:
                    month = int(parts[1]) - 1
                    monthly_expenses[month] += row[1]
            except:
                continue
        
        active_income_months = sum(1 for income in monthly_income if income > 0)
        total_income_this_year = sum(monthly_income)
        monthly_average = total_income_this_year / active_income_months if active_income_months > 0 else 0
        
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
        """Fatura verilerinde bulunan tüm yılların listesini döndürür - 3 ayrı veritabanı ile."""
        years_set = set()
        current_year = datetime.now().year
        
        years_set.add(str(current_year))
        
        # Gelir veritabanından yılları al
        gelir_invoices = self.db.get_all_gelir_invoices()
        for inv in gelir_invoices:
            try:
                if 'tarih' in inv and inv['tarih']:
                    date_obj = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                    years_set.add(str(date_obj.year))
            except (ValueError, KeyError):
                continue
        
        # Gider veritabanından yılları al
        gider_invoices = self.db.get_all_gider_invoices()
        for inv in gider_invoices:
            try:
                if 'tarih' in inv and inv['tarih']:
                    date_obj = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                    years_set.add(str(date_obj.year))
            except (ValueError, KeyError):
                continue
        
        # Genel gider veritabanından yılları al
        genel_gider_list = self.db.get_all_genel_gider()
        for gider in genel_gider_list:
            try:
                if 'tarih' in gider and gider['tarih']:
                    date_obj = datetime.strptime(gider['tarih'], "%d.%m.%Y")
                    years_set.add(str(date_obj.year))
            except (ValueError, KeyError):
                continue
        
        return sorted(list(years_set), reverse=True)

    def get_calculations_for_year(self, year):
        """Belirli bir yıl için aylık ve çeyrek dönem hesaplamaları - 3 ayrı veritabanı ile."""
        # Vergi oranını güvenli şekilde float'a dönüştür
        tax_rate_raw = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0)
        tax_rate = float(tax_rate_raw) / 100.0
        
        monthly_results = []
        
        for month in range(1, 13):
            # Gelir hesapla
            gelir_cursor = self.db.gelir_conn.cursor()
            gelir_cursor.execute("""
                SELECT SUM(toplam_tutar_tl), SUM(kdv_tutari) 
                FROM invoices 
                WHERE tarih LIKE ?
            """, (f"%.{month:02d}.{year}",))
            gelir_row = gelir_cursor.fetchone()
            kesilen = gelir_row[0] or 0
            kesilen_kdv = gelir_row[1] or 0
            
            # Fatura giderleri hesapla
            gider_cursor = self.db.gider_conn.cursor()
            gider_cursor.execute("""
                SELECT SUM(toplam_tutar_tl), SUM(kdv_tutari) 
                FROM invoices 
                WHERE tarih LIKE ?
            """, (f"%.{month:02d}.{year}",))
            gider_row = gider_cursor.fetchone()
            fatura_giderleri = gider_row[0] or 0
            fatura_gider_kdv = gider_row[1] or 0
            
            # Genel giderleri hesapla
            genel_gider_cursor = self.db.genel_gider_conn.cursor()
            genel_gider_cursor.execute("""
                SELECT SUM(miktar) 
                FROM general_expenses 
                WHERE tarih LIKE ?
            """, (f"%.{month:02d}.{year}",))
            genel_gider_row = genel_gider_cursor.fetchone()
            genel_giderler = genel_gider_row[0] or 0
            
            # Toplam gider
            toplam_gider = fatura_giderleri + genel_giderler
            
            monthly_results.append({
                'kesilen': kesilen,
                'gelen': toplam_gider,
                'kdv': kesilen_kdv - fatura_gider_kdv  # Genel giderlerde KDV yok
            })
        
        quarterly_results = []
        cumulative_profit = 0
        for quarter in range(4):
            start_month_idx = quarter * 3
            end_month_idx = start_month_idx + 3
            
            period_income = sum(m['kesilen'] for m in monthly_results[start_month_idx:end_month_idx])
            period_expense = sum(m['gelen'] for m in monthly_results[start_month_idx:end_month_idx])
            
            cumulative_profit += (period_income - period_expense)
            
            tax_for_period = cumulative_profit * tax_rate if cumulative_profit > 0 else 0
            
            paid_tax_in_previous_quarters = sum(q.get('vergi', 0) for q in quarterly_results)
            payable_tax = tax_for_period - paid_tax_in_previous_quarters
            
            quarterly_results.append({
                'kar': cumulative_profit, 
                'vergi': tax_for_period,
                'odenecek_kv': payable_tax if payable_tax > 0 else 0
            })
        
        return monthly_results, quarterly_results
    
    def get_yearly_summary(self, year):
        """Belirli bir yıl için yıllık özet - 3 ayrı veritabanı ile."""
        
        # Gelir hesapla
        gelir_cursor = self.db.gelir_conn.cursor()
        gelir_cursor.execute("""
            SELECT SUM(toplam_tutar_tl) FROM invoices 
            WHERE tarih LIKE ?
        """, (f"%.{year}",))
        gelir = gelir_cursor.fetchone()[0] or 0
        
        # Fatura giderleri hesapla
        gider_cursor = self.db.gider_conn.cursor()
        gider_cursor.execute("""
            SELECT SUM(toplam_tutar_tl) FROM invoices 
            WHERE tarih LIKE ?
        """, (f"%.{year}",))
        fatura_giderleri = gider_cursor.fetchone()[0] or 0
        
        # Genel giderleri hesapla
        genel_gider_cursor = self.db.genel_gider_conn.cursor()
        genel_gider_cursor.execute("""
            SELECT SUM(miktar) FROM general_expenses 
            WHERE tarih LIKE ?
        """, (f"%.{year}",))
        genel_giderler = genel_gider_cursor.fetchone()[0] or 0
        
        # Toplam gider
        toplam_gider = fatura_giderleri + genel_giderler
        
        brut_kar = gelir - toplam_gider
        
        # Vergi oranını güvenli şekilde float'a dönüştür
        tax_rate_raw = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0)
        tax_rate = float(tax_rate_raw) / 100
        vergi = brut_kar * tax_rate if brut_kar > 0 else 0
        
        return {
            'toplam_gelir': gelir,
            'toplam_gider': toplam_gider,
            'yillik_kar': brut_kar - vergi, # Net kar
            'vergi_tutari': vergi,
            'vergi_yuzdesi': tax_rate * 100
        }
    
    def _is_in_month_year(self, date_str, month, year):
        """Tarihin belirtilen ay ve yılda olup olmadığını kontrol eder."""
        try:
            if not date_str: return False
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
            parts = date_str.split('.')
            if len(parts) == 3:
                return int(parts[2]) == year
            return False
        except (ValueError, IndexError):
            return False
    
    def save_setting(self, key, value):
        """Ayarları kaydeder ve cache'i günceller."""
        # Database'e kaydet
        self.db.save_setting(key, value)
        # Cache'i güncelle ve türüne göre dönüştür
        if key == 'kurumlar_vergisi_yuzdesi':
            self.settings[key] = float(value)
        else:
            self.settings[key] = value
        # Veri güncellendiği sinyalini yay
        self.data_updated.emit()
        return True

    # --- QR KOD İŞLEME VE ENTEGRASYON ---
    def process_qr_files_in_folder(self, folder_path, max_workers=6):
        """
        Bir klasördeki dosyaları paralel olarak işler ve QR kod verilerini döndürür.
        """
        # HATA VEREN IMPORTLAR SADECE BU FONKSİYON ÇAĞRILINCA YÜKLENECEK
        global fitz, cv2, pyzbar
        try:
            import fitz  # PyMuPDF
            import cv2
            from pyzbar import pyzbar
            logging.info("QR kütüphaneleri başarıyla yüklendi.")
        except ImportError as e:
            logging.error(f"❌ KRİTİK HATA: QR kütüphaneleri yüklenemedi: {e}")
            logging.error("Lütfen 'PyMuPDF', 'opencv-python-headless' ve 'pyzbar' kütüphanelerinin kurulu olduğundan emin olun.")
            logging.error("Eksik .dll hatası alıyorsanız (örn: libiconv.dll), manuel .dll yüklemesi gerekebilir.")
            self.status_updated.emit("QR Kütüphaneleri Eksik!", 10000)
            return None # Fonksiyonu durdur

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
        
        # QR işlemciyi ilk kullanımda başlat
        if not hasattr(self.qr_processor, 'opencv_detector'):
            self.qr_processor._init_qr_tools()
            
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
        İşlenmiş QR sonuç listesini alır ve fatura olarak veritabanına ekler - 3 ayrı veritabanı ile.
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
                logging.info(f"\n   📄 [{i}/{len(qr_results)}] {dosya_adi}")
                logging.info(f"   🔑 JSON Anahtarları: {list(json_data.keys())}")
                
                # Önemli alanları logla
                if 'payableAmount' in json_data or 'totalAmount' in json_data:
                    logging.info(f"   💰 Tutar alanları bulundu: {[(k, v) for k, v in json_data.items() if 'amount' in k.lower() or 'tutar' in k.lower() or 'matrah' in k.lower()]}")
                
                parsed_data = self._parse_qr_to_invoice_fields(json_data)
                
                # Parse sonuçlarını detaylı logla
                logging.info(f"   ✏️ Parse Sonucu:")
                logging.info(f"     - Firma: {parsed_data.get('firma', 'YOK')}")
                logging.info(f"     - Malzeme: {parsed_data.get('malzeme', 'YOK')}")
                logging.info(f"     - Toplam Tutar: {parsed_data.get('toplam_tutar', 0)} {parsed_data.get('birim', 'TL')}")
                logging.info(f"     - KDV %: {parsed_data.get('kdv_yuzdesi', 0)}")
                logging.info(f"     - KDV Tutarı: {parsed_data.get('kdv_tutari', 0)} TL")
                logging.info(f"     - KDV Dahil: {parsed_data.get('kdv_dahil', False)}")
                
                # Veritabanına ekle
                if self.handle_invoice_operation('add', invoice_type, data=parsed_data):
                    successful_imports += 1
                    logging.info(f"   ✅ Veritabanına başarıyla eklendi\n")
                else:
                    failed_imports += 1
                    logging.error(f"   ❌ Veritabanına EKLENEMEDİ!\n")
            else:
                failed_imports += 1
                logging.warning(f"   ⚠️ [{i}/{len(qr_results)}] {dosya_adi} - QR Okunamadı: {result.get('durum', 'Bilinmiyor')}\n")
        
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

        logging.info(f"   🔍 QR JSON Anahtarları: {list(qr_json.keys())}")
        
        key_map = {
            'fatura_no': ['faturaNo', 'invoiceNumber', 'faturanumarasi', 'belgeNo', 'documentNo', 'seriNo', 'faturaid', 'documentnumber'],
            'irsaliye_no': ['invoiceId', 'irsaliyeNo', 'belgeno', 'uuid', 'id', 'no', 'belgeNo', 'seriNo', 'ettn', 'irsaliyenumarasi'],
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
            for key in keys:
                if key in qr_json and qr_json[key]:
                    return qr_json[key]
            
            qr_json_lower = {k.lower(): v for k, v in qr_json.items()}
            for key in keys:
                key_lower = key.lower()
                if key_lower in qr_json_lower and qr_json_lower[key_lower]:
                    return qr_json_lower[key_lower]
            
            return None

        parsed = {}
        parsed['fatura_no'] = str(get_value(key_map['fatura_no']) or '')
        parsed['irsaliye_no'] = str(get_value(key_map['irsaliye_no']) or f"QR-{int(time.time())}")
        # Tarih işleme - QR'dan gelen tarihi doğru formatlayalım
        qr_tarih = get_value(key_map['tarih'])
        if qr_tarih:
            # QR'dan gelen tarihi format_date fonksiyonuyla düzeltelim
            parsed['tarih'] = self.format_date(str(qr_tarih))
        else:
            parsed['tarih'] = datetime.now().strftime("%d.%m.%Y")
        
        firma_adi = get_value(key_map['firma'])
        if not firma_adi or (isinstance(firma_adi, str) and firma_adi.isdigit()):
            vkn = get_value(['vkntckn', 'vkn'])
            avkn = get_value(['avkntckn', 'avkn'])
            satici = get_value(['satici', 'saticiadi', 'sellerName'])
            
            if satici and not (isinstance(satici, str) and satici.isdigit()):
                firma_adi = satici
            elif vkn:
                firma_adi = f"VKN: {vkn}"
            elif avkn:
                firma_adi = f"Alıcı VKN: {avkn}"
            else:
                firma_adi = 'Bilinmeyen Firma'
        
        parsed['firma'] = str(firma_adi)
        
        malzeme = get_value(key_map['malzeme'])
        if malzeme:
            malzeme_str = str(malzeme).upper()
            
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
            
            parsed['malzeme'] = malzeme_str
        else:
            parsed['malzeme'] = 'QR Kodlu E-Fatura'
        
        miktar_value = get_value(key_map['miktar'])
        if miktar_value:
            try:
                miktar_str = str(miktar_value).strip()
                miktar_clean = re.sub(r'[^\d.,]', '', miktar_str)
                if miktar_clean:
                    parsed['miktar'] = miktar_clean.replace(',', '.')
                else:
                    parsed['miktar'] = '1'
            except:
                parsed['miktar'] = '1'
        else:
            parsed['miktar'] = '1'
        
        birim = str(get_value(key_map['birim']) or 'TRY').upper()
        if birim in ['TRY', 'TRL', 'TÜRK LİRASI', 'TURK LIRASI']:
            birim = 'TL'
        parsed['birim'] = birim
        
        logging.info(f"   📝 Temel Alanlar - Miktar: {parsed['miktar']}, Birim: {parsed['birim']}, Malzeme: {parsed['malzeme'][:30]}")

        toplam_tutar = self._to_float(get_value(key_map['toplam_tutar']))
        matrah = self._to_float(get_value(key_map['matrah']))
        kdv_tutari = self._to_float(get_value(key_map['kdv_tutari']))
        kdv_yuzdesi = self._to_float(get_value(key_map['kdv_yuzdesi']))

        logging.info(f"   💰 QR Tutar Bilgileri - Toplam: {toplam_tutar}, Matrah: {matrah}, KDV Tutarı: {kdv_tutari}, KDV%: {kdv_yuzdesi}")

        if kdv_yuzdesi > 0:
            parsed['kdv_yuzdesi'] = kdv_yuzdesi
        elif matrah > 0 and kdv_tutari > 0:
            parsed['kdv_yuzdesi'] = round((kdv_tutari / matrah) * 100, 2)
        else:
            parsed['kdv_yuzdesi'] = self.settings.get('kdv_yuzdesi', 20.0)

        if toplam_tutar > 0 and matrah > 0:
            parsed['toplam_tutar'] = matrah 
            parsed['kdv_dahil'] = False
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
            
            logging.info(f"   ✅ Matrah ve Toplam var - Matrah kullanılıyor: {matrah} TL, KDV: {parsed['kdv_tutari']} TL")
            
        elif toplam_tutar > 0:
            parsed['toplam_tutar'] = toplam_tutar
            
            if kdv_tutari > 0:
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = kdv_tutari
                matrah_calculated = toplam_tutar - kdv_tutari
                logging.info(f"   ✅ Toplam ve KDV Tutarı var - KDV Dahil: {toplam_tutar} TL, KDV: {kdv_tutari} TL, Hesaplanan Matrah: {matrah_calculated} TL")
            else:
                parsed['kdv_dahil'] = True
                parsed['kdv_tutari'] = toplam_tutar * (parsed['kdv_yuzdesi'] / (100 + parsed['kdv_yuzdesi']))
                matrah_calculated = toplam_tutar - parsed['kdv_tutari']
                logging.info(f"   ⚠️ Sadece Toplam var - KDV Dahil varsayıldı: {toplam_tutar} TL, Hesaplanan KDV: {parsed['kdv_tutari']:.2f} TL")
            
        elif matrah > 0:
            parsed['toplam_tutar'] = matrah
            parsed['kdv_dahil'] = False
            
            if kdv_tutari > 0:
                parsed['kdv_tutari'] = kdv_tutari
            else:
                parsed['kdv_tutari'] = matrah * (parsed['kdv_yuzdesi'] / 100)
            
            logging.info(f"   ✅ Sadece Matrah var - KDV Hariç: {matrah} TL, Hesaplanan KDV: {parsed['kdv_tutari']:.2f} TL")
            
        else:
            parsed['toplam_tutar'] = 0
            parsed['kdv_dahil'] = False
            parsed['kdv_tutari'] = 0
            logging.warning(f"   ❌ QR'da hiçbir tutar bilgisi bulunamadı!")

        logging.info(f"   📊 Sonuç - Tutar: {parsed.get('toplam_tutar', 0)} {parsed.get('birim', 'TL')}, KDV%: {parsed.get('kdv_yuzdesi', 0)}, KDV Tutarı: {parsed.get('kdv_tutari', 0)}, KDV Dahil: {parsed.get('kdv_dahil', False)}")
        logging.info(f"   📦 Diğer Alanlar - Miktar: {parsed.get('miktar', 'YOK')}, Birim: {parsed.get('birim', 'YOK')}, Firma: {parsed.get('firma', 'YOK')[:30]}")

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
        

