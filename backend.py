# backend.py
# -*- coding: utf-8 -*-

# Merkezi import dosyasından gerekli modülleri al
from imports import *
from db import Database
from invoices import InvoiceProcessor, InvoiceManager, PeriodicIncomeCalculator


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
        
        # Fatura işleyici ve yönetici
        self.invoice_processor = InvoiceProcessor(self)
        self.invoice_manager = InvoiceManager(self)
        
        # Dönemsel gelir hesaplayıcı
        self.periodic_calculator = PeriodicIncomeCalculator(self)
        
        # QR Entegrasyon - Lazy loading (gerektiğinde yüklenecek)
        self._qr_integrator = None
        
        # Kurları başlangıçta bir kez çek
        self.update_exchange_rates()

    @property
    def qr_integrator(self):
        """QR entegratörünü lazy loading ile başlatır - OPTİMİZE EDİLMİŞ MODÜL."""
        if self._qr_integrator is None:
            from fromqr import QRInvoiceIntegrator
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
        Decimal ve float değerleri destekler.
        """
        if not amount:
            return 0.0
        
        # Decimal'i float'a çevir
        if isinstance(amount, Decimal):
            amount = float(amount)
        
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

    def handle_invoice_operation(self, operation, invoice_type, data=None, record_id=None, limit=None, offset=None, order_by=None):
        """Frontend için fatura işlem merkezi - InvoiceManager'a yönlendirir."""
        return self.invoice_manager.handle_invoice_operation(operation, invoice_type, data, record_id, limit, offset, order_by)

    def handle_genel_gider_operation(self, operation, data=None, record_id=None, limit=None, offset=None):
        """Genel gider işlemleri - InvoiceManager'a yönlendirir."""
        return self.invoice_manager.handle_genel_gider_operation(operation, data, record_id, limit, offset)

    def delete_multiple_invoices(self, invoice_type, invoice_ids):
        """Çoklu fatura silme - InvoiceManager'a yönlendirir."""
        return self.invoice_manager.delete_multiple_invoices(invoice_type, invoice_ids)

    def delete_multiple_genel_gider(self, gider_ids):
        """Çoklu genel gider silme - InvoiceManager'a yönlendirir."""
        return self.invoice_manager.delete_multiple_genel_gider(gider_ids)

    # ============================================================================
    # DÖNEMSEL GELİR HESAPLAMALARI (Periodic Income Calculations)
    # ============================================================================

    def get_summary_data(self):
        """Gelir, gider ve kar/zarar özetini hesaplar - PeriodicIncomeCalculator'a yönlendirir."""
        return self.periodic_calculator.get_summary_data()
    
    def get_year_range(self):
        """Fatura verilerinde bulunan tüm yılların listesini döndürür - PeriodicIncomeCalculator'a yönlendirir."""
        return self.periodic_calculator.get_year_range()
    
    def get_calculations_for_year(self, year):
        """Belirli bir yıl için aylık ve çeyrek dönem hesaplamaları - PeriodicIncomeCalculator'a yönlendirir."""
        return self.periodic_calculator.get_calculations_for_year(year)
    
    def get_yearly_summary(self, year):
        """Belirli bir yıl için yıllık özet - PeriodicIncomeCalculator'a yönlendirir."""
        return self.periodic_calculator.get_yearly_summary(year)

    # ============================================================================
    # İŞLEM GEÇMİŞİ YÖNETİMİ (History Management)
    # ============================================================================
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

    # ============================================================================
    # AYARLAR YÖNETİMİ (Settings Management)
    # ============================================================================
    
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

    # ============================================================================
    # YARDIMCI FONKSİYONLAR (Helper Functions)
    # ============================================================================
    
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
    
    def format_date(self, date_str):
        """Tarih string'ini DD.MM.YYYY formatına dönüştürür."""
        if not date_str:
            return datetime.now().strftime("%d.%m.%Y")
        
        try:
            # Zaten DD.MM.YYYY formatındaysa direkt döndür
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', str(date_str)):
                return str(date_str)
            
            # YYYY-MM-DD formatı
            if re.match(r'^\d{4}-\d{2}-\d{2}', str(date_str)):
                date_obj = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
                return date_obj.strftime('%d.%m.%Y')
            
            # DD/MM/YYYY formatı
            if re.match(r'^\d{2}/\d{2}/\d{4}$', str(date_str)):
                return str(date_str).replace('/', '.')
            
            # Varsayılan olarak bugünün tarihi
            return datetime.now().strftime("%d.%m.%Y")
        except Exception as e:
            logging.warning(f"Tarih formatı dönüştürülemedi: {date_str}, hata: {e}")
            return datetime.now().strftime("%d.%m.%Y")
    
    # ============================================================================
    # QR İŞLEMLERİ - ENTEGRE SİSTEM (QR Operations - Integrated System)
    # ============================================================================
     
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