# backend.py

import os
import logging
import sqlite3
import time
from datetime import datetime
import pandas as pd
import requests
from PyQt6.QtCore import QObject, pyqtSignal

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Tablo oluşturma hatası: {e}")
            logging.error(f"Tablo oluşturma hatası: {e}")

    def _execute_query(self, query, params=()):
        """Veritabanı sorgularını çalıştırmak için yardımcı metod."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except sqlite3.Error as e:
            print(f"Sorgu hatası: {e} - Sorgu: {query}")
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

    def delete_invoice(self, table_name, invoice_id):
        """Belirtilen tablodan fatura siler."""
        query = f"DELETE FROM {table_name} WHERE id = ?"
        self._execute_query(query, (invoice_id,))

    def get_all_invoices(self, table_name):
        """Belirtilen tablodaki tüm faturaları getirir."""
        query = f"SELECT * FROM {table_name} ORDER BY tarih DESC"
        cursor = self._execute_query(query)
        if cursor:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []

class Backend(QObject):
    data_updated = pyqtSignal()
    status_updated = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.exchange_rates = {}
        
        # Uygulama ayarlarını başlat
        self.settings = {
            'kurumlar_vergisi_yuzdesi': 22.0,  # Varsayılan kurumlar vergisi yüzdesi
            'kdv_yuzdesi': 20.0,  # Varsayılan KDV yüzdesi
        }
        
        # Ayarları veritabanından yükle
        self.load_settings()
        
        # Döviz kurlarını güncelle
        self.fetch_exchange_rates()
        
    def load_settings(self):
        """Uygulama ayarlarını veritabanından yükler."""
        try:
            conn = sqlite3.connect('excellent_mvp.db')
            cursor = conn.cursor()
            
            # Ayarlar tablosunu oluştur (yoksa)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Tüm ayarları yükle
            cursor.execute("SELECT key, value FROM settings")
            for key, value in cursor.fetchall():
                try:
                    # String değeri uygun tipe dönüştür
                    if value.replace('.', '', 1).isdigit():
                        self.settings[key] = float(value)
                    else:
                        self.settings[key] = value
                except (ValueError, AttributeError):
                    self.settings[key] = value
                    
            conn.close()
        except sqlite3.Error as e:
            print(f"Ayarları yükleme hatası: {e}")
            logging.error(f"Ayarları yükleme hatası: {e}")
    
    def save_setting(self, key, value):
        """Bir ayarı kaydeder ve sinyal gönderir."""
        try:
            conn = sqlite3.connect('excellent_mvp.db')
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)",
                           (key, str(value)))
            conn.commit()
            conn.close()
            
            # Ayarı güncelle ve sinyal gönder
            self.settings[key] = value
            self.status_updated.emit(f"{key.replace('_', ' ').capitalize()} ayarı güncellendi.", 3000)
            self.data_updated.emit()
            return True
        except sqlite3.Error as e:
            print(f"Ayar kaydetme hatası: {e}")
            logging.error(f"Ayar kaydetme hatası: {e}")
            return False

    def fetch_exchange_rates(self):
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
        print("Tüm döviz kuru kaynakları başarısız. Varsayılan kurlar kullanılıyor.")
        logging.warning("Tüm döviz kuru kaynakları başarısız. Varsayılan kurlar kullanılıyor.")
        self.exchange_rates = {'USD': 0.029, 'EUR': 0.027}  # Yaklaşık güncel kurlar
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
                print(f"TCMB kurları: 1 USD = {usd_sell:.4f} TL, 1 EUR = {eur_sell:.4f} TL")
                logging.info(f"TCMB kurları: 1 USD = {usd_sell:.4f} TL, 1 EUR = {eur_sell:.4f} TL")
                return True
        except Exception as e:
            print(f"TCMB'den kur alınamadı: {e}")
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
                    print(f"ExchangeRate-API kurları: 1 TRY = {usd_rate:.6f} USD, 1 TRY = {eur_rate:.6f} EUR")
                    logging.info(f"ExchangeRate-API kurları: 1 TRY = {usd_rate:.6f} USD, 1 TRY = {eur_rate:.6f} EUR")
                    return True
        except Exception as e:
            print(f"ExchangeRate-API'den kur alınamadı: {e}")
            logging.error(f"ExchangeRate-API'den kur alınamadı: {e}")
        return False
    
    def _save_rates_to_db(self):
        """Güncel döviz kurlarını veritabanına kaydeder."""
        try:
            conn = sqlite3.connect('excellent_mvp.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    currency TEXT PRIMARY KEY,
                    rate REAL,
                    updated_at TEXT
                )
            """)
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for currency, rate in self.exchange_rates.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO exchange_rates (currency, rate, updated_at)
                    VALUES (?, ?, ?)
                """, (currency, rate, current_time))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Kurları veritabanına kaydetme hatası: {e}")
            logging.error(f"Kurları veritabanına kaydetme hatası: {e}")
    
    def _load_rates_from_db(self):
        """Veritabanından son kaydedilen kurları yükler."""
        try:
            conn = sqlite3.connect('excellent_mvp.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT currency, rate FROM exchange_rates")
            rates = cursor.fetchall()
            
            if rates:
                self.exchange_rates = {currency: rate for currency, rate in rates}
                conn.close()
                print(f"Veritabanından yüklenen kurlar: {self.exchange_rates}")
                logging.info(f"Veritabanından yüklenen kurlar: {self.exchange_rates}")
                return True
            
            conn.close()
        except Exception as e:
            print(f"Veritabanından kur yükleme hatası: {e}")
            logging.error(f"Veritabanından kur yükleme hatası: {e}")
        return False

    def convert_currency(self, amount, from_currency, to_currency):
        """Para birimleri arasında dönüşüm yapar."""
        if from_currency == to_currency or not amount:
            return amount
        
        rate = self.exchange_rates.get(to_currency) if from_currency == 'TRY' else self.exchange_rates.get(from_currency)
        if not rate: return 0.0

        if from_currency == 'TRY':
            return amount * rate
        if to_currency == 'TRY':
            return amount / rate
        
        # USD <-> EUR dönüşümü için önce TRY'ye çevir
        try_amount = self.convert_currency(amount, from_currency, 'TRY')
        return self.convert_currency(try_amount, 'TRY', to_currency)

    def format_date(self, date_str):
        """Tarih string'ini 'dd.mm.yyyy' formatına çevirir."""
        date_str = date_str.replace('.', '').replace('/', '')
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:2]}.{date_str[2:4]}.{date_str[4:]}"
        return datetime.now().strftime("%d.%m.%Y")

    def _process_invoice_data(self, invoice_data, is_update=False):
        """Fatura verilerini işler ve doğrular."""
        # Zorunlu alanları kontrol et
        required_fields = ['irsaliye_no', 'firma', 'malzeme']
        for field in required_fields:
            if not invoice_data.get(field, '').strip():
                print(f"Eksik veri: {invoice_data}")
                logging.warning(f"Eksik veri: {invoice_data}")
                return None
        
        try:            
            # Tarih formatını düzelt
            invoice_data['tarih'] = self.format_date(invoice_data.get('tarih', ''))
            
            # Miktar string olarak sakla
            invoice_data['miktar'] = str(invoice_data.get('miktar', '')).strip()
            
            # Sayısal değerleri işle
            # Sayısal değerleri ve KDV durumunu işle
            toplam_tutar = float(str(invoice_data.get('toplam_tutar', '0')).strip().replace(',', '.') or '0')
            kdv_yuzdesi = float(str(invoice_data.get('kdv_yuzdesi', '0')).strip().replace(',', '.') or '0')
            kdv_dahil = 1 if invoice_data.get('kdv_dahil', False) else 0
            
            # Matrahı (KDV'siz tutar) hesapla
            matrah = toplam_tutar
            if kdv_dahil and kdv_yuzdesi > 0:
                matrah = toplam_tutar / (1 + (kdv_yuzdesi / 100))
            
            # Para birimi dönüşümleri
            currency_amounts = self.calculate_currency_amounts(matrah, invoice_data['birim'])
            invoice_data.update(currency_amounts)
            
            # KDV tutarı hesapla
            invoice_data['kdv_yuzdesi'] = kdv_yuzdesi
            invoice_data['kdv_dahil'] = kdv_dahil
            invoice_data['kdv_tutari'] = (currency_amounts.get('toplam_tutar_tl', 0) * kdv_yuzdesi) / 100
            
            return invoice_data

        except (ValueError, TypeError) as e:
            print(f"Veri işleme hatası: {e}")
            logging.error(f"Veri işleme hatası: {e}")
            return None

    def calculate_currency_amounts(self, amount, from_currency):
        """Girilen tutar ve birime göre diğer para birimlerindeki değerleri hesaplar."""
        amounts = {'toplam_tutar_tl': 0.0, 'toplam_tutar_usd': 0.0, 'toplam_tutar_eur': 0.0}
        try:
            amount = float(amount)
            if from_currency == 'TL':
                amounts['toplam_tutar_tl'] = amount
                amounts['toplam_tutar_usd'] = self.convert_currency(amount, 'TRY', 'USD')
                amounts['toplam_tutar_eur'] = self.convert_currency(amount, 'TRY', 'EUR')
            elif from_currency == 'USD':
                amounts['toplam_tutar_tl'] = self.convert_currency(amount, 'USD', 'TRY')
                amounts['toplam_tutar_usd'] = amount
                amounts['toplam_tutar_eur'] = self.convert_currency(amount, 'USD', 'EUR')
            elif from_currency == 'EUR':
                amounts['toplam_tutar_tl'] = self.convert_currency(amount, 'EUR', 'TRY')
                amounts['toplam_tutar_usd'] = self.convert_currency(amount, 'EUR', 'USD')
                amounts['toplam_tutar_eur'] = amount
            return amounts
        except (ValueError, TypeError):
            return amounts

    def _invoice_operation(self, operation_type, invoice_type, *args):
        """Fatura işlemleri için merkezi bir metot."""
        table_name = f"{invoice_type}_invoices"
        should_emit_signal = False
        
        if operation_type == 'add':
            data = self._process_invoice_data(args[0])
            if data:
                new_id = self.db.add_invoice(table_name, data)
                if new_id:
                    self.status_updated.emit("Fatura başarıyla eklendi.", 3000)
                    self.data_updated.emit()
                    return True
        
        elif operation_type == 'update':
            invoice_id, data = args
            processed_data = self._process_invoice_data(data, is_update=True)
            if processed_data:
                self.db.update_invoice(table_name, invoice_id, processed_data)
                self.status_updated.emit("Fatura başarıyla güncellendi.", 3000)
                self.data_updated.emit()
                return True
        
        elif operation_type == 'delete':
            self.db.delete_invoice(table_name, args[0])
            self.status_updated.emit("Fatura silindi.", 3000)
            self.data_updated.emit()
            return True
        
        elif operation_type == 'get_all':
            return self.db.get_all_invoices(table_name)
        
        return False # Başarısız işlem durumu

    def add_outgoing_invoice(self, data): self._invoice_operation('add', 'outgoing', data)
    def add_incoming_invoice(self, data): self._invoice_operation('add', 'incoming', data)
    def update_outgoing_invoice(self, invoice_id, data): self._invoice_operation('update', 'outgoing', invoice_id, data)
    def update_incoming_invoice(self, invoice_id, data): self._invoice_operation('update', 'incoming', invoice_id, data)
    def delete_outgoing_invoice(self, invoice_id): self._invoice_operation('delete', 'outgoing', invoice_id)
    def delete_incoming_invoice(self, invoice_id): self._invoice_operation('delete', 'incoming', invoice_id)
    def get_all_outgoing_invoices(self): return self._invoice_operation('get_all', 'outgoing')
    def get_all_incoming_invoices(self): return self._invoice_operation('get_all', 'incoming')
    
    def handle_invoice_operation(self, operation, invoice_type, data=None, record_id=None):
        """Daha genel bir fatura işlemleri API'si sağlar."""
        if operation == 'add':
            return self._invoice_operation('add', invoice_type, data)
        elif operation == 'update':
            return self._invoice_operation('update', invoice_type, record_id, data)
        elif operation == 'delete':
            return self._invoice_operation('delete', invoice_type, record_id)
        elif operation == 'get':
            return self._invoice_operation('get_all', invoice_type)
        elif operation == 'get_by_id':
            # Tek bir fatura getirmek için
            invoices = self._invoice_operation('get_all', invoice_type)
            return next((inv for inv in invoices if inv.get('id') == record_id), None)

    def get_summary_data(self):
        """Gelir, gider ve kar/zarar özetini hesaplar."""
        outgoing_invoices = self.get_all_outgoing_invoices()
        incoming_invoices = self.get_all_incoming_invoices()

        # Toplam değerleri hesapla
        total_revenue = sum(inv.get('toplam_tutar_tl', 0) for inv in outgoing_invoices)
        total_expense = sum(inv.get('toplam_tutar_tl', 0) for inv in incoming_invoices)
        
        # Aylık dağılım
        monthly_income = [0] * 12
        monthly_expenses = [0] * 12
        current_year = datetime.now().year
        current_month = datetime.now().month
        active_months = set()
        
        # Gelir faturalarını aylara dağıt
        for inv in outgoing_invoices:
            try:
                inv_date = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                if inv_date.year == current_year:
                    month_idx = inv_date.month - 1
                    monthly_income[month_idx] += inv.get('toplam_tutar_tl', 0)
                    if monthly_income[month_idx] > 0:
                        active_months.add(inv_date.month)
            except (ValueError, KeyError):
                continue

        # Gider faturalarını aylara dağıt
        for inv in incoming_invoices:
            try:
                inv_date = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                if inv_date.year == current_year:
                    monthly_expenses[inv_date.month - 1] += inv.get('toplam_tutar_tl', 0)
            except (ValueError, KeyError):
                continue

        # Aylık ortalama hesapla
        active_months_count = len(active_months) or max(1, current_month)
        total_income_this_year = sum(monthly_income[:current_month])
        monthly_average = total_income_this_year / active_months_count
        
        # Net kar hesapla
        net_profit = total_revenue - total_expense
        profit_percentage = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            "son_gelirler": total_revenue,
            "toplam_giderler": total_expense,
            "net_kar": net_profit,
            "aylik_ortalama": monthly_average,
            "kar_yuzdesi": profit_percentage
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
            invoices = self._invoice_operation('get_all', invoice_type)
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
        """Belirli bir yıl için aylık ve çeyrek dönem hesaplamaları."""
        outgoing = self.get_all_outgoing_invoices()
        incoming = self.get_all_incoming_invoices()
        tax_rate = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0) / 100.0
        
        # Aylık sonuçlar
        monthly_results = []
        for month in range(1, 13):
            kesilen = sum(inv.get('toplam_tutar_tl', 0) for inv in outgoing 
                         if self._is_in_month_year(inv.get('tarih', ''), month, year))
            gelen = sum(inv.get('toplam_tutar_tl', 0) for inv in incoming 
                       if self._is_in_month_year(inv.get('tarih', ''), month, year))
            
            # KDV farkı
            kesilen_kdv = sum(inv.get('kdv_tutari', 0) for inv in outgoing 
                             if self._is_in_month_year(inv.get('tarih', ''), month, year))
            gelen_kdv = sum(inv.get('kdv_tutari', 0) for inv in incoming 
                           if self._is_in_month_year(inv.get('tarih', ''), month, year))
            
            monthly_results.append({
                'kesilen': kesilen,
                'gelen': gelen,
                'kdv': kesilen_kdv - gelen_kdv
            })
        
        # Çeyrek dönem sonuçları
        quarterly_results = []
        for quarter in range(4):
            period = monthly_results[quarter * 3:(quarter + 1) * 3]
            income = sum(d['kesilen'] for d in period)
            expense = sum(d['gelen'] for d in period)
            profit = income - expense
            tax = profit * tax_rate if profit > 0 else 0
            
            quarterly_results.append({'kar': profit, 'vergi': tax})
        
        return monthly_results, quarterly_results
    
    def get_yearly_summary(self, year):
        """Belirli bir yıl için yıllık özet."""
        outgoing = self.get_all_outgoing_invoices()
        incoming = self.get_all_incoming_invoices()
        
        gelir = sum(inv.get('toplam_tutar_tl', 0) for inv in outgoing if self._is_in_year(inv.get('tarih', ''), year))
        gider = sum(inv.get('toplam_tutar_tl', 0) for inv in incoming if self._is_in_year(inv.get('tarih', ''), year))
        net_kar = gelir - gider
        
        # Vergi hesapla
        tax_rate = self.settings.get('kurumlar_vergisi_yuzdesi', 22.0) / 100
        vergi = net_kar * tax_rate if net_kar > 0 else 0
        
        return {
            'toplam_gelir': gelir,
            'toplam_gider': gider,
            'yillik_kar': net_kar - vergi,
            'vergi_tutari': vergi,
            'vergi_yuzdesi': tax_rate * 100
        }
    
    def _is_in_month_year(self, date_str, month, year):
        """Tarihin belirtilen ay ve yılda olup olmadığını kontrol eder."""
        try:
            if not date_str:
                return False
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            return date_obj.month == month and date_obj.year == year
        except ValueError:
            return False
    
    def _is_in_year(self, date_str, year):
        """Tarihin belirtilen yılda olup olmadığını kontrol eder."""
        try:
            if not date_str:
                return False
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            return date_obj.year == year
        except ValueError:
            return False
    
    def export_to_excel(self, file_path, sheets_data):
        """Verilen verileri bir Excel dosyasına aktarır."""
        try:
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                for sheet_name, content in sheets_data.items():
                    pd.DataFrame(content["data"]).to_excel(writer, sheet_name=sheet_name, index=False)
            self.status_updated.emit(f"Veriler '{file_path}' dosyasına aktarıldı.", 5000)
        except Exception as e:
            print(f"Excel'e aktarma hatası: {e}")
            self.status_updated.emit("Excel'e aktarma başarısız oldu!", 5000)