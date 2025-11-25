# db.py
# -*- coding: utf-8 -*-
"""
Veritabanı Yönetim Modülü
6 Ayrı Veritabanı Yapısı - Database Dizininde
"""

from imports import *


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
