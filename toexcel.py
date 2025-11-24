# -*- coding: utf-8 -*-
"""
Excel Export Module for Invoice Management System
Bu modül fatura listelerini Excel formatına dönüştürür
"""

import os
import pandas as pd
import logging
from datetime import datetime

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
                'fg_color': '#D7E4BC',
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
                'İRSALİYE NO': invoice.get('irsaliye_no', ''),
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

def export_all_data_to_excel(backend_instance, file_path=None):
    """Tüm verileri Excel'e aktar"""
    exporter = InvoiceExcelExporter()
    return exporter.export_all_data_to_excel(backend_instance, file_path)