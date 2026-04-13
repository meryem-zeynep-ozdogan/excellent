# invoices.py
# -*- coding: utf-8 -*-
"""
FATURA İŞLEME VE HESAPLAMA MODÜLÜ

Bu modül, fatura verilerinin doğrulanması, formatlanması ve
vergi/kur hesaplamalarının yapılmasından sorumludur.
"""

from imports import *


# ============================================================================
# FATURA İŞLEME SINIFI
# ============================================================================
class InvoiceProcessor:
    """
    Fatura verilerini işleyen, doğrulayan ve hesaplayan merkezi sınıf.
    Backend ile sıkı entegrasyon içinde çalışır.
    """
    
    def __init__(self, backend):
        """
        InvoiceProcessor başlatıcısı.
        
        Args:
            backend: Backend instance (settings, exchange_rates, convert_currency erişimi için)
        """
        self.backend = backend
    
    # ------------------------------------------------------------------------
    # YARDIMCI METOTLAR
    # ------------------------------------------------------------------------

    def _to_decimal(self, value):
        """
        Finansal hesaplamalar için güvenli Decimal dönüşümü yapar.
        Farklı sayı formatlarını (Avrupa/ABD) otomatik algılar.
        
        Örnekler:
        - "1.234,56" -> Decimal("1234.56") (Avrupa)
        - "1,234.56" -> Decimal("1234.56") (ABD)
        - "1234"     -> Decimal("1234.00")
        """
        if value is None or value == '': 
            return Decimal('0')
        
        try:
            # Eğer zaten Decimal ise direkt döndür
            if isinstance(value, Decimal):
                return value
            
            str_value = str(value).strip()
            
            if not str_value or str_value.lower() in ['none', 'null', 'n/a']:
                return Decimal('0')
            
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
            
            return Decimal(str_value)
            
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning(f"Decimal dönüşüm hatası: '{value}' -> Hata: {e}")
            return Decimal('0')

    def format_date(self, date_str):
        """
        Farklı formatlardaki tarih stringlerini standart 'dd.mm.yyyy' formatına çevirir.
        Desteklenen formatlar: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY vb.
        """
        # Boş string veya None ise None döndür (bugünün tarihi değil)
        if not date_str or (isinstance(date_str, str) and not date_str.strip()):
            return None
        
        # String değilse string'e çevir
        if not isinstance(date_str, str):
            date_str = str(date_str)
        
        date_str = date_str.strip()
        
        # Yaygın tarih formatlarını dene (4 basamaklı yıl)
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        # 2 basamaklı yıl içeren ayırıcılı formatları dene (örn: 12.12.25 -> 12.12.2025)
        for fmt in ("%d.%m.%y", "%d-%m-%y", "%d/%m/%y"):
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

    # ------------------------------------------------------------------------
    # ANA İŞLEM METOTLARI
    # ------------------------------------------------------------------------

    def process_invoice_data(self, invoice_data):
        """
        Fatura verilerini işler, doğrular ve KDV/kur hesaplamalarını yapar.
        Decimal kullanarak yüksek hassasiyetle para hesaplamaları yapar.
        """
        # Toplam tutar için hem 'toplam_tutar' hem de 'toplam_tutar_tl' alanlarını kontrol et
        toplam_tutar_raw = invoice_data.get('toplam_tutar') or invoice_data.get('toplam_tutar_tl')
        
        toplam_tutar = self._to_decimal(toplam_tutar_raw if toplam_tutar_raw is not None and str(toplam_tutar_raw).strip() != "" else 0)
        
        if toplam_tutar < 0:
            return None
        
        try:            
            processed = invoice_data.copy()
            
            # Toplam tutar alanını normalize et
            if 'toplam_tutar' not in processed and 'toplam_tutar_tl' in processed:
                processed['toplam_tutar'] = processed['toplam_tutar_tl']
            
            # Boş alanları olduğu gibi bırak
            processed['fatura_no'] = processed.get('fatura_no', '').strip()
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
            
            toplam_tutar = self._to_decimal(processed.get('toplam_tutar', 0))
            kdv_yuzdesi = self._to_decimal(processed.get('kdv_yuzdesi', 0))
            kdv_tutari_input = self._to_decimal(processed.get('kdv_tutari', 0)) 
            birim = processed.get('birim', 'TL')
            
            logging.debug(f"\n   🧾 FATURA İŞLEME BAŞLADI (MATRAH SİSTEMİ - DECIMAL)")
            logging.debug(f"   📋 Giriş Verileri:")
            logging.debug(f"     - Girilen Matrah: {toplam_tutar} {birim}")
            logging.debug(f"     - KDV Yüzdesi: {kdv_yuzdesi}%")
            
            # KDV yüzdesi kontrolü
            if kdv_yuzdesi <= 0:
                kdv_yuzdesi = self._to_decimal(self.backend.settings.get('kdv_yuzdesi', 20.0))
                logging.debug(f"   ⚙️ KDV yüzdesi girilmedi, varsayılan kullanılıyor: {kdv_yuzdesi}%")
            
            # Manuel kur girişi kontrolü - önce kontrol et
            manual_usd_rate = invoice_data.get('manual_usd_rate', None)
            manual_eur_rate = invoice_data.get('manual_eur_rate', None)
            
            # Toplu işlemden gelen kur bilgisi (Tarihli kur)
            bulk_exchange_rates = invoice_data.get('exchange_rates', {})
            
            if manual_usd_rate and manual_usd_rate > 0:
                # Manuel USD kuru girilmiş (1 USD = ? TL formatında)
                usd_to_tl = manual_usd_rate
                logging.debug(f"   💱 Manuel USD kuru kullanılıyor: 1 USD = {usd_to_tl} TL")
            elif bulk_exchange_rates and 'USD' in bulk_exchange_rates:
                # Toplu işlemden gelen kur
                usd_to_tl = bulk_exchange_rates.get('USD', 0)
                logging.debug(f"   💱 Tarihli USD kuru kullanılıyor: 1 USD = {usd_to_tl} TL")
            else:
                # TCMB kurunu kullan (cache'den)
                current_rates = self.backend.exchange_rates
                usd_rate = current_rates.get('USD', 0)
                usd_to_tl = (1 / usd_rate) if usd_rate > 0 else 0
                logging.debug(f"   💱 Cache'den USD kuru: 1 USD = {usd_to_tl} TL")
            
            if manual_eur_rate and manual_eur_rate > 0:
                # Manuel EUR kuru girilmiş (1 EUR = ? TL formatında)
                eur_to_tl = manual_eur_rate
                logging.debug(f"   💱 Manuel EUR kuru kullanılıyor: 1 EUR = {eur_to_tl} TL")
            elif bulk_exchange_rates and 'EUR' in bulk_exchange_rates:
                # Toplu işlemden gelen kur
                eur_to_tl = bulk_exchange_rates.get('EUR', 0)
                logging.debug(f"   💱 Tarihli EUR kuru kullanılıyor: 1 EUR = {eur_to_tl} TL")
            else:
                # TCMB kurunu kullan (cache'den)
                current_rates = self.backend.exchange_rates
                eur_rate = current_rates.get('EUR', 0)
                eur_to_tl = (1 / eur_rate) if eur_rate > 0 else 0
                logging.debug(f"   💱 Cache'den EUR kuru: 1 EUR = {eur_to_tl} TL")

            # KDV HESAPLAMA - Girilen tutar tabloda aynı kalır, KDV ayrıca hesaplanır
            # KDV = Girilen Tutar × KDV% (100 TL için %20 = 20 TL KDV)
            if toplam_tutar >= 0:
                try:
                    # Önce TL'ye çevir
                    conversion_rate = Decimal('1.0')
                    if birim == 'USD':
                        # Float'tan Decimal'e çevirirken string kullanmak daha güvenli
                        # Ancak float 'nan' veya 'inf' ise hata verebilir, kontrol et
                        if math.isnan(usd_to_tl) or math.isinf(usd_to_tl):
                            conversion_rate = Decimal('0')
                        else:
                            conversion_rate = Decimal(str(usd_to_tl))
                    elif birim == 'EUR':
                        if math.isnan(eur_to_tl) or math.isinf(eur_to_tl):
                            conversion_rate = Decimal('0')
                        else:
                            conversion_rate = Decimal(str(eur_to_tl))
                    
                    # Girilen tutarı TL'ye çevir ve MATRAH olarak kaydet
                    matrah_tl_decimal = toplam_tutar * conversion_rate

                    # KDV tutarını matrah üzerinden hesapla
                    # Örnek: Matrah 100 TL, KDV %20 → KDV = 100 × 0.20 = 20 TL
                    kdv_tutari_tl = matrah_tl_decimal * (kdv_yuzdesi / Decimal('100'))
                    
                    # Toplam tutarı hesapla (Matrah + KDV)
                    # Örnek: 100 + 20 = 120 TL
                    toplam_tutar_tl_decimal = matrah_tl_decimal + kdv_tutari_tl
                    
                    # 5 ondalık basamağa yuvarla
                    toplam_tutar_tl_decimal = toplam_tutar_tl_decimal.quantize(Decimal('0.00001'))
                    kdv_tutari_tl = kdv_tutari_tl.quantize(Decimal('0.00001'))
                    matrah_tl_decimal = matrah_tl_decimal.quantize(Decimal('0.00001'))
                    
                    logging.debug(f"   ✅ KDV HESAPLAMA (MATRAH ESASLI):")
                    logging.debug(f"     - Girilen Matrah: {toplam_tutar} {birim}")
                    logging.debug(f"     - Kur: {conversion_rate}")
                    logging.debug(f"     - Matrah (TL): {matrah_tl_decimal} TL")
                    logging.debug(f"     - KDV Oranı: %{kdv_yuzdesi}")
                    logging.debug(f"     - KDV Tutarı (TL): {kdv_tutari_tl} TL")
                    logging.debug(f"     - Genel Toplam (TL): {toplam_tutar_tl_decimal} TL")
                    
                except Exception as calc_err:
                    logging.error(f"   ❌ Hesaplama hatası (Decimal): {calc_err}")
                    # Hata durumunda varsayılan değerler
                    toplam_tutar_tl_decimal = Decimal('0')
                    kdv_tutari_tl = Decimal('0')
                    
            else:
                logging.error(f"   ❌ HATA: Toplam tutar girilmemiş!")
                return None
            
            # Toplam tutar girilen değer olarak kalır (artırılmaz)
            toplam_kdv_dahil_tl = toplam_tutar_tl_decimal

            # Sonuç verilerini hazırla - toplam_tutar_tl girilen tutar olarak kalır
            # Tüm tutarları 5 ondalık basamağa yuvarla
            processed['toplam_tutar_tl'] = round(float(toplam_kdv_dahil_tl), 5)
            
            # USD ve EUR tutarlarını manuel kurlar ile hesapla
            if usd_to_tl > 0:
                processed['toplam_tutar_usd'] = round(float(toplam_kdv_dahil_tl) / usd_to_tl, 5)
            else:
                processed['toplam_tutar_usd'] = 0
                
            if eur_to_tl > 0:
                processed['toplam_tutar_eur'] = round(float(toplam_kdv_dahil_tl) / eur_to_tl, 5)
            else:
                processed['toplam_tutar_eur'] = 0
            
            # Orijinal para birimindeki toplam tutarı da güncelle (Matrah -> Toplam)
            if birim == 'TL':
                processed['toplam_tutar'] = processed['toplam_tutar_tl']
            elif birim == 'USD':
                processed['toplam_tutar'] = processed['toplam_tutar_usd']
            elif birim == 'EUR':
                processed['toplam_tutar'] = processed['toplam_tutar_eur']
            
            processed['birim'] = birim 
            processed['kdv_yuzdesi'] = round(float(kdv_yuzdesi), 5)
            processed['kdv_dahil'] = 1  # Her zaman KDV dahil
            processed['kdv_tutari'] = round(float(kdv_tutari_tl), 5)
            processed['usd_rate'] = round(float(usd_to_tl), 5)
            processed['eur_rate'] = round(float(eur_to_tl), 5)
            processed['matrah'] = round(float(matrah_tl_decimal), 5)
            
            logging.debug(f"   📊 SONUÇ (TL CİNSİNDEN):")
            logging.debug(f"     - Matrah: {matrah_tl_decimal:.2f} TL")
            logging.debug(f"     - KDV Tutarı: {kdv_tutari_tl:.2f} TL") 
            logging.debug(f"     - TOPLAM (KDV DAHİL): {toplam_kdv_dahil_tl:.2f} TL")
            logging.debug(f"   ✅ İşlem başarılı!\n")
            
            return processed

        except (ValueError, TypeError) as e:
            logging.error(f"❌ Fatura veri işleme hatası: {e} - Veri: {invoice_data}")
            return None

    def process_genel_gider_data(self, gider_data):
        """Genel gider verilerini genel_gider.db formatına çevirir. Decimal kullanır."""
        if not gider_data:
            return None
        
        # Miktar alanını hem sayı hem metin olarak kabul et
        miktar_input = gider_data.get('miktar', '')
        if not miktar_input or str(miktar_input).strip() == '':
            logging.warning(f"Genel gider miktarı girilmemiş: {gider_data}")
            return None
        
        # Eğer sayısal bir değer ise float'a çevir, değilse string olarak bırak
        try:
            miktar_float = float(miktar_input)
            # 5 ondalık basamağa yuvarla
            miktar = round(miktar_float, 5)
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


# ============================================================================
# FATURA YÖNETİM SINIFI
# ============================================================================
class InvoiceManager:
    """Fatura operasyonlarını yöneten sınıf."""
    
    def __init__(self, backend):
        """
        InvoiceManager başlatıcısı.
        
        Args:
            backend: Backend instance (db, data_updated sinyal erişimi için)
        """
        self.backend = backend
        self.processor = InvoiceProcessor(backend)
    
    def handle_invoice_operation(self, operation, invoice_type, data=None, record_id=None, limit=None, offset=None, order_by=None):
        """Frontend için fatura işlem merkezi - 3 ayrı veritabanı ile."""
        
        if operation == 'add':
            processed_data = self.processor.process_invoice_data(data)
            if not processed_data:
                logging.error(f"❌ İşlenmiş veri boş! Ham veri: {data}")
                return False
            
            logging.info(f"🔹 Fatura ekleniyor -> Tip: {invoice_type}, Firma: {processed_data.get('firma', 'N/A')[:30]}")
            
            if invoice_type == 'outgoing':
                result = self.backend.db.add_gelir_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gelir', processed_data)
                    logging.info(f"✅ GELİR faturası eklendi (ID: {result})")
                else:
                    logging.error(f"❌ GELİR faturası eklenemedi!")
            elif invoice_type == 'incoming':
                result = self.backend.db.add_gider_invoice(processed_data)
                if result:
                    self._add_history_record('EKLEME', 'gider', processed_data)
                    logging.info(f"✅ GİDER faturası eklendi (ID: {result})")
                else:
                    logging.error(f"❌ GİDER faturası eklenemedi!")
            else:
                logging.error(f"❌ Geçersiz invoice_type: {invoice_type}")
                return False
                
            if result:
                if self.backend.on_data_updated: self.backend.on_data_updated()
                return True
            return False
        
        elif operation == 'update':
            processed_data = self.processor.process_invoice_data(data)
            if not processed_data:
                return False
            
            if invoice_type == 'outgoing':
                result = self.backend.db.update_gelir_invoice(record_id, processed_data)
                if result:
                    self._add_history_record('GÜNCELLEME', 'gelir', processed_data)
            elif invoice_type == 'incoming':
                result = self.backend.db.update_gider_invoice(record_id, processed_data)
                if result:
                    self._add_history_record('GÜNCELLEME', 'gider', processed_data)
            else:
                return False
                
            if result:
                if self.backend.on_data_updated: self.backend.on_data_updated()
                return True
            return False
        
        elif operation == 'delete':
            # Silmeden önce fatura bilgilerini al
            if invoice_type == 'outgoing':
                invoice_data = self.backend.db.get_gelir_invoice_by_id(record_id)
                result = self.backend.db.delete_gelir_invoice(record_id)
                if result and invoice_data:
                    self._add_history_record('SİLME', 'gelir', invoice_data)
            elif invoice_type == 'incoming':
                invoice_data = self.backend.db.get_gider_invoice_by_id(record_id)
                result = self.backend.db.delete_gider_invoice(record_id)
                if result and invoice_data:
                    self._add_history_record('SİLME', 'gider', invoice_data)
            else:
                return False
                
            if result:
                if self.backend.on_data_updated: self.backend.on_data_updated()
                return True
            return False
        
        elif operation == 'get':
            if invoice_type == 'outgoing':
                # Rust tarafı limit, offset, order_by parametrelerini opsiyonel olarak bekliyor
                return self.backend.db.get_all_gelir_invoices(limit, offset, order_by)
            elif invoice_type == 'incoming':
                return self.backend.db.get_all_gider_invoices(limit, offset, order_by)
            else:
                return []
        
        elif operation == 'count':
            if invoice_type == 'outgoing':
                return self.backend.db.get_gelir_invoice_count()
            elif invoice_type == 'incoming':
                return self.backend.db.get_gider_invoice_count()
            else:
                return 0
        
        elif operation == 'get_by_id':
            if invoice_type == 'outgoing':
                return self.backend.db.get_gelir_invoice_by_id(record_id)
            elif invoice_type == 'incoming':
                return self.backend.db.get_gider_invoice_by_id(record_id)
            else:
                return None
        
        logging.warning(f"Geçersiz fatura operasyonu: {operation}")
        return False

    def handle_genel_gider_operation(self, operation, data=None, record_id=None, limit=None, offset=None):
        """Genel gider işlemleri için özel metod - ayrı veritabanı ile."""
        
        if operation == 'get':
            return self.backend.db.get_all_yearly_expenses()
        
        elif operation == 'count':
            return self.backend.db.get_yearly_expenses_count()
        
        elif operation == 'get_by_id':
            return self.backend.db.get_yearly_expenses_by_id(record_id)
        
        return None

    def delete_multiple_invoices(self, invoice_type, invoice_ids):
        """Çoklu fatura silme işlemi - 3 ayrı veritabanı ile."""
        try:
            if invoice_type == 'outgoing':
                deleted_count = self.backend.db.delete_multiple_gelir_invoices(invoice_ids)
            elif invoice_type == 'incoming':
                deleted_count = self.backend.db.delete_multiple_gider_invoices(invoice_ids)
            else:
                return 0
                
            if deleted_count > 0:
                if self.backend.on_data_updated: self.backend.on_data_updated()
            return deleted_count
        except Exception as e:
            logging.error(f"Çoklu {invoice_type} faturası silme hatası: {e}")
            return 0

    def _add_history_record(self, operation_type, invoice_type, invoice_data=None, details=None):
        """Fatura işlemlerinde geçmiş kaydı ekler."""
        try:
            # İşlem tipine göre detay mesajı oluştur
            if not details:
                firma = None
                amount = None
                birim = 'TL'
                invoice_date = None
                
                if invoice_data:
                    invoice_date = invoice_data.get('tarih')
                    firma = invoice_data.get('firma') or invoice_data.get('tur')
                    # MATRAH (KDV hariç) kullan
                    amount = invoice_data.get('matrah') or invoice_data.get('toplam_tutar_tl') or invoice_data.get('miktar')
                    birim = invoice_data.get('birim', 'TL')
                
                if operation_type == 'EKLEME':
                    details = f"{invoice_type.title()} fatura eklendi"
                elif operation_type == 'GÜNCELLEME':
                    details = f"{invoice_type.title()} fatura güncellendi"
                elif operation_type == 'SİLME':
                    details = f"{invoice_type.title()} fatura silindi"
                else:
                    details = f"{operation_type} işlemi"
                
                # Detaylı bilgi ekle
                if firma:
                    details += f" - Firma: {firma}"
                if amount:
                    details += f" - Tutar: {amount}|{birim}"  # Birim bilgisi eklendi
                if invoice_date:
                    details += f" - Tarih: {invoice_date}"
            
            # Rust modülü sadece action ve details alıyor
            action = f"{operation_type}_{invoice_type.upper()}"
            self.backend.db.add_history_record(action, details)
            
        except Exception as e:
            logging.error(f"Geçmiş kaydı ekleme hatası: {e}")


# ============================================================================
# DÖNEMSEL GELİR HESAPLAMALARI (Periodic Income Calculations)
# ============================================================================

class PeriodicIncomeCalculator:
    """Dönemsel gelir, gider ve kar/zarar hesaplamaları yapan sınıf."""
    
    def __init__(self, backend):
        """
        PeriodicIncomeCalculator başlatıcısı.
        
        Args:
            backend: Backend instance (db, settings erişimi için)
        """
        self.backend = backend
    
    def get_summary_data(self):
        """Gelir, gider ve kar/zarar özetini hesaplar - Rust async DB ile."""
        try:
            # Tüm gelirleri al
            gelir_invoices = self.backend.db.get_all_gelir_invoices(None, None) or []
            total_revenue_kdv_dahil = sum(inv.get('toplam_tutar_tl', 0) or 0 for inv in gelir_invoices)
            total_revenue_kdv = sum(inv.get('kdv_tutari', 0) or 0 for inv in gelir_invoices)
            total_revenue = total_revenue_kdv_dahil - total_revenue_kdv  # Matrah (KDV hariç)
            
            # Tüm giderleri al
            gider_invoices = self.backend.db.get_all_gider_invoices(None, None) or []
            invoice_expenses_kdv_dahil = sum(inv.get('toplam_tutar_tl', 0) or 0 for inv in gider_invoices)
            invoice_expenses_kdv = sum(inv.get('kdv_tutari', 0) or 0 for inv in gider_invoices)
            invoice_expenses = invoice_expenses_kdv_dahil - invoice_expenses_kdv  # Matrah (KDV hariç)
            
            # Genel giderleri al (yıllık)
            current_year = datetime.now().year
            yearly_expenses = self.backend.db.get_yearly_expenses(current_year)
            general_expenses = 0
            if yearly_expenses:
                months = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran',
                         'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
                general_expenses = sum(yearly_expenses.get(month, 0) or 0 for month in months)
            
            # Toplam gider
            total_expense = invoice_expenses + general_expenses
            
            # Aylık veriler
            monthly_income = [0] * 12
            monthly_expenses = [0] * 12
            
            # Gelir aylık dağılım
            for inv in gelir_invoices:
                try:
                    tarih = inv.get('tarih', '')
                    if tarih:
                        parts = tarih.split('.')
                        if len(parts) == 3 and parts[2] == str(current_year):
                            month = int(parts[1]) - 1
                            if 0 <= month < 12:
                                monthly_income[month] += inv.get('toplam_tutar_tl', 0) or 0
                except:
                    continue
            
            # Gider aylık dağılım (faturalar)
            for inv in gider_invoices:
                try:
                    tarih = inv.get('tarih', '')
                    if tarih:
                        parts = tarih.split('.')
                        if len(parts) == 3 and parts[2] == str(current_year):
                            month = int(parts[1]) - 1
                            if 0 <= month < 12:
                                monthly_expenses[month] += inv.get('toplam_tutar_tl', 0) or 0
                except:
                    continue
            
            # Genel giderler aylık dağılım
            if yearly_expenses:
                months = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran',
                         'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
                for i, month in enumerate(months):
                    monthly_expenses[i] += yearly_expenses.get(month, 0) or 0
            
            active_income_months = sum(1 for income in monthly_income if income > 0)
            total_income_this_year = sum(monthly_income)
            monthly_average = total_income_this_year / active_income_months if active_income_months > 0 else 0
            
        except Exception as e:
            logging.error(f"Özet veri hesaplama hatası: {e}")
            return {
                'total_revenue': 0,
                'total_expense': 0,
                'net_profit': 0,
                'monthly_income': [0] * 12,
                'monthly_expenses': [0] * 12,
                'monthly_average': 0
            }
        
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
        """Fatura verilerinde bulunan tüm yılların listesini döndürür - Rust async DB ile."""
        years_set = set()
        current_year = datetime.now().year
        
        years_set.add(str(current_year))
        
        try:
            # Gelir veritabanından yılları al
            gelir_invoices = self.backend.db.get_all_gelir_invoices(None, None) or []
            for inv in gelir_invoices:
                try:
                    if 'tarih' in inv and inv['tarih']:
                        date_obj = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                        years_set.add(str(date_obj.year))
                except (ValueError, KeyError):
                    continue
            
            # Gider veritabanından yılları al
            gider_invoices = self.backend.db.get_all_gider_invoices(None, None) or []
            for inv in gider_invoices:
                try:
                    if 'tarih' in inv and inv['tarih']:
                        date_obj = datetime.strptime(inv['tarih'], "%d.%m.%Y")
                        years_set.add(str(date_obj.year))
                except (ValueError, KeyError):
                    continue
            
            # Genel gider veritabanından yılları al
            yearly_expenses_list = self.backend.db.get_all_yearly_expenses() or []
            for expense_record in yearly_expenses_list:
                try:
                    if 'yil' in expense_record:
                        years_set.add(str(expense_record['yil']))
                except (ValueError, KeyError):
                    continue
        except Exception as e:
            logging.error(f"Yıl aralığı alma hatası: {e}")
        
        return sorted(list(years_set), reverse=True)
    
    def get_calculations_for_year(self, year):
        """Belirli bir yıl için aylık ve çeyrek dönem hesaplamaları - Rust async DB ile."""
        # Vergi oranını güvenli şekilde float'a dönüştür
        tax_rate_raw = self.backend.settings.get('kurumlar_vergisi_yuzdesi', 22.0)
        tax_rate = float(tax_rate_raw) / 100.0
        
        # Tüm faturaları al
        gelir_invoices = self.backend.db.get_all_gelir_invoices(None, None) or []
        gider_invoices = self.backend.db.get_all_gider_invoices(None, None) or []
        yearly_expenses = self.backend.db.get_yearly_expenses(year)
        
        monthly_results = []
        months_tr = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran',
                     'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
        
        for month in range(1, 13):
            month_str = f"{month:02d}"
            
            # Gelir hesapla - toplam_tutar_tl KDV dahil, kar için matrah hesaplayalım
            kesilen_kdv_dahil = 0
            kesilen_kdv = 0
            for inv in gelir_invoices:
                try:
                    tarih = inv.get('tarih', '')
                    if tarih:
                        parts = tarih.split('.')
                        if len(parts) == 3 and parts[1] == month_str and parts[2] == str(year):
                            kesilen_kdv_dahil += inv.get('toplam_tutar_tl', 0) or 0
                            kesilen_kdv += inv.get('kdv_tutari', 0) or 0
                except:
                    continue
            
            kesilen_matrah = kesilen_kdv_dahil - kesilen_kdv  # KDV dahil tutardan matrahı çıkar
            
            # Fatura giderleri hesapla
            fatura_giderleri_kdv_dahil = 0
            fatura_gider_kdv = 0
            for inv in gider_invoices:
                try:
                    tarih = inv.get('tarih', '')
                    if tarih:
                        parts = tarih.split('.')
                        if len(parts) == 3 and parts[1] == month_str and parts[2] == str(year):
                            fatura_giderleri_kdv_dahil += inv.get('toplam_tutar_tl', 0) or 0
                            fatura_gider_kdv += inv.get('kdv_tutari', 0) or 0
                except:
                    continue
            
            fatura_giderleri_matrah = fatura_giderleri_kdv_dahil - fatura_gider_kdv
            
            # Genel giderleri hesapla
            genel_giderler = 0
            if yearly_expenses:
                month_key = months_tr[month - 1]
                genel_giderler = yearly_expenses.get(month_key, 0) or 0
            
            # Toplam gider (matrah bazında)
            toplam_gider_matrah = fatura_giderleri_matrah + genel_giderler
            
            monthly_results.append({
                'kesilen': kesilen_matrah,  # Kar hesabı için matrah kullanılıyor
                'gelen': toplam_gider_matrah,
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
        """Belirli bir yıl için yıllık özet - Rust async DB ile."""
        
        # Tüm faturaları al
        gelir_invoices = self.backend.db.get_all_gelir_invoices(None, None) or []
        gider_invoices = self.backend.db.get_all_gider_invoices(None, None) or []
        yearly_expenses = self.backend.db.get_yearly_expenses(year)
        
        # Gelir hesapla (KDV dahil tutardan matrahı çıkar)
        gelir_kdv_dahil = 0
        gelir_kdv = 0
        for inv in gelir_invoices:
            try:
                tarih = inv.get('tarih', '')
                if tarih and tarih.endswith(str(year)):
                    gelir_kdv_dahil += inv.get('toplam_tutar_tl', 0) or 0
                    gelir_kdv += inv.get('kdv_tutari', 0) or 0
            except:
                continue
        
        gelir_matrah = gelir_kdv_dahil - gelir_kdv
        
        # Fatura giderleri hesapla (KDV dahil tutardan matrahı çıkar)
        fatura_giderleri_kdv_dahil = 0
        fatura_giderleri_kdv = 0
        for inv in gider_invoices:
            try:
                tarih = inv.get('tarih', '')
                if tarih and tarih.endswith(str(year)):
                    fatura_giderleri_kdv_dahil += inv.get('toplam_tutar_tl', 0) or 0
                    fatura_giderleri_kdv += inv.get('kdv_tutari', 0) or 0
            except:
                continue
        
        fatura_giderleri_matrah = fatura_giderleri_kdv_dahil - fatura_giderleri_kdv
        
        # Genel giderleri hesapla
        genel_giderler = 0
        if yearly_expenses:
            months = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran',
                     'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
            genel_giderler = sum(yearly_expenses.get(month, 0) or 0 for month in months)
        
        # Toplam gider (matrah bazında)
        toplam_gider_matrah = fatura_giderleri_matrah + genel_giderler
        
        brut_kar = gelir_matrah - toplam_gider_matrah
        
        # Vergi oranını güvenli şekilde float'a dönüştür
        tax_rate_raw = self.backend.settings.get('kurumlar_vergisi_yuzdesi', 22.0)
        tax_rate = float(tax_rate_raw) / 100
        vergi = brut_kar * tax_rate if brut_kar > 0 else 0
        
        return {
            'toplam_gelir': gelir_matrah,
            'toplam_gider': toplam_gider_matrah,
            'yillik_kar': brut_kar - vergi, # Net kar
            'vergi_tutari': vergi,
            'vergi_yuzdesi': tax_rate * 100
        }
