# -*- coding: utf-8 -*-
"""
Excel Export Module for Invoice Management System
Bu modül fatura listelerini Excel formatına dönüştürür
"""

# Merkezi import dosyasından gerekli modülleri al
from imports import *

class InvoiceExcelExporter:
    """Fatura listelerini Excel'e dönüştüren sınıf"""
    
    def __init__(self):
        self.excel_folder = "ExcelReports"
        if not os.path.exists(self.excel_folder):
            os.makedirs(self.excel_folder)
    
    def _auto_adjust_column_widths(self, writer, sheet_name, df):
        """Sütun genişliklerini içeriğe göre otomatik ayarla"""
        try:
            worksheet = writer.sheets[sheet_name]
            workbook = writer.book
            
            # Header formatı
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#6C5DD3',
                'font_color': 'white',
                'border': 1
            })
            
            # Veri formatı
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1
            })
            
            # Tutar formatı (2 ondalık)
            money_format = workbook.add_format({
                'num_format': '#,##0.00',
                'valign': 'top',
                'border': 1
            })
            
            # Döviz kuru formatı (5 ondalık)
            currency_format = workbook.add_format({
                'num_format': '#,##0.00000',
                'valign': 'top',
                'border': 1
            })
            
            for i, col in enumerate(df.columns):
                # Kolon başlığının uzunluğu
                header_len = len(str(col))
                
                # Kolon verilerinin maksimum uzunluğu
                if len(df) > 0:
                    max_len = df[col].astype(str).map(len).max()
                    # En uzun değeri bul, ancak çok uzun olmasın
                    col_width = min(max(max_len, header_len) + 2, 50)
                else:
                    col_width = header_len + 2
                
                # Minimum genişlik
                col_width = max(col_width, 10)
                
                # Sütun genişliğini ayarla
                worksheet.set_column(i, i, col_width)
                
                # Header'ı formatla
                worksheet.write(0, i, col, header_format)
                
                # Veri tipine göre format uygula
                if len(df) > 0:
                    for row_num in range(1, len(df) + 1):
                        cell_value = df.iloc[row_num-1, i]
                        if col in ['TUTAR (TL)', 'KDV TUTARI', 'TUTAR', 'MİKTAR'] and isinstance(cell_value, (int, float)):
                            worksheet.write(row_num, i, cell_value, money_format)
                        elif col in ['TUTAR (USD)', 'TUTAR (EUR)'] and isinstance(cell_value, (int, float)):
                            worksheet.write(row_num, i, cell_value, currency_format)
                        else:
                            worksheet.write(row_num, i, cell_value, cell_format)
                            
        except Exception as e:
            logging.error(f"Sütun genişlik ayarlama hatası: {e}")
    
    def export_to_excel(self, file_path, sheets_data):
        """
        Verilen verileri bir Excel dosyasına aktarır ve sütun genişliklerini otomatik ayarlar
        
        Args:
            file_path (str): Excel dosya yolu
            sheets_data (dict): Sayfa adları ve verileri içeren sözlük
        
        Returns:
            bool: Başarılı ise True, aksi halde False
        """
        try:
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                for sheet_name, content in sheets_data.items():
                    df = pd.DataFrame(content.get("data", []))
                    if not df.empty:
                        # Veriyi yaz (header olmadan)
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=1)
                        # Sütun genişliklerini ve formatları ayarla
                        self._auto_adjust_column_widths(writer, sheet_name, df)
            
            print(f"Veriler '{os.path.basename(file_path)}' dosyasına aktarıldı.")
            return True
        except Exception as e:
            logging.error(f"Excel'e aktarma hatası: {e}")
            print(f"Excel'e aktarma başarısız oldu! Hata: {e}")
            return False

    def _format_date(self, date_str):
        """Tarih formatını düzenle"""
        if not date_str:
            return ''
        
        if '-' in date_str:
            try:
                year, month, day = date_str.split('-')
                return f"{day}.{month}.{year}"
            except:
                return date_str
        return date_str
    
    def _prepare_invoice_data(self, invoice_data):
        """Fatura verilerini Excel formatına hazırla"""
        excel_data = []
        for invoice in invoice_data:
            row = {
                'FATURA NO': invoice.get('fatura_no', ''),
                'TARİH': self._format_date(invoice.get('tarih', '')),
                'FİRMA': invoice.get('firma', ''),
                'MALZEME': invoice.get('malzeme', ''),
                'MİKTAR': invoice.get('miktar', ''),
                'TUTAR (TL)': float(invoice.get('toplam_tutar_tl', 0) or 0),
                'KDV TUTARI': float(invoice.get('kdv_tutari', 0) or 0),
                'KDV YÜZDESI': float(invoice.get('kdv_yuzdesi', 0) or 0)
            }
            excel_data.append(row)
        return excel_data

    def export_invoices_to_excel(self, invoice_data, invoice_type, file_path=None):
        """Fatura listesini Excel'e dönüştür"""
        try:
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{invoice_type}_faturalari_{timestamp}.xlsx"
                file_path = os.path.join(self.excel_folder, filename)
            
            excel_data = self._prepare_invoice_data(invoice_data)
            sheets_data = {f"{invoice_type.title()} Faturalar": {"data": excel_data}}
            
            return self.export_to_excel(file_path, sheets_data)
            
        except Exception as e:
            logging.error(f"Fatura Excel aktarma hatası: {e}")
            print(f"Fatura Excel aktarma hatası: {e}")
            return False

    def export_general_expenses_to_excel(self, expense_data, file_path=None):
        """Genel gider listesini Excel'e dönüştür"""
        try:
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"genel_giderler_{timestamp}.xlsx"
                file_path = os.path.join(self.excel_folder, filename)
            
            excel_data = []
            for expense in expense_data:
                row = {
                    'TARİH': self._format_date(expense.get('tarih', '')),
                    'GİDER TÜRÜ': expense.get('tur', ''),
                    'TUTAR': float(expense.get('miktar', 0) or 0),
                    'AÇIKLAMA': expense.get('aciklama', '')
                }
                excel_data.append(row)
            
            sheets_data = {"Genel Giderler": {"data": excel_data}}
            return self.export_to_excel(file_path, sheets_data)
            
        except Exception as e:
            logging.error(f"Genel gider Excel aktarma hatası: {e}")
            print(f"Genel gider Excel aktarma hatası: {e}")
            return False

    def export_all_data_to_excel(self, backend_instance, file_path=None):
        """Tüm verileri tek Excel dosyasına aktar"""
        try:
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tum_veriler_{timestamp}.xlsx"
                file_path = os.path.join(self.excel_folder, filename)
            
            sheets_data = {}
            
            # Giden faturalar
            outgoing_invoices = backend_instance.handle_invoice_operation('get', 'outgoing')
            if outgoing_invoices:
                outgoing_data = self._prepare_invoice_data(outgoing_invoices)
                sheets_data["Giden Faturalar"] = {"data": outgoing_data}
            
            # Gelen faturalar
            incoming_invoices = backend_instance.handle_invoice_operation('get', 'incoming')
            if incoming_invoices:
                incoming_data = self._prepare_invoice_data(incoming_invoices)
                sheets_data["Gelen Faturalar"] = {"data": incoming_data}
            
            # Genel giderler
            expenses = backend_instance.handle_genel_gider_operation('get')
            if expenses:
                expense_data = []
                for expense in expenses:
                    row = {
                        'TARİH': self._format_date(expense.get('tarih', '')),
                        'GİDER TÜRÜ': expense.get('tur', ''),
                        'TUTAR': float(expense.get('miktar', 0) or 0)
                    }
                    expense_data.append(row)
                sheets_data["Genel Giderler"] = {"data": expense_data}
            
            if not sheets_data:
                print("Aktarılacak veri bulunamadı.")
                return False
            
            return self.export_to_excel(file_path, sheets_data)
            
        except Exception as e:
            logging.error(f"Tüm veri Excel aktarma hatası: {e}")
            print(f"Tüm veri Excel aktarma hatası: {e}")
            return False


# Frontend'den kolayca çağırılabilir yardımcı fonksiyonlar
def export_outgoing_invoices_to_excel(invoice_data, file_path=None):
    """Giden faturaları Excel'e aktar"""
    exporter = InvoiceExcelExporter()
    return exporter.export_invoices_to_excel(invoice_data, 'outgoing', file_path)

def export_incoming_invoices_to_excel(invoice_data, file_path=None):
    """Gelen faturaları Excel'e aktar"""
    exporter = InvoiceExcelExporter()
    return exporter.export_invoices_to_excel(invoice_data, 'incoming', file_path)

def export_general_expenses_to_excel(expense_data, file_path=None):
    """Genel giderleri Excel'e aktar"""
    exporter = InvoiceExcelExporter()
    return exporter.export_general_expenses_to_excel(expense_data, file_path)

def export_monthly_general_expenses_to_excel(expense_data, year=None, file_path=None):
    """Genel giderleri aylık formatta Excel'e aktar - Yatay tablo (Aylar sütunlarda)"""
    try:
        from datetime import datetime
        import calendar
        
        if not year:
            year = datetime.now().year
        
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"genel_giderler_aylik_{year}_{timestamp}.xlsx"
            exporter = InvoiceExcelExporter()
            file_path = os.path.join(exporter.excel_folder, filename)
        
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet(f'{year} Genel Giderler')
        
        # Formatlar
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#6C5DD3',
            'font_color': 'white',
            'border': 1,
            'font_size': 12
        })
        
        money_format = workbook.add_format({
            'num_format': '#,##0.00 "₺"',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11
        })
        
        # Ayları parse et ve topla
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        monthly_totals = {i+1: 0.0 for i in range(12)}
        
        # Expense data'dan aylık toplamları hesapla
        for expense in expense_data:
            tarih = expense.get('tarih', '')
            miktar = float(expense.get('miktar', 0) or 0)
            
            # Tarihi parse et (formatlar: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD)
            try:
                if '.' in tarih:
                    parts = tarih.split('.')
                    month = int(parts[1])
                elif '/' in tarih:
                    parts = tarih.split('/')
                    month = int(parts[1])
                elif '-' in tarih:
                    parts = tarih.split('-')
                    month = int(parts[1])
                else:
                    continue
                    
                if 1 <= month <= 12:
                    monthly_totals[month] += miktar
            except:
                continue
        
        # Başlık satırı (Aylar)
        worksheet.write(0, 0, 'AY', header_format)
        for i, month in enumerate(months):
            worksheet.write(0, i+1, month, header_format)
        
        # Tutar satırı
        worksheet.write(1, 0, 'TUTAR', header_format)
        for i in range(12):
            worksheet.write(1, i+1, monthly_totals[i+1], money_format)
        
        # Sütun genişliklerini ayarla
        worksheet.set_column(0, 0, 12)  # İlk sütun (AY)
        worksheet.set_column(1, 12, 15)  # Ay sütunları
        
        workbook.close()
        print(f"Aylık genel giderler '{os.path.basename(file_path)}' dosyasına aktarıldı.")
        return True
        
    except Exception as e:
        print(f"Aylık genel gider Excel aktarma hatası: {e}")
        return False

def export_all_data_to_excel(backend_instance, file_path=None):
    """Tüm verileri Excel'e aktar"""
    exporter = InvoiceExcelExporter()
    return exporter.export_all_data_to_excel(backend_instance, file_path)

def export_monthly_income_to_excel(year, monthly_results, quarterly_results, summary, file_path):
    """Dönemsel gelir raporunu Excel'e aktar - Uygulama görünümüne benzer formatla"""
    try:
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet(f'{year} Raporu')
        
        # Renkler - Mor tema (açıktan koyuya)
        colors = {
            'mavi': '#E8E5F5',      # Ocak-Mart (açık mor)
            'pembe': '#D4CDED',     # Nisan-Haziran (orta açık mor)
            'sari': '#C0B5E5',      # Temmuz-Eylül (orta mor)
            'yesil': '#AC9EDD'      # Ekim-Aralık (koyu mor)
        }
        
        # Formatlar
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#6C5DD3',
            'font_color': 'white',
            'border': 1,
            'font_size': 11
        })
        
        month_format_base = {
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        }
        
        # Her üç ayın formatı
        month_formats = {}
        for color_name, color_code in colors.items():
            month_formats[color_name] = workbook.add_format({
                **month_format_base,
                'bg_color': color_code
            })
        
        money_format_base = {
            'num_format': '#,##0.00 ₺',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        }
        
        # Para formatları (renkli)
        money_formats = {}
        for color_name, color_code in colors.items():
            money_formats[color_name] = workbook.add_format({
                **money_format_base,
                'bg_color': color_code
            })
        
        # Toplam satırı formatı
        total_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#E7E6E6',
            'border': 1,
            'font_size': 11
        })
        
        total_money_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00 ₺',
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#E7E6E6',
            'border': 1,
            'font_size': 11
        })
        
        # Kâr satırı formatı
        kar_label_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#E7E6E6',
            'border': 1,
            'font_size': 11
        })
        
        kar_value_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00 ₺',
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#E7E6E6',
            'border': 1,
            'font_size': 11
        })
        
        # Sütun genişlikleri
        worksheet.set_column('A:A', 18)  # AYLAR
        worksheet.set_column('B:E', 20)  # Para sütunları
        
        # Başlıklar
        headers = ['AYLAR', 'GELİR (Kesilen)', 'GİDER (Gelen)', 'KDV FARKI', 'ÖDENECEK VERGİ']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Aylar ve veriler
        months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", 
                 "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
        
        color_mapping = {
            0: 'mavi', 1: 'mavi', 2: 'mavi',
            3: 'pembe', 4: 'pembe', 5: 'pembe',
            6: 'sari', 7: 'sari', 8: 'sari',
            9: 'yesil', 10: 'yesil', 11: 'yesil'
        }
        
        quarter_indices_map = {2: 0, 5: 1, 8: 2, 11: 3}
        total_kdv_farki = 0.0
        total_vergi = 0.0
        
        for i, month_name in enumerate(months):
            row = i + 1
            monthly_data = monthly_results[i]
            color = color_mapping[i]
            
            kdv_farki = monthly_data.get('kdv', 0)
            total_kdv_farki += kdv_farki
            
            odenecek_vergi = 0.0
            if i in quarter_indices_map:
                q_index = quarter_indices_map[i]
                if q_index < len(quarterly_results):
                    odenecek_vergi = quarterly_results[q_index].get('odenecek_kv', 0)
                    total_vergi += odenecek_vergi
            
            # Ay adı
            worksheet.write(row, 0, month_name, month_formats[color])
            
            # Para değerleri
            worksheet.write(row, 1, monthly_data.get('kesilen', 0), money_formats[color])
            worksheet.write(row, 2, monthly_data.get('gelen', 0), money_formats[color])
            worksheet.write(row, 3, kdv_farki, money_formats[color])
            worksheet.write(row, 4, odenecek_vergi, money_formats[color])
        
        # Toplam satırı (row 13)
        total_row = 13
        worksheet.write(total_row, 0, 'GENEL TOPLAM', total_format)
        worksheet.write(total_row, 1, summary.get('toplam_gelir', 0), total_money_format)
        worksheet.write(total_row, 2, summary.get('toplam_gider', 0), total_money_format)
        worksheet.write(total_row, 3, total_kdv_farki, total_money_format)
        worksheet.write(total_row, 4, total_vergi, total_money_format)
        
        # Kâr satırı (row 14) - Birleştirilmiş hücreler
        kar_row = 14
        worksheet.merge_range(kar_row, 0, kar_row, 3, 'YILLIK NET KÂR', kar_label_format)
        worksheet.write(kar_row, 4, summary.get('yillik_kar', 0), kar_value_format)
        
        # Satır yükseklikleri
        worksheet.set_row(0, 25)  # Başlık
        for i in range(1, 15):
            worksheet.set_row(i, 22)  # Veri satırları
        
        workbook.close()
        
        logging.info(f"Dönemsel gelir raporu başarıyla oluşturuldu: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Dönemsel gelir Excel aktarma hatası: {e}")
        print(f"Dönemsel gelir Excel aktarma hatası: {e}")
        return False