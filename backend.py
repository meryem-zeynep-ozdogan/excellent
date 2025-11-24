# backend.py
# -*- coding: utf-8 -*-

import os
import logging
import sqlite3
import time
import json
import re
import warnings

import numpy as np

from datetime import datetime, timedelta
import pandas as pd
import requests
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')





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
        
        # QR Entegrasyon - Lazy loading (gerektiğinde yüklenecek)
        self._qr_integrator = None
        
        # Kurları başlangıçta bir kez çek
        self.update_exchange_rates()

    @property
    def qr_integrator(self):
        """QR entegratörünü lazy loading ile başlatır - OPTİMİZE EDİLMİŞ MODÜL."""
        if self._qr_integrator is None:
            from qr_optimized import QRInvoiceIntegrator
            self._qr_integrator = QRInvoiceIntegrator(self)
            logging.info("✅ QR Entegratörü başlatıldı (optimize edilmiş)")
        return self._qr_integrator
    
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

    def _to_float(self, value):
        """Bir değeri güvenli bir şekilde float'a çevirir."""
        if value is None or value == '': 
            return 0.0
        
        try:
            str_value = str(value).strip()
            
            if not str_value or str_value.lower() in ['none', 'null', 'n/a']:
                return 0.0
            
            # Sadece rakam, nokta, virgül ve işaretleri bırak
            str_value = re.sub(r'[^\d.,\-+]', '', str_value)
            
            # Hem virgül hem nokta varsa format belirle
            if ',' in str_value and '.' in str_value:
                last_comma = str_value.rfind(',')
                last_dot = str_value.rfind('.')
                
                if last_comma > last_dot:
                    # Avrupa formatı: 1.234,56 -> 1234.56
                    str_value = str_value.replace('.', '').replace(',', '.')
                else:
                    # ABD formatı: 1,234.56 -> 1234.56
                    str_value = str_value.replace(',', '')
            elif ',' in str_value:
                # Sadece virgül var
                parts = str_value.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Ondalık ayırıcı: 123,45 -> 123.45
                    str_value = str_value.replace(',', '.')
                else:
                    # Binlik ayırıcı: 1,234 -> 1234
                    str_value = str_value.replace(',', '')
            
            return float(str_value)
            
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning(f"Float dönüşüm hatası: '{value}' -> Hata: {e}")
            return 0.0

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
                logging.error(f"❌ İşlenmiş veri boş! Ham veri: {data}")
                return False
            
            logging.info(f"🔹 Fatura ekleniyor -> Tip: {invoice_type}, Firma: {processed_data.get('firma', 'N/A')[:30]}")
            
            if invoice_type == 'outgoing':
                result = self.db.add_gelir_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gelir', processed_data)
                    logging.info(f"✅ GELİR faturası eklendi (ID: {result})")
                else:
                    logging.error(f"❌ GELİR faturası eklenemedi!")
            elif invoice_type == 'incoming':
                result = self.db.add_gider_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gider', processed_data)
                    logging.info(f"✅ GİDER faturası eklendi (ID: {result})")
                else:
                    logging.error(f"❌ GİDER faturası eklenemedi!")
            else:
                logging.error(f"❌ Geçersiz invoice_type: {invoice_type}")
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
    
    # === QR İŞLEMLERİ - ENTEGRE SİSTEM ===
    
    def process_qr_files_in_folder(self, folder_path, max_workers=8, status_callback=None):
        """
        QR dosyalarını işler - qrayiklanmis.py modülüne yönlendirir.
        
        Args:
            folder_path: İşlenecek dosyaların klasör yolu
            max_workers: Paralel işlem sayısı
            status_callback: İlerleme bildirimi için callback (opsiyonel)
            
        Returns:
            list: QR işleme sonuçları
        """
        # Callback wrapper - hem sinyal hem de frontend callback'i çağır
        def combined_callback(msg, duration):
            # Backend sinyalini yay
            self.status_updated.emit(msg, duration)
            # Frontend callback varsa çağır
            if status_callback:
                return status_callback(msg, duration)
            return True
        
        # QR entegratörüne callback'i geçir
        return self.qr_integrator.process_qr_files_in_folder(
            folder_path, 
            max_workers, 
            status_callback=combined_callback if status_callback else None
        )
    
    def add_invoices_from_qr_data(self, qr_results, invoice_type):
        """
        QR sonuçlarını veritabanına ekler - MANUEL TİP SEÇİMİ
        
        Args:
            qr_results: QR işleme sonuçları
            invoice_type: 'outgoing' (gelir) veya 'incoming' (gider)
            
        Returns:
            dict: {
                'success': bool,
                'added': int,
                'failed': int,
                'total': int,
                'invoice_type': str,
                'processing_details': list
            }
        """
        return self.qr_integrator.add_invoices_from_qr_data(qr_results, invoice_type)