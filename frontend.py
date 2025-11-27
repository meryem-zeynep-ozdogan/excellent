# Frontend.py - Flet UI
# Merkezi imports'tan gerekli kütüphaneleri al
from imports import ft, datetime, time, threading, Decimal, os
import sys
import win32event
import win32api
from winerror import ERROR_ALREADY_EXISTS

# Backend modüllerini import et
from backend import Backend
from invoices import InvoiceProcessor
from toexcel import InvoiceExcelExporter, export_monthly_general_expenses_to_excel
from topdf import InvoicePDFExporter, export_monthly_general_expenses_to_pdf

# Tek instance kontrolü
mutex = win32event.CreateMutex(None, False, 'Global\\ExcellentMVPSingleInstance')
last_error = win32api.GetLastError()

if last_error == ERROR_ALREADY_EXISTS:
    # Uygulama zaten çalışıyor
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, "Excellent uygulaması zaten çalışıyor!", "Uyarı", 0x30)
    sys.exit(0)

# Backend instance oluştur
backend_instance = Backend()
invoice_processor = InvoiceProcessor(backend_instance)
excel_exporter = InvoiceExcelExporter()
pdf_exporter = InvoicePDFExporter()

# Backend callback'lerini ayarla (Flet uyumlu)
def on_backend_data_updated():
    """Backend'den veri güncellendiğinde tüm sayfalardaki bileşenleri günceller"""
    try:
        print("🔔 Backend veri güncelleme callback çağrıldı")
        # Tüm kayıtlı callback'leri çağır
        for page_name, callback in state["update_callbacks"].items():
            if callback is not None:
                try:
                    print(f"  → {page_name} callback çalıştırılıyor...")
                    callback()
                except Exception as ex:
                    print(f"  ✗ {page_name} callback hatası: {ex}")
    except Exception as e:
        print(f"❌ on_backend_data_updated hatası: {e}")

def on_backend_status_updated(message, duration):
    """Backend'den status mesajı geldiğinde çağrılır"""
    pass  # İleride UI'da snackbar/toast gösterilebilir

backend_instance.on_data_updated = on_backend_data_updated
backend_instance.on_status_updated = on_backend_status_updated

# --- RENK PALETİ ---
col_primary = "#6C5DD3"   # Mor
col_secondary = "#FF9F43" # Turuncu
col_success = "#4CD964"   # Yeşil
col_danger = "#FF3B30"    # Kırmızı
col_bg = "#F4F5FA"        # Arka Plan
col_white = "#FFFFFF"     # Beyaz
col_text = "#1A1D1F"      # Koyu Metin
col_text_light = "#9AA1B9" # Gri Metin
col_blue_donut = "#2D9CDB"
col_border = "#E6E8EC"
col_table_header_bg = "#5A5278"
col_selected_row = "#E8F5E9" 
col_input_bg = "#FFFFFF"
col_text_secondary = "#6B7280"  # Gri metin (input label)
col_card = "#FFFFFF"  # Beyaz (input arka plan) 

# Şeffaf Renkler
col_primary_50 = "#806C5DD3"
col_secondary_50 = "#80FF9F43"
transparent_white = "#00FFFFFF"
tooltip_bg = "#CC1A1D1F"

# --- GLOBAL DURUM ---
state = {
    "sidebar_expanded": False,
    "current_currency": "TRY",
    "donuts": [],
    "invoice_type": "income",
    "selected_row": None,
    "current_page": "home",
    "invoice_sort_option": "newest",
    "animation_completed": False,
    "excel_export_path": os.path.join(os.getcwd(), "ExcelReports"),
    "pdf_export_path": os.path.join(os.getcwd(), "PDFExports"),
    # Dinamik güncelleme için referanslar
    "update_callbacks": {
        "home_page": None,
        "donemsel_page": None,
        "invoice_page": None,
        "general_expenses": None
    }
}

# --- BACKEND YARDIMCI FONKSİYONLAR ---
def get_exchange_rates():
    """Backend'den güncel döviz kurlarını al"""
    return backend_instance.exchange_rates

def convert_currency(amount, from_currency, to_currency):
    """Para birimi dönüşümü yap"""
    return backend_instance.convert_currency(amount, from_currency, to_currency)

def process_invoice(invoice_data):
    """Fatura verilerini işle ve KDV hesapla"""
    return invoice_processor.process_invoice_data(invoice_data)

def format_currency(amount, currency="TRY", compact=False):
    """Para birimi formatla - compact=True ise K/M formatında göster"""
    if compact:
        # Kompakt format (K/M ile)
        if amount >= 1000000:
            return f"₺ {amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"₺ {amount/1000:.1f}K"
        else:
            return f"₺ {amount:.0f}"
    
    # Normal format
    if currency == "TRY":
        return f"{amount:,.2f} ₺"
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    return f"{amount:,.2f} {currency}"

def get_exchange_rate_display():
    """Kur bilgilerini string olarak döndür"""
    rates = get_exchange_rates()
    usd_rate = rates.get('USD', 0)
    eur_rate = rates.get('EUR', 0)
    
    if usd_rate > 0 and eur_rate > 0:
        usd_tl = 1 / usd_rate
        eur_tl = 1 / eur_rate
        return f"1 USD = {usd_tl:.2f} TL | 1 EUR = {eur_tl:.2f} TL"
    return "Kur bilgisi yükleniyor..."

# --- YARDIMCI BİLEŞENLER ---

class ScaleButton(ft.Container):
    def __init__(self, icon, color, tooltip_text, width=50, height=45, on_click=None):
        super().__init__()
        self.bgcolor = color
        self.border_radius = 8
        self.width = width
        self.height = height
        self.tooltip = tooltip_text
        self.alignment = ft.alignment.center
        self.animate_scale = ft.Animation(200, ft.AnimationCurve.EASE_OUT_BACK)
        self.animate = ft.Animation(200, "easeOut")
        self.ink = False 
        if on_click:
            self.on_click = on_click
        
        hex_code = color.lstrip("#")
        shadow_color = f"#80{hex_code}"
        self.shadow = ft.BoxShadow(blur_radius=5, color=shadow_color, offset=ft.Offset(0, 3))
        self.content = ft.Icon(icon, color=col_white, size=22)
        self.on_hover = self.hover_effect
        self.scale = 1.0 

    def hover_effect(self, e):
        if e.data == "true":
            self.scale = 1.15
            self.shadow.blur_radius = 15
            self.shadow.offset = ft.Offset(0, 6)
        else:
            self.scale = 1.0 
            self.shadow.blur_radius = 5
            self.shadow.offset = ft.Offset(0, 3)
        self.update()

class AestheticButton(ft.Container):
    def __init__(self, text, icon, color, width=130, on_click=None):
        super().__init__()
        self.bgcolor = color
        self.border_radius = 8
        self.padding = ft.padding.symmetric(horizontal=15, vertical=10)
        self.width = width
        self.animate_scale = ft.Animation(150, ft.AnimationCurve.EASE_OUT)
        self.animate = ft.Animation(200, "easeOut") 
        self.ink = False 
        if on_click:
            self.on_click = on_click
        
        hex_code = color.lstrip("#")
        self.shadow = ft.BoxShadow(blur_radius=8, color=f"#4D{hex_code}", offset=ft.Offset(0, 3))
        
        self.content = ft.Row([
            ft.Icon(icon, color=col_white, size=18),
            ft.Text(text, color=col_white, weight="bold", size=12)
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        self.on_hover = self.hover_effect
        self.scale = 1.0
        
    def hover_effect(self, e):
        if e.data == "true":
            self.scale = 1.08
            self.shadow.offset = ft.Offset(0, 5)
            self.shadow.blur_radius = 12
        else:
            self.scale = 1.0
            self.shadow.offset = ft.Offset(0, 3)
            self.shadow.blur_radius = 8
        self.update()

def create_vertical_input(label, hint, width=None, expand=True, is_dropdown=False, dropdown_options=None):
    if is_dropdown:
        input_control = ft.Dropdown(
            options=[ft.dropdown.Option(opt) for opt in dropdown_options] if dropdown_options else [],
            text_size=13, color=col_text, border_color="transparent", bgcolor="transparent",
            content_padding=ft.padding.only(left=10, bottom=5), hint_text=hint,
            hint_style=ft.TextStyle(color="#D0D0D0", size=12),
        )
    else:
        input_control = ft.TextField(
            hint_text=hint, hint_style=ft.TextStyle(color="#D0D0D0", size=12),
            text_size=13, color=col_text, border_color="transparent", bgcolor="transparent",
            content_padding=ft.padding.only(left=10, bottom=12), 
        )

    return ft.Column([
        ft.Text(label, size=12, color=col_text_light, weight="bold"),
        ft.Container(
            content=input_control, bgcolor=col_white, border=ft.border.all(1, col_border),
            border_radius=8, height=38, width=width
        )
    ], spacing=3, expand=expand)

# --- FATURA VERİSİ ---
# Frontend sample invoice data removed to avoid embedded backend/test scaffolding.
# Integrate a backend data source and supply rows dynamically when ready.

def get_sorted_invoices(sort_option):
    """Placeholder: returns empty list until backend integration is provided."""
    return []

def create_invoice_table_content(sort_option="newest", invoice_type="income", on_select_changed=None, invoice_list=None):
    """Backend'den fatura verilerini çekerek DataTable oluşturur."""
    def header(t): return ft.DataColumn(ft.Text(t, weight="bold", color=col_white, size=12))
    
    # Backend'den faturaları çek (eğer liste verilmediyse)
    rows = []
    invoices = invoice_list  # Liste cache'i için
    
    try:
        if invoices is None:
            # invoice_type'a göre doğru veritabanını belirle
            db_type = 'outgoing' if invoice_type == 'income' else 'incoming'
            
            # Sıralama seçeneğine göre order_by parametresi
            if sort_option == "newest":
                order_by = "id DESC"
            elif sort_option == "date_desc":
                order_by = "tarih DESC"
            elif sort_option == "date_asc":
                order_by = "tarih ASC"
            else:
                order_by = "id DESC"
            
            # Backend'den faturaları al
            invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type=db_type,
                limit=100,
                offset=0,
                order_by=order_by
            )
        
        # DataTable satırlarını oluştur
        if invoices:
            for inv in invoices:
                def cell(text, color=col_text): 
                    return ft.DataCell(ft.Text(str(text), size=12, color=color))
                
                # Checkbox hücresi - manuel seçim için
                checkbox = ft.Checkbox(value=False, on_change=on_select_changed if on_select_changed else None)
                checkbox_cell = ft.DataCell(checkbox)
                
                # Kur bilgisini al
                usd_rate = inv.get('usd_rate', 0)
                eur_rate = inv.get('eur_rate', 0)
                
                # Tutar görüntüleme - kur bilgisi ile
                tutar_usd = float(inv.get('toplam_tutar_usd', 0))
                tutar_eur = float(inv.get('toplam_tutar_eur', 0))
                
                usd_text = f"{tutar_usd:,.2f}" if usd_rate == 0 else f"{tutar_usd:,.2f} ({usd_rate:.2f} TL)"
                eur_text = f"{tutar_eur:,.2f}" if eur_rate == 0 else f"{tutar_eur:,.2f} ({eur_rate:.2f} TL)"
                
                # Her satıra invoice verilerini data olarak ekle
                row = ft.DataRow(
                    data=inv,  # Tüm invoice verisini data olarak sakla
                    cells=[
                        checkbox_cell,  # İlk hücre checkbox
                        cell(inv.get('fatura_no', '')),
                        cell(inv.get('irsaliye_no', '')),
                        cell(inv.get('tarih', '')),
                        cell(inv.get('firma', '')),
                        cell(inv.get('malzeme', '')),
                        cell(inv.get('miktar', '')),
                        cell(f"{float(inv.get('toplam_tutar_tl', 0)):,.2f}"),
                        cell(usd_text),
                        cell(eur_text),
                        cell(f"%{float(inv.get('kdv_yuzdesi', 0)):.0f}")
                    ]
                )
                rows.append(row)
    except Exception as e:
        pass

    return ft.DataTable(
        columns=[header("SEÇ"), header("FATURA NO"), header("İRSALİYE NO"), header("TARİH"), header("FİRMA"), header("MALZEME"), header("MİKTAR"), ft.DataColumn(ft.Text("TUTAR (TL)", weight="bold", color=col_white, size=12), numeric=True), ft.DataColumn(ft.Text("TUTAR (USD)", weight="bold", color=col_white, size=12), numeric=True), ft.DataColumn(ft.Text("TUTAR (EUR)", weight="bold", color=col_white, size=12), numeric=True), header("KDV")],
        rows=rows, heading_row_color=col_table_header_bg, heading_row_height=45, data_row_max_height=40,
        vertical_lines=ft.border.BorderSide(0, "transparent"), horizontal_lines=ft.border.BorderSide(1, "#F0F0F0"),
        column_spacing=15, width=float("inf")
    )

def create_donemsel_table(year=None, tax_fields=None, on_tax_change=None):
    """Dönemsel gelir/gider tablosu - Gerçek verilerle dolu"""
    if year is None:
        year = datetime.now().year
    
    months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
    quarter_colors = [col_danger, col_success, col_secondary, col_blue_donut]
    def header(t): return ft.DataColumn(ft.Text(t, weight="bold", color=col_white, size=12))
    def cell(t): return ft.DataCell(ft.Text(t, color="#333333", size=12))
    
    # Backend'den verileri çek
    try:
        income_invoices = backend_instance.handle_invoice_operation('get', 'outgoing') or []
        expense_invoices = backend_instance.handle_invoice_operation('get', 'incoming') or []
        
        # Genel giderleri çek
        general_expenses = backend_instance.db.get_yearly_expenses(year) or {}
        
        # Kurumlar vergisi tutarlarını çek (aylık)
        corporate_tax_data = backend_instance.db.get_corporate_tax(year) or {}
        
        # Aylık toplamları hesapla
        monthly_income = [0.0] * 12
        monthly_expense = [0.0] * 12
        monthly_general = [0.0] * 12
        monthly_corporate_tax = [0.0] * 12  # Aylık kurumlar vergisi tutarları
        monthly_income_kdv = [0.0] * 12  # Gelir faturalarındaki KDV
        monthly_expense_kdv = [0.0] * 12  # Gider faturalarındaki KDV
        
        # Gelir faturalarını işle
        for invoice in income_invoices:
            tarih = invoice.get('tarih', '')
            if not tarih: continue
            
            parts = tarih.split('.')
            if len(parts) != 3: continue
            
            try:
                month = int(parts[1])
                invoice_year = int(parts[2])
                
                if invoice_year == year:
                    amount_tl = float(invoice.get('toplam_tutar_tl', 0))
                    kdv_tl = float(invoice.get('kdv_tutari', 0))
                    monthly_income[month-1] += amount_tl
                    monthly_income_kdv[month-1] += kdv_tl
            except (ValueError, IndexError):
                continue
        
        # Gider faturalarını işle
        for invoice in expense_invoices:
            tarih = invoice.get('tarih', '')
            if not tarih: continue
            
            parts = tarih.split('.')
            if len(parts) != 3: continue
            
            try:
                month = int(parts[1])
                invoice_year = int(parts[2])
                
                if invoice_year == year:
                    amount_tl = float(invoice.get('toplam_tutar_tl', 0))
                    kdv_tl = float(invoice.get('kdv_tutari', 0))
                    monthly_expense[month-1] += amount_tl
                    monthly_expense_kdv[month-1] += kdv_tl
            except (ValueError, IndexError):
                continue
        
        # Genel giderleri ay ay ekle
        month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
        for month_idx in range(12):
            month_key = month_keys[month_idx]
            if month_key in general_expenses:
                monthly_general[month_idx] = float(general_expenses[month_key] or 0)
            if month_key in corporate_tax_data:
                monthly_corporate_tax[month_idx] = float(corporate_tax_data[month_key] or 0)
        
        # Tabloyu oluştur
        rows = []
        total_income = 0.0
        total_expense = 0.0
        total_general = 0.0
        total_kdv_diff = 0.0
        total_kurumlar_vergisi = 0.0
        
        for i, m in enumerate(months):
            quarter_index = i // 3 
            current_color = quarter_colors[quarter_index]
            
            income = monthly_income[i]
            expense = monthly_expense[i]
            general = monthly_general[i]
            income_kdv = monthly_income_kdv[i]
            expense_kdv = monthly_expense_kdv[i]
            
            # Kurumlar vergisi yüzdesini al
            tax_percentage = monthly_corporate_tax[i]  # Yüzde olarak girilen değer
            
            # Kurumlar vergisi = (Gelir fatura + Gider fatura) * Yüzde / 100
            # Genel giderler dahil DEĞİL, sadece faturalar
            taxable_base = income + expense
            kurumlar_vergisi = (taxable_base * tax_percentage / 100) if tax_percentage > 0 else 0
            
            # Toplam gider = Faturalı gider + Genel gider
            total_month_expense = expense + general
            
            # KDV farkı = Mutlak değer (her zaman pozitif)
            kdv_diff = abs(income_kdv - expense_kdv)
            
            # Ödenecek vergi = KDV farkı + Kurumlar Vergisi
            odenecek_vergi = kdv_diff + kurumlar_vergisi
            
            # Toplamları güncelle
            total_income += income
            total_expense += total_month_expense
            total_general += general
            total_kdv_diff += kdv_diff
            total_kurumlar_vergisi += kurumlar_vergisi
            
            month_cell = ft.DataCell(ft.Container(
                content=ft.Text(m, color=current_color, weight="bold", size=12), 
                padding=ft.padding.only(left=8), 
                border=ft.border.only(left=ft.border.BorderSide(3, current_color)), 
                alignment=ft.alignment.center_left
            ))
            
            # Gider hücresinde toplam göster (fatura + genel)
            expense_text = f"{total_month_expense:,.2f} TL"
            
            # Kurumlar vergisi hücresi - TextField ile düzenlenebilir
            if tax_fields and i < len(tax_fields):
                tax_field = tax_fields[i]
                kurumlar_cell = ft.DataCell(ft.Container(
                    content=tax_field,
                    padding=2,
                    alignment=ft.alignment.center
                ))
            else:
                kurumlar_text = f"{kurumlar_vergisi:,.2f} TL" if kurumlar_vergisi > 0 else "-"
                kurumlar_cell = cell(kurumlar_text)
            
            rows.append(ft.DataRow(cells=[
                month_cell, 
                cell(f"{income:,.2f} TL"),
                cell(expense_text),
                cell(f"{kdv_diff:,.2f} TL"),
                kurumlar_cell,
                cell(f"{odenecek_vergi:,.2f} TL")
            ]))
        
        table = ft.DataTable(
            columns=[header("DÖNEM"), header("GELİR (Kesilen)"), header("GİDER (Gelen + Genel)"), header("KDV FARKI"), header("KURUMLAR VERGİSİ"), header("ÖDENECEK VERGİ")], 
            rows=rows, 
            heading_row_color=col_table_header_bg, 
            heading_row_height=45, 
            data_row_max_height=40, 
            vertical_lines=ft.border.BorderSide(1, "#E0E0E0"), 
            horizontal_lines=ft.border.BorderSide(1, "#E0E0E0"), 
            column_spacing=10, 
            width=float("inf")
        )
        
        # Toplam kurumlar vergisi ve ödenecek vergi hesapla
        total_odenecek_vergi = total_kdv_diff + total_kurumlar_vergisi
        
        total_card = ft.Container(
            margin=ft.margin.only(top=10), 
            padding=20, 
            bgcolor="#F8F7FC", 
            border=ft.border.all(1, "#E0DBF5"), 
            border_radius=12, 
            shadow=ft.BoxShadow(blur_radius=5, color="#106C5DD3", offset=ft.Offset(0, 3)),
            content=ft.Row([
                ft.Row([ft.Icon("functions", color=col_primary), ft.Text("GENEL TOPLAM", color=col_primary, weight="bold", size=16)], spacing=10),
                ft.Row([
                    ft.Column([ft.Text("Gelir", color="#9AA1B9", size=11), ft.Text(f"{total_income:,.2f} TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("Gider (Fatura + Genel)", color="#9AA1B9", size=11), ft.Text(f"{total_expense:,.2f} TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("KDV Farkı", color="#9AA1B9", size=11), ft.Text(f"{total_kdv_diff:,.2f} TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("Kurumlar Vergisi", color="#9AA1B9", size=11), ft.Text(f"{total_kurumlar_vergisi:,.2f} TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("Ödenecek Vergi", color=col_danger, size=11, weight="bold"), ft.Text(f"{total_odenecek_vergi:,.2f} TL", color=col_text, weight="bold", size=16)], spacing=2),
                ], spacing=20)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        
        return ft.Column([table, total_card])
        
    except Exception as e:
        pass
        
        # Hata durumunda boş tablo döndür
        rows = []
        for i, m in enumerate(months):
            quarter_index = i // 3 
            current_color = quarter_colors[quarter_index]
            month_cell = ft.DataCell(ft.Container(content=ft.Text(m, color=current_color, weight="bold", size=12), padding=ft.padding.only(left=8), border=ft.border.only(left=ft.border.BorderSide(3, current_color)), alignment=ft.alignment.center_left))
            rows.append(ft.DataRow(cells=[month_cell, cell("0.00 TL"), cell("0.00 TL"), cell("0.00 TL"), cell("0.00 TL")]))
        
        table = ft.DataTable(columns=[header("DÖNEM"), header("GELİR (Kesilen)"), header("GİDER (Gelen)"), header("KDV FARKI"), header("ÖDENECEK VERGİ")], rows=rows, heading_row_color=col_table_header_bg, heading_row_height=45, data_row_max_height=40, vertical_lines=ft.border.BorderSide(1, "#E0E0E0"), horizontal_lines=ft.border.BorderSide(1, "#E0E0E0"), column_spacing=10, width=float("inf"))
        
        total_card = ft.Container(
            margin=ft.margin.only(top=10), padding=20, bgcolor="#F8F7FC", border=ft.border.all(1, "#E0DBF5"), border_radius=12, shadow=ft.BoxShadow(blur_radius=5, color="#106C5DD3", offset=ft.Offset(0, 3)),
            content=ft.Row([
                ft.Row([ft.Icon("functions", color=col_primary), ft.Text("GENEL TOPLAM", color=col_primary, weight="bold", size=16)], spacing=10),
                ft.Row([
                    ft.Column([ft.Text("Gelir", color="#9AA1B9", size=11), ft.Text("0.00 TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("Gider", color="#9AA1B9", size=11), ft.Text("0.00 TL", color=col_text, weight="bold")], spacing=2),
                    ft.Container(width=1, height=30, bgcolor="#D0D0D0"),
                    ft.Column([ft.Text("Ödenecek Vergi", color=col_danger, size=11, weight="bold"), ft.Text("0.00 TL", color=col_text, weight="bold", size=16)], spacing=2),
                ], spacing=30)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        return ft.Column([table, total_card])

def create_grid_expenses(page):
    months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
    
    # Yıl seçenekleri
    current_year = datetime.now().year
    year_options = [ft.dropdown.Option(str(y)) for y in range(current_year - 2, current_year + 2)]
    
    year_dropdown = ft.Dropdown(
        options=year_options,
        value=str(current_year),
        text_size=12,
        content_padding=10,
        width=95,
        bgcolor=col_white,
        border_color=col_border,
        border_radius=8
    )
    
    # TextField'ları sakla
    expense_fields = {}
    expense_cards = []
    
    for i, m in enumerate(months):
        text_field = ft.TextField(
            value="0", 
            text_size=14, 
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD), 
            color=col_text, 
            text_align=ft.TextAlign.CENTER, 
            border_color="#E0E0E0", 
            focused_border_color=col_primary, 
            height=35, 
            content_padding=5, 
            bgcolor="#FAFAFA", 
            prefix_text="₺ "
        )
        expense_fields[month_keys[i]] = text_field
        
        card = ft.Container(
            bgcolor=col_white, 
            border_radius=12, 
            padding=10, 
            width=140, 
            height=85, 
            shadow=ft.BoxShadow(blur_radius=5, color="#08000000", offset=ft.Offset(0,3)), 
            border=ft.border.all(1, "#F0F0F0"), 
            content=ft.Column([
                ft.Container(content=ft.Text(m, size=13, weight="bold", color=col_primary), alignment=ft.alignment.center), 
                ft.Divider(height=5, color="transparent"), 
                text_field
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
        )
        expense_cards.append(card)
    
    # Seçili yılın verilerini yükle
    def load_year_data(year=None):
        if year is None:
            year = int(year_dropdown.value)
        yearly_data = backend_instance.db.get_yearly_expenses(year)
        
        if yearly_data:
            for month_key in month_keys:
                amount = yearly_data.get(month_key, 0)
                expense_fields[month_key].value = str(amount) if amount else "0"
        else:
            # Veri yoksa sıfırla
            for month_key in month_keys:
                expense_fields[month_key].value = "0"
        page.update()
    
    # Yıl değiştiğinde verileri yükle
    def on_year_change(e):
        load_year_data(int(e.control.value))
    
    year_dropdown.on_change = on_year_change
    
    # Kaydet butonu fonksiyonu
    def save_expenses(e):
        """Genel giderleri database'e kaydet"""
        try:
            selected_year = int(year_dropdown.value)
            monthly_data = {}
            
            # Tüm ayların değerlerini topla
            for month_key in month_keys:
                value = expense_fields[month_key].value
                try:
                    monthly_data[month_key] = float(value) if value else 0
                except ValueError:
                    monthly_data[month_key] = 0
            
            # Database'e kaydet
            result = backend_instance.db.add_or_update_yearly_expenses(selected_year, monthly_data)
            
            if result:
                # Veri güncelleme callback'ini çağır
                if backend_instance.on_data_updated:
                    backend_instance.on_data_updated()
                
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {selected_year} yılı genel giderleri kaydedildi!", color=col_white), bgcolor=col_success)
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ Kaydetme işlemi başarısız!", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()
                
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ Hata: {str(ex)}", color=col_white), bgcolor=col_danger)
            page.snack_bar.open = True
            page.update()
    
    def export_general_expenses_excel(e):
        """Genel giderleri Excel'e aktar - Aylık format"""
        try:
            expenses = backend_instance.handle_genel_gider_operation('get', limit=1000)
            
            if not expenses:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ Dışa aktarılacak genel gider bulunamadı!", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()
                return
            
            # Ayarlardan klasör yolunu al
            export_folder = state.get("excel_export_path", os.path.join(os.getcwd(), "ExcelReports"))
            os.makedirs(export_folder, exist_ok=True)
            
            # Dosya yolu oluştur
            selected_year = int(year_dropdown.value)
            timestamp = datetime.now().strftime("%d-%m-%Y")
            file_path = os.path.join(export_folder, f"GenelGiderler_{selected_year}_{timestamp}.xlsx")
            
            # Aylık formatta Excel'e aktar
            success = export_monthly_general_expenses_to_excel(expenses, year=selected_year, file_path=file_path)
            
            if success:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {len(expenses)} genel gider Excel'e aktarıldı!\n{file_path}", color=col_white), bgcolor=col_success)
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ Excel aktarımı başarısız!", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()
                
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ Excel hatası: {str(ex)}", color=col_white), bgcolor=col_danger)
            page.snack_bar.open = True
            page.update()
    
    def export_general_expenses_pdf(e):
        """Genel giderleri PDF'e aktar - Aylık format"""
        try:
            expenses = backend_instance.handle_genel_gider_operation('get', limit=1000)
            
            if not expenses:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ Dışa aktarılacak genel gider bulunamadı!", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()
                return
            
            # Ayarlardan klasör yolunu al
            export_folder = state.get("pdf_export_path", os.path.join(os.getcwd(), "PDFExports"))
            os.makedirs(export_folder, exist_ok=True)
            
            # Dosya yolu oluştur
            selected_year = int(year_dropdown.value)
            timestamp = datetime.now().strftime("%d-%m-%Y")
            file_path = os.path.join(export_folder, f"GenelGiderler_{selected_year}_{timestamp}.pdf")
            
            # Aylık formatta PDF'e aktar
            success = export_monthly_general_expenses_to_pdf(expenses, year=selected_year, file_path=file_path)
            
            if success:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {len(expenses)} genel gider PDF'e aktarıldı!\n{file_path}", color=col_white), bgcolor=col_success)
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ PDF aktarımı başarısız!", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()
                
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ PDF hatası: {str(ex)}", color=col_white), bgcolor=col_danger)
            page.snack_bar.open = True
            page.update()
    
    # Sayfa yüklendiğinde mevcut verileri yükle
    load_year_data()
    
    # Dinamik güncelleme için callback oluştur
    def refresh_general_expenses():
        """Genel giderleri yeniden yükle"""
        try:
            load_year_data()
        except:
            pass
    
    state["update_callbacks"]["general_expenses"] = refresh_general_expenses
    
    # Butonları event handler'larla oluştur
    btn_save = ScaleButton("save", "#4CD964", "Kaydet", width=40, height=40)
    btn_save.on_click = save_expenses
    
    btn_excel = ScaleButton("table_view", "#217346", "Excel İndir", width=40, height=40)
    btn_excel.on_click = export_general_expenses_excel
    
    btn_pdf = ScaleButton("picture_as_pdf", "#D32F2F", "PDF İndir", width=40, height=40)
    btn_pdf.on_click = export_general_expenses_pdf
    
    expense_buttons = ft.Container(padding=ft.padding.only(right=40), content=ft.Row([ft.Container(height=38, content=year_dropdown), btn_save, btn_excel, btn_pdf, ScaleButton("print", "#607D8B", "Yazdır", width=40, height=40)], spacing=5))
    
    return ft.Container(padding=ft.padding.only(top=15), content=ft.Column([ft.Row([ft.Row([ft.Icon("calendar_month", color=col_secondary, size=20), ft.Text("Yıllık Genel Giderler", size=16, weight="bold", color=col_text)], spacing=8), expense_buttons], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), ft.Row(controls=expense_cards, wrap=True, spacing=15, run_spacing=15, alignment=ft.MainAxisAlignment.CENTER)]))

class AnimatedDonut(ft.Stack):
    def __init__(self, value, total, color, text_value):
        super().__init__()
        self.width = 110
        self.height = 110
        self.alignment = ft.alignment.center
        hex_code = color.lstrip("#")
        shadow_color = f"#66{hex_code}"
        remainder_color = f"#1A{hex_code}"
        self.chart_rotate = ft.Rotate(-3.14, alignment=ft.alignment.center)
        self.chart = ft.PieChart(
            sections=[
                ft.PieChartSection(value=value, color=color, radius=14, title=""),
                ft.PieChartSection(value=total - value, color=remainder_color, radius=14, title=""),
            ],
            center_space_radius=38, sections_space=0, start_degree_offset=-90
        )
        self.chart_container = ft.Container(
            content=self.chart, width=110, height=110, bgcolor=col_white, shape=ft.BoxShape.CIRCLE,
            shadow=ft.BoxShadow(blur_radius=20, spread_radius=2, color=shadow_color, offset=ft.Offset(0, 8)),
            rotate=self.chart_rotate, opacity=0, animate_opacity=ft.Animation(800, "easeIn"), animate_rotation=ft.Animation(1500, "easeOutBack")
        )
        self.text_container = ft.Container(content=ft.Text(text_value, size=15, weight="bold", color=col_text, text_align="center"), alignment=ft.alignment.center, rotate=ft.Rotate(0, alignment=ft.alignment.center))
        self.controls = [self.chart_container, self.text_container]
        state["donuts"].append(self)

    def start_animation(self):
        try:
            # Sayfa yüklü değilse veya obje sayfada değilse çalışma
            if not self.chart_container.page: return

            if state["animation_completed"]:
                self.chart_container.opacity = 1
                self.chart_container.rotate.angle = 0
                self.chart_container.animate_opacity = None 
                self.chart_container.animate_rotation = None
                self.chart_container.update()
            else:
                self.chart_container.rotate.angle = 0
                self.chart_container.opacity = 1
                self.chart_container.update()
        except: pass
    
    def update_value(self, new_value, new_total, new_text):
        """Donut değerlerini günceller"""
        try:
            if not self.chart_container.page: return
            
            # Chart sections'ı güncelle
            self.chart.sections[0].value = new_value
            self.chart.sections[1].value = max(0, new_total - new_value)
            
            # Text'i güncelle
            self.text_container.content.value = new_text
            
            # Güncellemeyi uygula
            self.chart_container.update()
            self.text_container.update()
        except Exception as e:
            print(f"Donut update hatası: {e}")

class DonutStatCard(ft.Container):
    def __init__(self, title, icon, color, trend_text, donut_val, donut_total, display_text):
        super().__init__()
        self.bgcolor = col_white
        self.border_radius = 24
        self.padding = ft.padding.all(20)
        self.expand = 1
        self.shadow = ft.BoxShadow(blur_radius=15, color="#08000000", offset=ft.Offset(0, 5))
        self.donut = AnimatedDonut(value=donut_val, total=donut_total, color=color, text_value=display_text)
        self.content = ft.Row([
            ft.Column([
                ft.Container(content=ft.Icon(icon, color=col_white, size=24), bgcolor=color, border_radius=14, width=48, height=48, alignment=ft.alignment.center, shadow=ft.BoxShadow(blur_radius=10, color=f"#4D{color.lstrip('#')}", offset=ft.Offset(0,4))),
                ft.Container(height=5),
                ft.Text(title, size=14, color=col_text_light, weight="w600"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
            ft.Container(content=self.donut, alignment=ft.alignment.center_right)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

class TransactionRow(ft.Container):
    def __init__(self, title, date, amount, is_income=True, is_updated=False, invoice_date=None):
        super().__init__()
        self.padding = ft.padding.symmetric(vertical=10)
        self.border = ft.border.only(bottom=ft.border.BorderSide(1, "#F0F0F0"))
        color = col_success if is_income else col_danger
        icon = "arrow_upward" if is_income else "arrow_downward"
        sign = "+" if is_income else "-"
        
        # Güncellenmiş faturalar için özel gösterge
        status_indicator = None
        if is_updated:
            status_indicator = ft.Container(
                width=8,
                height=8,
                bgcolor="#FF9F43",  # Turuncu nokta
                border_radius=4,
                tooltip="Güncellenmiş fatura"
            )
        
        # İkon container'ı
        icon_container = ft.Container(
            width=40, 
            height=40, 
            bgcolor=f"{color}20", 
            border_radius=10, 
            content=ft.Icon(icon, color=color, size=20), 
            alignment=ft.alignment.center
        )
        
        # Güncellenmiş ise border ekle
        if is_updated:
            icon_container.border = ft.border.all(2, "#FF9F43")
        
        # Row içeriği
        row_controls = [icon_container]
        
        # Tarih formatı: işlem tarihi (Fat.Tar. fatura_tarihi)
        date_text = date
        if invoice_date and invoice_date != date:
            date_text = f"{date} (Fat.Tar. {invoice_date})"
        
        # Tarih için Row - normal kısım ve parantez kısmı farklı fontlarla
        if invoice_date and invoice_date != date:
            date_row = ft.Row([
                ft.Text(date, size=12, color=col_text_light),
                ft.Text(f" (Fat.Tar. {invoice_date})", size=10, color=col_text_light, italic=True)
            ], spacing=0)
        else:
            date_row = ft.Text(date, size=12, color=col_text_light)
        
        # Başlık ve tarih - güncellenmiş ise yanında turuncu nokta
        if is_updated:
            title_row = ft.Row([
                ft.Text(title, weight="bold", size=14, color=col_text),
                status_indicator
            ], spacing=5)
            row_controls.append(
                ft.Column([title_row, date_row], spacing=2, expand=True)
            )
        else:
            row_controls.append(
                ft.Column([ft.Text(title, weight="bold", size=14, color=col_text), date_row], spacing=2, expand=True)
            )
        
        row_controls.append(ft.Text(f"{sign} {amount}", weight="bold", size=15, color=color))
        
        self.content = ft.Row(row_controls, spacing=12)

def currency_button(text, currency_code, current_selection, on_click_handler):
    is_selected = (currency_code == current_selection)
    return ft.Container(
        content=ft.Text(text, color=col_primary if is_selected else col_text_light, weight="bold" if is_selected else "normal"),
        bgcolor=col_white if is_selected else "transparent",
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=10,
        shadow=ft.BoxShadow(blur_radius=5, color="#10000000", offset=ft.Offset(0,2)) if is_selected else None,
        on_click=lambda e: on_click_handler(currency_code),
        animate=ft.Animation(200, "easeOut")
    )

# --- ANA UYGULAMA ---
def main(page: ft.Page):
    page.title = "Excellent MVP Dashboard"
    page.padding = 0
    page.bgcolor = col_bg
    page.window_width = 1400 
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Grafik Verileri için Backend'den Gerçek Veri Çekme Fonksiyonu ---
    def get_all_available_years():
        """Veritabanındaki tüm yılları döndürür (gelir, gider ve genel gider tablolarından) - sadece veri olan yıllar"""
        years = set()
        try:
            # Gelir faturalarından yılları topla
            income_invoices = backend_instance.handle_invoice_operation('get', 'outgoing') or []
            for invoice in income_invoices:
                tarih = invoice.get('tarih', '')
                if tarih:
                    parts = tarih.split('.')
                    if len(parts) == 3:
                        try:
                            years.add(int(parts[2]))
                        except ValueError:
                            pass
            
            # Gider faturalarından yılları topla
            expense_invoices = backend_instance.handle_invoice_operation('get', 'incoming') or []
            for invoice in expense_invoices:
                tarih = invoice.get('tarih', '')
                if tarih:
                    parts = tarih.split('.')
                    if len(parts) == 3:
                        try:
                            years.add(int(parts[2]))
                        except ValueError:
                            pass
            
            # Genel giderlerden yılları topla (sadece en az bir aya veri girilmişse)
            try:
                all_general_expenses = backend_instance.db.get_all_yearly_expenses()
                month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 
                             'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
                
                for expense_data in all_general_expenses:
                    if expense_data and 'yil' in expense_data:
                        # En az bir ayda veri var mı kontrol et
                        has_data = False
                        for month in month_keys:
                            if expense_data.get(month) and float(expense_data.get(month, 0) or 0) > 0:
                                has_data = True
                                break
                        
                        if has_data:
                            try:
                                years.add(int(expense_data['yil']))
                            except (ValueError, TypeError):
                                pass
            except:
                pass
            
        except Exception as e:
            print(f"Yıl toplama hatası: {e}")
        
        # Eğer hiç yıl bulunamadıysa mevcut yılı ekle
        if not years:
            years.add(datetime.now().year)
        
        return sorted(years, reverse=True)
    
    def get_line_chart_data():
        """Backend'den aylık gelir/gider verilerini çeker ve line chart formatında döndürür"""
        try:
            # Backend'den tüm faturaları al (operation='get')
            income_invoices = backend_instance.handle_invoice_operation('get', 'outgoing') or []
            expense_invoices = backend_instance.handle_invoice_operation('get', 'incoming') or []
            
            # Yıllara göre grupla
            yearly_data = {}
            
            # Gelir faturalarını işle
            for idx, invoice in enumerate(income_invoices):
                tarih = invoice.get('tarih', '')
                if not tarih: 
                    continue
                
                parts = tarih.split('.')
                if len(parts) != 3: 
                    continue
                
                try:
                    month = int(parts[1])
                    year = int(parts[2])
                    amount_tl = float(invoice.get('toplam_tutar_tl', 0)) / 1000  # K (bin) cinsine çevir
                    
                    if year not in yearly_data:
                        yearly_data[year] = {"gelir": [0]*12, "gider": [0]*12}
                    
                    yearly_data[year]["gelir"][month-1] += amount_tl
                except (ValueError, IndexError) as ex:
                    continue
            
            # Gider faturalarını işle
            for invoice in expense_invoices:
                tarih = invoice.get('tarih', '')
                if not tarih: continue
                
                parts = tarih.split('.')
                if len(parts) != 3: continue
                
                try:
                    month = int(parts[1])
                    year = int(parts[2])
                    amount_tl = float(invoice.get('toplam_tutar_tl', 0)) / 1000  # K (bin) cinsine çevir
                    
                    if year not in yearly_data:
                        yearly_data[year] = {"gelir": [0]*12, "gider": [0]*12}
                    
                    yearly_data[year]["gider"][month-1] += amount_tl
                except (ValueError, IndexError):
                    continue
            
            # Genel giderleri ekle - her yıl için
            month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
            for year in list(yearly_data.keys()):
                general_expenses = backend_instance.db.get_yearly_expenses(year)
                if general_expenses:
                    for month_idx, month_key in enumerate(month_keys):
                        if month_key in general_expenses:
                            general_amount = float(general_expenses[month_key] or 0) / 1000  # K cinsine çevir
                            yearly_data[year]["gider"][month_idx] += general_amount
            
            # Eğer veri yoksa boş dict döndür
            if not yearly_data:
                return {}
            
            return yearly_data
        except Exception as e:
            return {}
    
    # --- Grafik Verileri ve Tanımı ---
    full_data = get_line_chart_data()  # Backend'den gerçek veri
    
    # Max değeri hesapla (dinamik Y ekseni için)
    def calculate_max_y(year=None):
        """Grafikteki maksimum değeri bulur ve uygun Y ekseni limiti döndürür. Eğer yıl belirtilirse sadece o yılın verilerini kullanır."""
        if not full_data:
            return 150  # Varsayılan
        
        max_value = 0
        
        if year and year in full_data:
            # Sadece belirtilen yılın verileri
            year_data = full_data[year]
            max_value = max(max(year_data.get("gelir", [0])), max(year_data.get("gider", [0])))
        else:
            # Tüm yılların verileri
            for year_data in full_data.values():
                max_value = max(max_value, max(year_data.get("gelir", [0])), max(year_data.get("gider", [0])))
        
        # Yuvarla (50'lik artışlarla)
        if max_value == 0:
            return 150
        
        # Daha iyi görünüm için biraz boşluk bırak
        return ((int(max_value) // 50) + 2) * 50
    
    chart_max_y = calculate_max_y()
    
    # Y ekseni label'larını dinamik oluştur
    def get_y_axis_labels(max_y):
        """Y ekseni için dinamik label'lar oluşturur"""
        step = max_y // 3
        return [
            ft.ChartAxisLabel(value=0, label=ft.Text("0", size=10, color=col_text_light)),
            ft.ChartAxisLabel(value=step, label=ft.Text(f"{step}K", size=10, color=col_text_light)),
            ft.ChartAxisLabel(value=step*2, label=ft.Text(f"{step*2}K", size=10, color=col_text_light)),
            ft.ChartAxisLabel(value=max_y, label=ft.Text(f"{max_y}K", size=10, color=col_text_light))
        ]
    
    line_chart = ft.LineChart(data_series=[ft.LineChartData(data_points=[], stroke_width=5, color=col_primary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_primary_50, transparent_white])), ft.LineChartData(data_points=[], stroke_width=5, color=col_secondary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_secondary_50, transparent_white]))], border=ft.border.all(0, "transparent"), bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(m, size=12, color=col_text_light)) for i, m in enumerate(["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"])], labels_size=30), left_axis=ft.ChartAxis(labels=get_y_axis_labels(chart_max_y), labels_size=40), tooltip_bgcolor=tooltip_bg, min_y=0, max_y=chart_max_y, min_x=0, max_x=11, expand=True, horizontal_grid_lines=ft.ChartGridLines(color="#F0F0F0", width=1, dash_pattern=[5, 5]), animate=None)

    def draw_snake_chart(year):
        """Yılan grafiğini çizen fonksiyon - yıl parametresi int veya str olabilir"""
        # Yıl değerini int'e çevir
        try:
            year = int(year)
        except (ValueError, TypeError):
            return
            
        if state["current_page"] != "home": return
        
        # SAYFADAN KONTROL: Eğer bileşen sayfada yoksa işlem yapma
        if not line_chart.page: return
        
        # Veri kontrolü - Eğer seçili yıl veya veri yoksa boş grafik göster
        if not full_data or year not in full_data:
            line_chart.data_series[0].data_points = []
            line_chart.data_series[1].data_points = []
            try: line_chart.update()
            except: pass
            return
        
        # Seçili yıla göre Y eksenini yeniden hesapla ve güncelle
        year_max_y = calculate_max_y(year)
        line_chart.max_y = year_max_y
        line_chart.left_axis.labels = get_y_axis_labels(year_max_y)

        # Animasyon bittiyse direkt çiz
        if state["animation_completed"]:
            line_chart.data_series[0].data_points = [ft.LineChartDataPoint(i, full_data[year]["gelir"][i], tooltip=f"{full_data[year]['gelir'][i]:.1f}K") for i in range(12)]
            line_chart.data_series[1].data_points = [ft.LineChartDataPoint(i, full_data[year]["gider"][i], tooltip=f"{full_data[year]['gider'][i]:.1f}K") for i in range(12)]
            try: 
                line_chart.update()
            except Exception as ex:
                pass
            return

        # Animasyonlu Çizim Başlangıcı
        line_chart.data_series[0].data_points = []
        line_chart.data_series[1].data_points = []
        try: line_chart.update()
        except: pass
        
        time.sleep(0.2) 
        
        gelir_data = full_data[year]["gelir"]
        gider_data = full_data[year]["gider"]
        
        for i in range(len(gelir_data)):
            if state["current_page"] != "home": 
                state["animation_completed"] = True
                return
            
            line_chart.data_series[0].data_points.append(ft.LineChartDataPoint(i, gelir_data[i], tooltip=f"{gelir_data[i]:.1f}K"))
            line_chart.data_series[1].data_points.append(ft.LineChartDataPoint(i, gider_data[i], tooltip=f"{gider_data[i]:.1f}K"))
            
            try:
                if line_chart.page: line_chart.update()
            except: pass
            time.sleep(0.04) 
        
        state["animation_completed"] = True 
        try:
            if line_chart.page: line_chart.update()
        except Exception as ex:
            pass

    def on_year_change(e): 
        state["animation_completed"] = False
        # Hem yılan grafik hem de donut'ları güncelle
        threading.Thread(target=draw_snake_chart, args=(e.control.value,), daemon=True).start()
        # Donut'ları da güncelle
        update_donuts_for_year(int(e.control.value))
    
    def update_donuts_for_year(year):
        """Seçili yıla göre donut'ları günceller"""
        try:
            # Seçili yıl için istatistikleri al
            year_stats = get_dashboard_stats(year)
            
            # Her donut için yeni değerleri hesapla
            profit_max = max(abs(year_stats['net_profit']) * 1.2, 10000)
            income_max = max(year_stats['total_income'] * 1.2, 10000)
            expense_max = max(year_stats['total_expense'] * 1.2, 10000)
            avg_max = max(year_stats['monthly_avg'] * 1.2, 10000)
            
            # Donut'ları güncelle
            if len(state["donuts"]) >= 4:
                # Net kâr donut
                state["donuts"][0].update_value(abs(year_stats['net_profit']), profit_max, format_currency(year_stats['net_profit'], compact=True))
                
                # Toplam gelir donut
                state["donuts"][1].update_value(year_stats['total_income'], income_max, format_currency(year_stats['total_income'], compact=True))
                
                # Toplam gider donut
                state["donuts"][2].update_value(year_stats['total_expense'], expense_max, format_currency(year_stats['total_expense'], compact=True))
                
                # Aylık ortalama donut
                state["donuts"][3].update_value(year_stats['monthly_avg'], avg_max, format_currency(year_stats['monthly_avg'], compact=True))
        except Exception as e:
            print(f"Donut güncelleme hatası: {e}")

    # Backend callback'ini yeniden tanımla (grafikleri güncellemek için)
    def refresh_charts_and_data():
        """Grafikleri ve verileri yeniden yükler"""
        try:
            nonlocal full_data, chart_max_y, year_dropdown_options, available_years
            
            # 1. Grafik verilerini yeniden yükle
            full_data = get_line_chart_data()
            
            # 2. Yıl seçeneklerini güncelle - tüm veritabanı yıllarını çek
            available_years = get_all_available_years()
            year_dropdown_options = [ft.dropdown.Option(str(year)) for year in available_years]
            
            # 3. Dropdown'ı güncelle
            if year_dropdown_ref and hasattr(year_dropdown_ref, 'page') and year_dropdown_ref.page:
                year_dropdown_ref.options = year_dropdown_options
                # Eğer seçili yıl hala mevcut değilse, ilk yılı seç
                current_selected = year_dropdown_ref.value
                if current_selected not in [str(y) for y in available_years]:
                    year_dropdown_ref.value = str(available_years[0]) if available_years else str(datetime.now().year)
                year_dropdown_ref.update()
            
            # 4. Seçili yılı al
            selected_year = int(year_dropdown_ref.value) if year_dropdown_ref and year_dropdown_ref.value else (available_years[0] if available_years else datetime.now().year)
            
            # 5. Seçili yıla göre Max Y değerini hesapla
            chart_max_y = calculate_max_y(selected_year)
            
            # 6. Line chart'ı güncelle
            if line_chart:
                try:
                    line_chart.left_axis.labels = get_y_axis_labels(chart_max_y)
                    line_chart.max_y = chart_max_y
                    
                    if selected_year in full_data:
                        # Grafiği direkt çiz (animasyonsuz)
                        line_chart.data_series[0].data_points = [ft.LineChartDataPoint(i, full_data[selected_year]["gelir"][i], tooltip=f"{full_data[selected_year]['gelir'][i]:.1f}K") for i in range(12)]
                        line_chart.data_series[1].data_points = [ft.LineChartDataPoint(i, full_data[selected_year]["gider"][i], tooltip=f"{full_data[selected_year]['gider'][i]:.1f}K") for i in range(12)]
                    else:
                        # Veri yoksa grafiği temizle
                        line_chart.data_series[0].data_points = []
                        line_chart.data_series[1].data_points = []
                    
                    # Update sadece page varsa
                    if hasattr(line_chart, 'page') and line_chart.page:
                        line_chart.update()
                except:
                    pass
            
            # 7. Donut grafikleri güncelle - seçili yıla göre
            update_donuts_for_year(selected_year)
            
            # 7. Sayfayı güncelle
            try:
                page.update()
            except:
                pass
                        
        except Exception as e:
            pass
    
    # Ana sayfa callback'ini henüz kaydetme - animasyon başladıktan sonra kaydedeceğiz
    # state["update_callbacks"]["home_page"] = refresh_charts_and_data

    # --- SIDEBAR (GÜNCELLENDİ: GİRİŞ BUTONU DA STANDARDİZE EDİLDİ) ---
    class SidebarButton(ft.Container):
        def __init__(self, icon_name, text, page_name, is_selected=False):
            super().__init__()
            self.data = page_name
            self.is_selected = is_selected
            self.icon_name = icon_name  # İkon adını sakla
            self.width = 50
            self.height = 50
            self.border_radius = 12
            self.padding = 0
            self.alignment = ft.alignment.center
            self.animate = ft.Animation(200, "easeOut") 
            # Başlangıç rengi - seçili ise beyaz, değilse koyu gri
            initial_color = col_white if is_selected else "#374151"
            # İKİ AYRI IKON OLUŞTUR
            self.icon_expanded = ft.Icon(icon_name, size=24, color=initial_color)
            self.icon_collapsed = ft.Icon(icon_name, size=24, color=initial_color)
            self.text_control = ft.Text(text, size=15, weight="w600", visible=state["sidebar_expanded"], color=initial_color)
            self.content_row = ft.Row([self.icon_expanded, self.text_control], spacing=15, alignment=ft.MainAxisAlignment.START, visible=state["sidebar_expanded"])
            self.content_icon_only = ft.Container(content=self.icon_collapsed, alignment=ft.alignment.center, visible=not state["sidebar_expanded"])
            self.content = ft.Stack([self.content_row, self.content_icon_only])
            self.update_visuals(run_update=False)

        def update_visuals(self, run_update=True):
            self.text_control.visible = state["sidebar_expanded"]
            self.content_row.visible = state["sidebar_expanded"]
            self.content_icon_only.visible = not state["sidebar_expanded"]
            self.width = 220 if state["sidebar_expanded"] else 50
            self.padding = ft.padding.only(left=15) if state["sidebar_expanded"] else 0
            self.alignment = ft.alignment.center_left if state["sidebar_expanded"] else ft.alignment.center
            
            # --- STANDART KURAL ---
            if self.is_selected:
                self.bgcolor = col_primary
                new_color = col_white
                self.shadow = ft.BoxShadow(blur_radius=10, color=col_primary_50, offset=ft.Offset(0, 4))
            else:
                self.bgcolor = "#F5F5F5"  # Açık gri arka plan
                new_color = "#374151"  # Daha koyu gri - neredeyse siyah
                self.shadow = None
            
            # Her iki ikonu da güncelle
            self.icon_expanded.color = new_color
            self.icon_collapsed.color = new_color
            self.text_control.color = new_color
                
            if run_update: self.update()

    def toggle_sidebar(e):
        state["sidebar_expanded"] = not state["sidebar_expanded"]
        sidebar_container.width = 260 if state["sidebar_expanded"] else 90
        logo_text.visible = state["sidebar_expanded"]
        menu_row.alignment = ft.MainAxisAlignment.START if state["sidebar_expanded"] else ft.MainAxisAlignment.CENTER
        
        # Nested Column yapısında butonları güncelle
        for col in sidebar_column.controls:
            if isinstance(col, ft.Column):
                for btn in col.controls:
                    if isinstance(btn, SidebarButton):
                        # Önce görünürlük ayarlarını güncelle
                        btn.text_control.visible = state["sidebar_expanded"]
                        btn.content_row.visible = state["sidebar_expanded"]
                        btn.content_icon_only.visible = not state["sidebar_expanded"]
                        btn.width = 220 if state["sidebar_expanded"] else 50
                        btn.padding = ft.padding.only(left=15) if state["sidebar_expanded"] else 0
                        btn.alignment = ft.alignment.center_left if state["sidebar_expanded"] else ft.alignment.center
                        
                        # Renkleri güncelle
                        if btn.is_selected:
                            btn.bgcolor = col_primary
                            btn.icon_expanded.color = col_white
                            btn.icon_collapsed.color = col_white
                            btn.text_control.color = col_white
                            btn.shadow = ft.BoxShadow(blur_radius=10, color=col_primary_50, offset=ft.Offset(0, 4))
                        else:
                            btn.bgcolor = "#F5F5F5"
                            btn.icon_expanded.color = "#374151"
                            btn.icon_collapsed.color = "#374151"
                            btn.text_control.color = "#374151"
                            btn.shadow = None
                        
                        btn.update()
        page.update()

    # --- DÖNEMSEL GELİR SAYFASI ---
    def create_donemsel_page():
        # Yıl dropdown'ı için seçenekler
        current_year = datetime.now().year
        year_options = [ft.dropdown.Option(str(y)) for y in range(current_year - 2, current_year + 2)]
        
        year_dropdown = ft.Dropdown(
            options=year_options,
            value=str(current_year),
            text_size=12,
            content_padding=10,
            width=95,
            bgcolor=col_white,
            border_color=col_border,
            border_radius=8
        )
        
        # Kurumlar vergisi input field'ları - tabloda kullanılacak
        month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
        tax_fields_dict = {}
        tax_fields_list = []
        
        # Kaydetme fonksiyonu - odak kaybedildiğinde çalışır
        def on_tax_field_blur(e):
            """TextField'dan çıkıldığında otomatik kaydet"""
            try:
                selected_year = int(year_dropdown.value)
                monthly_data = {}
                
                for month_key in month_keys:
                    value = tax_fields_dict[month_key].value
                    try:
                        monthly_data[month_key] = float(value.replace(',', '.')) if value else 0
                    except ValueError:
                        monthly_data[month_key] = 0
                
                # Database'e kaydet
                backend_instance.db.add_or_update_corporate_tax(selected_year, monthly_data)
                
                # Veri güncelleme callback'ini çağır
                if backend_instance.on_data_updated:
                    backend_instance.on_data_updated()
                
                # Tabloyu güncelle (ödenecek vergi hesabı için)
                table_container.content = create_donemsel_table(selected_year, tax_fields_list, on_tax_field_blur)
                page.update()
            except:
                pass
        
        # 12 aylık TextField oluştur
        for i, month_key in enumerate(month_keys):
            text_field = ft.TextField(
                value="0",
                text_size=12,
                color=col_text,
                text_align=ft.TextAlign.CENTER,
                border_color="#E0E0E0",
                focused_border_color=col_primary,
                height=35,
                width=120,
                content_padding=ft.padding.symmetric(horizontal=5, vertical=5),
                bgcolor="#FAFAFA",
                suffix_text=" %",
                hint_text="0",
                on_blur=on_tax_field_blur
            )
            tax_fields_dict[month_key] = text_field
            tax_fields_list.append(text_field)
        
        # Database'den kurumlar vergisi verilerini yükle
        def load_corporate_tax_data():
            selected_year = int(year_dropdown.value)
            tax_data = backend_instance.db.get_corporate_tax(selected_year) or {}
            for month_key in month_keys:
                amount = tax_data.get(month_key, 0)
                tax_fields_dict[month_key].value = str(amount) if amount else "0"
            # Tabloya field'ları geç ve güncelle
            table_container.content = create_donemsel_table(selected_year, tax_fields_list, on_tax_field_blur)
            page.update()
        
        # Dinamik güncelleme için callback kaydet
        def refresh_donemsel_data():
            """Veri değiştiğinde dönemsel tabloyu güncelle"""
            try:
                # Sadece dönemsel sayfadayken güncelle
                if state["current_page"] != "donemsel":
                    return
                    
                selected_year = int(year_dropdown.value)
                
                # Kurumlar vergisi verilerini yeniden yükle
                tax_data = backend_instance.db.get_corporate_tax(selected_year) or {}
                month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
                for month_key in month_keys:
                    amount = tax_data.get(month_key, 0)
                    if month_key in tax_fields_dict:
                        tax_fields_dict[month_key].value = str(amount) if amount else "0"
                
                # Tabloyu güncelle
                table_container.content = create_donemsel_table(selected_year, tax_fields_list, on_tax_field_blur)
                if table_container.page:
                    table_container.update()
                    page.update()
            except:
                pass
        
        state["update_callbacks"]["donemsel_page"] = refresh_donemsel_data
        
        # Tablo container - başlangıçta field'ları ile oluştur
        table_container = ft.Container(
            width=1100,
            bgcolor=col_white,
            padding=20,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=10, color="#1A000000", offset=ft.Offset(0, 5)),
            content=create_donemsel_table(current_year, tax_fields_list, on_tax_field_blur)
        )
        
        # İlk yüklemede verileri doldur
        load_corporate_tax_data()
        
        def on_year_change(e):
            """Yıl değiştiğinde tabloyu güncelle"""
            selected_year = int(e.control.value)
            
            # Kurumlar vergisi verilerini yükle
            tax_data = backend_instance.db.get_corporate_tax(selected_year) or {}
            month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
            for month_key in month_keys:
                amount = tax_data.get(month_key, 0)
                tax_fields_dict[month_key].value = str(amount) if amount else "0"
            
            # Tabloyu güncelle
            table_container.content = create_donemsel_table(selected_year, tax_fields_list, on_tax_field_blur)
            page.update()
        
        year_dropdown.on_change = on_year_change
        
        # Export fonksiyonları
        def export_to_excel_donemsel(e):
            """Dönemsel gelir raporunu Excel'e aktar"""
            try:
                selected_year = int(year_dropdown.value)
                
                # Verileri topla
                monthly_results, quarterly_results, summary = calculate_periodic_data(selected_year)
                
                # Dosya yolu oluştur
                timestamp = datetime.now().strftime("%d-%m-%Y")
                filename = f"DonemselGelir_{selected_year}_{timestamp}.xlsx"
                export_folder = state.get("excel_export_path", os.path.join(os.getcwd(), "ExcelReports"))
                if not os.path.exists(export_folder):
                    os.makedirs(export_folder)
                file_path = os.path.join(export_folder, filename)
                
                # Export
                from toexcel import export_monthly_income_to_excel
                success = export_monthly_income_to_excel(selected_year, monthly_results, quarterly_results, summary, file_path)
                
                if success:
                    print(f"✅ Excel raporu oluşturuldu: {filename}")
                else:
                    print("❌ Excel raporu oluşturulamadı")
            except Exception as ex:
                print(f"❌ Hata: {str(ex)}")
        
        def export_to_pdf_donemsel(e):
            """Dönemsel gelir raporunu PDF'e aktar"""
            try:
                selected_year = int(year_dropdown.value)
                
                # Verileri topla
                monthly_results, quarterly_results, summary = calculate_periodic_data(selected_year)
                
                # Dosya yolu oluştur
                timestamp = datetime.now().strftime("%d-%m-%Y")
                filename = f"DonemselGelir_{selected_year}_{timestamp}.pdf"
                export_folder = state.get("pdf_export_path", os.path.join(os.getcwd(), "PDFExports"))
                if not os.path.exists(export_folder):
                    os.makedirs(export_folder)
                file_path = os.path.join(export_folder, filename)
                
                # Export
                from topdf import export_monthly_income_to_pdf
                success = export_monthly_income_to_pdf(selected_year, monthly_results, quarterly_results, summary, file_path)
                
                if success:
                    print(f"✅ PDF raporu oluşturuldu: {filename}")
                else:
                    print("❌ PDF raporu oluşturulamadı")
            except Exception as ex:
                print(f"❌ Hata: {str(ex)}")
        
        def calculate_periodic_data(year):
            """Dönemsel veriler için hesaplama yap"""
            # Backend'den verileri çek
            income_invoices = backend_instance.handle_invoice_operation('get', 'outgoing') or []
            expense_invoices = backend_instance.handle_invoice_operation('get', 'incoming') or []
            general_expenses = backend_instance.db.get_yearly_expenses(year) or {}
            corporate_tax_data = backend_instance.db.get_corporate_tax(year) or {}
            
            # Aylık hesaplamalar
            monthly_income = [0.0] * 12
            monthly_expense = [0.0] * 12
            monthly_general = [0.0] * 12
            monthly_income_kdv = [0.0] * 12
            monthly_expense_kdv = [0.0] * 12
            monthly_corporate_tax = [0.0] * 12
            
            # Gelir faturalarını işle
            for invoice in income_invoices:
                tarih = invoice.get('tarih', '')
                if not tarih: continue
                parts = tarih.split('.')
                if len(parts) != 3: continue
                try:
                    month = int(parts[1])
                    invoice_year = int(parts[2])
                    if invoice_year == year:
                        monthly_income[month-1] += float(invoice.get('toplam_tutar_tl', 0))
                        monthly_income_kdv[month-1] += float(invoice.get('kdv_tutari', 0))
                except:
                    continue
            
            # Gider faturalarını işle
            for invoice in expense_invoices:
                tarih = invoice.get('tarih', '')
                if not tarih: continue
                parts = tarih.split('.')
                if len(parts) != 3: continue
                try:
                    month = int(parts[1])
                    invoice_year = int(parts[2])
                    if invoice_year == year:
                        monthly_expense[month-1] += float(invoice.get('toplam_tutar_tl', 0))
                        monthly_expense_kdv[month-1] += float(invoice.get('kdv_tutari', 0))
                except:
                    continue
            
            # Genel gider ve kurumlar vergisi
            month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
            for i in range(12):
                month_key = month_keys[i]
                if month_key in general_expenses:
                    monthly_general[i] = float(general_expenses[month_key] or 0)
                if month_key in corporate_tax_data:
                    monthly_corporate_tax[i] = float(corporate_tax_data[month_key] or 0)
            
            # Aylık sonuçlar
            monthly_results = []
            for i in range(12):
                total_expense = monthly_expense[i] + monthly_general[i]
                kdv_farki = abs(monthly_income_kdv[i] - monthly_expense_kdv[i])
                monthly_results.append({
                    'kesilen': monthly_income[i],
                    'gelen': total_expense,
                    'kdv': kdv_farki
                })
            
            # Çeyreklik sonuçlar
            quarterly_results = []
            for q in range(4):
                start_month = q * 3
                end_month = start_month + 3
                q_income = sum(monthly_income[start_month:end_month])
                q_expense = sum(monthly_expense[start_month:end_month]) + sum(monthly_general[start_month:end_month])
                q_tax_percent = monthly_corporate_tax[end_month - 1]  # Son ayın yüzdesi
                q_kurumlar = (q_income + sum(monthly_expense[start_month:end_month])) * q_tax_percent / 100 if q_tax_percent > 0 else 0
                q_kdv = sum(abs(monthly_income_kdv[i] - monthly_expense_kdv[i]) for i in range(start_month, end_month))
                quarterly_results.append({
                    'odenecek_kv': q_kurumlar + q_kdv
                })
            
            # Özet
            total_income = sum(monthly_income)
            total_expense = sum(monthly_expense) + sum(monthly_general)
            total_kdv = sum(abs(monthly_income_kdv[i] - monthly_expense_kdv[i]) for i in range(12))
            total_kurumlar = sum(q['odenecek_kv'] for q in quarterly_results)
            net_profit = total_income - total_expense - total_kdv - (total_kurumlar - total_kdv)  # KDV daha önce çıkarıldı
            
            summary = {
                'toplam_gelir': total_income,
                'toplam_gider': total_expense,
                'yillik_kar': net_profit
            }
            
            return monthly_results, quarterly_results, summary
        
        right_buttons = ft.Container(
            padding=ft.padding.only(right=40),
            content=ft.Row([
                ScaleButton("table_view", "#217346", "Excel", width=45, height=40, on_click=export_to_excel_donemsel),
                ScaleButton("picture_as_pdf", "#D32F2F", "PDF", width=45, height=40, on_click=export_to_pdf_donemsel),
                ScaleButton("print", "#607D8B", "Yazdır", width=45, height=40),
            ], spacing=8)
        )

        top_bar = ft.Row([
            ft.Container(height=38, content=year_dropdown),
            right_buttons
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        return ft.Container(
            alignment=ft.alignment.top_center,
            padding=30,
            content=ft.Column([
                ft.Row([ft.Text("Dönemsel ve Yıllık Gelir", size=26, weight="bold", color=col_text)]),
                ft.Container(height=15),
                ft.Container(content=top_bar, width=1100),
                ft.Container(height=15),
                table_container
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO, expand=True)
        )

    # --- FATURA SAYFASI ---
    def create_invoices_page():
        general_expenses_section = create_grid_expenses(page)
        # Başlangıç durumuna göre visibility ayarla (income=gelir ise gizli, expense=gider ise görünür)
        general_expenses_section.visible = (state.get("invoice_type", "income") == "expense")

        # Seçili fatura sayısını gösteren text
        selected_count_text = ft.Text("", size=12, color=col_danger, weight="bold", visible=False)
        
        # Input alanları önce tanımlanmalı (update_selected_count bunları kullanacak)
        input_fatura_no = ft.TextField(hint_text="FAT-2025...", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_irsaliye = ft.TextField(hint_text="IRS...", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_tarih = ft.TextField(hint_text="25.11.2025", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_firma = ft.TextField(hint_text="Firma seçiniz...", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_malzeme = ft.TextField(hint_text="Ürün giriniz...", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_miktar = ft.TextField(hint_text="0", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_tutar = ft.TextField(hint_text="0.00", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_para_birimi = ft.Dropdown(options=[ft.dropdown.Option("TL"), ft.dropdown.Option("USD"), ft.dropdown.Option("EUR")], text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=5), hint_text="TL", hint_style=ft.TextStyle(color="#D0D0D0", size=12), value="TL")
        input_kdv = ft.TextField(hint_text="20.0", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        
        # Manuel döviz kuru girişi (opsiyonel)
        input_usd_kur = ft.TextField(hint_text="Opsiyonel (TCMB)", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        input_eur_kur = ft.TextField(hint_text="Opsiyonel (TCMB)", hint_style=ft.TextStyle(color="#D0D0D0", size=12), text_size=13, color=col_text, border_color="transparent", bgcolor="transparent", content_padding=ft.padding.only(left=10, bottom=12))
        
        def update_selected_count(e=None):
            """Seçili fatura sayısını güncelle ve tek seçimde inputları doldur"""
            try:
                if table_container.content and hasattr(table_container.content, 'rows'):
                    # Checkbox'lardan seçili olanları bul
                    selected_rows = []
                    for row in table_container.content.rows:
                        # İlk hücredeki checkbox'u kontrol et
                        if len(row.cells) > 0:
                            first_cell = row.cells[0]
                            if hasattr(first_cell, 'content') and isinstance(first_cell.content, ft.Checkbox):
                                if first_cell.content.value:
                                    selected_rows.append(row)
                    
                    selected_count = len(selected_rows)
                    
                    if selected_count > 0:
                        selected_count_text.value = f"({selected_count})"
                        selected_count_text.visible = True
                        
                        # Tek satır seçiliyse inputları doldur
                        if selected_count == 1 and isinstance(selected_rows[0].data, dict):
                            invoice = selected_rows[0].data
                            input_fatura_no.value = str(invoice.get('fatura_no', ''))
                            input_irsaliye.value = str(invoice.get('irsaliye_no', ''))
                            input_tarih.value = str(invoice.get('tarih', ''))
                            input_firma.value = str(invoice.get('firma', ''))
                            input_malzeme.value = str(invoice.get('malzeme', ''))
                            input_miktar.value = str(invoice.get('miktar', ''))
                            
                            # Para birimine göre doğru tutar alanını seç
                            birim = str(invoice.get('birim', 'TL'))
                            input_para_birimi.value = birim
                            
                            if birim == 'TL':
                                tutar = round(float(invoice.get('toplam_tutar_tl', 0)), 5)
                            elif birim == 'USD':
                                tutar = round(float(invoice.get('toplam_tutar_usd', 0)), 5)
                            elif birim == 'EUR':
                                tutar = round(float(invoice.get('toplam_tutar_eur', 0)), 5)
                            else:
                                tutar = round(float(invoice.get('toplam_tutar_tl', 0)), 5)
                            
                            input_tutar.value = str(tutar) if tutar else '0'
                            input_kdv.value = str(round(float(invoice.get('kdv_yuzdesi', 20.0)), 5))
                            
                            # Manuel döviz kurlarını doldur (varsa)
                            usd_rate = round(float(invoice.get('usd_rate', 0)), 5)
                            eur_rate = round(float(invoice.get('eur_rate', 0)), 5)
                            
                            input_usd_kur.value = str(usd_rate) if usd_rate and usd_rate > 0 else ''
                            input_eur_kur.value = str(eur_rate) if eur_rate and eur_rate > 0 else ''
                    else:
                        selected_count_text.value = ""
                        selected_count_text.visible = False
                    
                    # Hem selected_count_text hem de tüm input alanlarını güncelle
                    selected_count_text.update()
                    table_container.update()
                    page.update()
            except Exception as ex:
                pass
        
        table_container = ft.Container(
            width=1200, 
            border_radius=12, 
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000", offset=ft.Offset(0, 5)), 
            bgcolor=col_white, 
            content=create_invoice_table_content("newest", state.get("invoice_type", "income"), on_select_changed=update_selected_count)
        )

        def update_invoice_table(sort_option=None):
            # Sadece fatura sayfasındayken güncelle
            if state["current_page"] != "invoices":
                return
                
            # Güncel invoice_type'ı kullan
            if sort_option is None:
                sort_option = state.get("invoice_sort_option", "newest")
            current_invoice_type = state.get("invoice_type", "income")
            table_container.content = create_invoice_table_content(sort_option, current_invoice_type, on_select_changed=update_selected_count)
            if table_container.page:
                table_container.update()
        
        # Dinamik güncelleme için callback kaydet
        state["update_callbacks"]["invoice_page"] = update_invoice_table

        def on_sort_change(e): update_invoice_table(e.control.value)

        def toggle_invoice_type(e):
            # State'i değiştir
            state["invoice_type"] = "expense" if state["invoice_type"] == "income" else "income"
            is_expense = state["invoice_type"] == "expense"
            
            # Buton görünümünü güncelle
            active_color = col_secondary if is_expense else col_primary
            btn_container = e.control
            btn_container.content.controls[0].value = "Gelen Faturalar (Gider)" if is_expense else "Giden Faturalar (Gelir)"
            btn_container.bgcolor = active_color
            btn_container.shadow.color = col_secondary_50 if is_expense else col_primary_50
            btn_container.update()
            
            # Genel giderler bölümünü göster/gizle
            general_expenses_section.visible = is_expense
            general_expenses_section.update()
            
            # Fatura tablosunu güncelle
            update_invoice_table(state.get("invoice_sort_option", "newest"))

        # Başlangıç durumuna göre buton ayarla (state başlangıçta "income")
        initial_is_expense = state.get("invoice_type", "income") == "expense"
        initial_color = col_secondary if initial_is_expense else col_primary
        initial_text = "Gelen Faturalar (Gider)" if initial_is_expense else "Giden Faturalar (Gelir)"
        initial_shadow = col_secondary_50 if initial_is_expense else col_primary_50
        
        type_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Text(initial_text, color=col_white, weight="bold", size=14), 
                ft.Icon("swap_horiz", color=col_white, size=20)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5), 
            bgcolor=initial_color, 
            padding=ft.padding.symmetric(horizontal=20, vertical=10), 
            border_radius=8, 
            on_click=toggle_invoice_type, 
            ink=False, 
            shadow=ft.BoxShadow(blur_radius=5, color=initial_shadow, offset=ft.Offset(0,2)), 
            animate=ft.Animation(100, "easeOut")
        )

        def clear_inputs(e=None):
            """Input alanlarını temizle ve seçimleri kaldır"""
            try:
                input_fatura_no.value = ""
                input_irsaliye.value = ""
                input_tarih.value = ""
                input_firma.value = ""
                input_malzeme.value = ""
                input_miktar.value = ""
                input_tutar.value = ""
                input_para_birimi.value = "TL"
                input_kdv.value = ""
                input_usd_kur.value = ""
                input_eur_kur.value = ""
                state["selected_invoice_id"] = None
                
                # Tüm checkbox seçimlerini kaldır
                if table_container.content and hasattr(table_container.content, 'rows'):
                    for row in table_container.content.rows:
                        if len(row.cells) > 0:
                            first_cell = row.cells[0]
                            if hasattr(first_cell, 'content') and isinstance(first_cell.content, ft.Checkbox):
                                first_cell.content.value = False
                
                # Seçim sayısını sıfırla
                selected_count_text.value = ""
                selected_count_text.visible = False
                
                page.update()
            except Exception as ex:
                pass

        def add_invoice(e):
            """Fatura ekle"""
            try:
                # Input verilerini topla
                invoice_data = {
                    'fatura_no': input_fatura_no.value or "",
                    'irsaliye_no': input_irsaliye.value or "",
                    'tarih': input_tarih.value or "",
                    'firma': input_firma.value or "",
                    'malzeme': input_malzeme.value or "",
                    'miktar': input_miktar.value or "",
                    'toplam_tutar': float(input_tutar.value) if input_tutar.value else 0,
                    'birim': input_para_birimi.value or "TL",
                    'kdv_yuzdesi': float(input_kdv.value) if input_kdv.value else 20.0
                }
                
                # Manuel kur girişi varsa ekle (opsiyonel)
                if input_usd_kur.value and input_usd_kur.value.strip():
                    try:
                        invoice_data['manual_usd_rate'] = float(input_usd_kur.value.replace(',', '.'))
                    except ValueError:
                        pass
                
                if input_eur_kur.value and input_eur_kur.value.strip():
                    try:
                        invoice_data['manual_eur_rate'] = float(input_eur_kur.value.replace(',', '.'))
                    except ValueError:
                        pass
                
                # Fatura işle
                processed_data = process_invoice(invoice_data)
                
                if processed_data:
                    # Backend'e kaydet
                    invoice_type = 'incoming' if state["invoice_type"] == "expense" else 'outgoing'
                    
                    result = backend_instance.handle_invoice_operation('add', invoice_type, processed_data)
                    
                    if result:
                        # Başarılı - tabloyu güncelle
                        update_invoice_table(state.get("invoice_sort_option", "newest"))
                        clear_inputs()
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ Fatura başarıyla eklendi!", color=col_white), bgcolor=col_success)
                        page.snack_bar.open = True
                        page.update()
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("❌ Fatura eklenemedi!", color=col_white), bgcolor=col_danger)
                        page.snack_bar.open = True
                        page.update()
                else:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ Geçersiz fatura verisi! Tutar giriniz.", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    
            except Exception as ex:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ Hata: {str(ex)}", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()

        def update_invoice(e):
            """Seçili faturayi güncelle"""
            try:
                # Checkbox'lardan seçili olanları bul
                selected_rows = []
                for row in table_container.content.rows:
                    if len(row.cells) > 0:
                        first_cell = row.cells[0]
                        if hasattr(first_cell, 'content') and isinstance(first_cell.content, ft.Checkbox):
                            if first_cell.content.value:
                                selected_rows.append(row)
                
                if not selected_rows:
                    page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ Güncellemek için bir fatura seçin!", color=col_white), bgcolor=col_secondary)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                if len(selected_rows) > 1:
                    page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ Sadece bir fatura seçin!", color=col_white), bgcolor=col_secondary)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                # Input verilerini topla
                invoice_data = {
                    'fatura_no': input_fatura_no.value or "",
                    'irsaliye_no': input_irsaliye.value or "",
                    'tarih': input_tarih.value or "",
                    'firma': input_firma.value or "",
                    'malzeme': input_malzeme.value or "",
                    'miktar': input_miktar.value or "",
                    'toplam_tutar': float(input_tutar.value) if input_tutar.value else 0,
                    'birim': input_para_birimi.value or "TL",
                    'kdv_yuzdesi': float(input_kdv.value) if input_kdv.value else 20.0
                }
                
                # Manuel kur girişi varsa ekle (opsiyonel)
                if input_usd_kur.value and input_usd_kur.value.strip():
                    try:
                        invoice_data['manual_usd_rate'] = float(input_usd_kur.value.replace(',', '.'))
                    except ValueError:
                        pass
                
                if input_eur_kur.value and input_eur_kur.value.strip():
                    try:
                        invoice_data['manual_eur_rate'] = float(input_eur_kur.value.replace(',', '.'))
                    except ValueError:
                        pass
                
                # Fatura işle
                processed_data = process_invoice(invoice_data)
                
                if processed_data:
                    # Backend'e güncelle
                    invoice_data_from_row = selected_rows[0].data
                    invoice_id = invoice_data_from_row.get('id') if isinstance(invoice_data_from_row, dict) else invoice_data_from_row
                    invoice_type = 'incoming' if state["invoice_type"] == "expense" else 'outgoing'
                    
                    result = backend_instance.handle_invoice_operation('update', invoice_type, processed_data, record_id=invoice_id)
                    
                    if result:
                        # Tabloyu yenile - invoice type'a göre
                        table_container.content = create_invoice_table_content(
                            state.get("invoice_sort_option", "newest"),
                            state.get("invoice_type", "income"),
                            on_select_changed=update_selected_count
                        )
                        table_container.update()
                        clear_inputs()
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ Fatura güncellendi!", color=col_white), bgcolor=col_success)
                        page.snack_bar.open = True
                        page.update()
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("❌ Güncelleme başarısız!", color=col_white), bgcolor=col_danger)
                        page.snack_bar.open = True
                        page.update()
                else:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ Geçersiz fatura verisi!", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    
            except Exception as ex:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ Güncelleme hatası: {str(ex)}", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()

        def delete_invoice(e):
            """Seçili faturaları sil - Çoklu seçim destekli"""
            # Checkbox'lardan seçili olanları bul
            selected_rows = []
            for row in table_container.content.rows:
                if len(row.cells) > 0:
                    first_cell = row.cells[0]
                    if hasattr(first_cell, 'content') and isinstance(first_cell.content, ft.Checkbox):
                        if first_cell.content.value:
                            selected_rows.append(row)
            
            if not selected_rows:
                page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ Lütfen silmek için en az bir fatura seçin!", color=col_white), bgcolor=col_secondary)
                page.snack_bar.open = True
                page.update()
                return
            
            selected_count = len(selected_rows)
            
            # Tüm faturaları direkt sil (tek veya çoklu, fark etmez)
            try:
                current_invoice_type = state.get("invoice_type", "income")
                db_type = 'outgoing' if current_invoice_type == 'income' else 'incoming'
                
                # Callback'i geçici olarak devre dışı bırak (çoklu silmede her seferinde tetiklenmesin)
                original_callback = backend_instance.on_data_updated
                backend_instance.on_data_updated = None
                
                # Her seçili satırı sil
                deleted_count = 0
                failed_count = 0
                for idx, row in enumerate(selected_rows):
                    invoice_data = row.data
                    
                    if invoice_data and isinstance(invoice_data, dict) and 'id' in invoice_data:
                        invoice_id = invoice_data['id']
                        result = backend_instance.handle_invoice_operation(
                            operation='delete',
                            invoice_type=db_type,
                            record_id=invoice_id
                        )
                        if result:
                            deleted_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                
                # Callback'i geri yükle
                backend_instance.on_data_updated = original_callback
                
                # Tabloyu yenile
                table_container.content = create_invoice_table_content(
                    state.get("invoice_sort_option", "newest"),
                    state.get("invoice_type", "income"),
                    on_select_changed=update_selected_count
                )
                clear_inputs()
                
                # Callback'i manuel olarak tetikle (tek seferde tüm güncellemeleri yap)
                if original_callback:
                    original_callback()
                
                # Bildirim göster
                if deleted_count > 0:
                    message = f"✅ {deleted_count} fatura silindi!"
                    if failed_count > 0:
                        message += f" ({failed_count} başarısız)"
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(message, color=col_white),
                        bgcolor=col_success
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("❌ Hiçbir fatura silinemedi!", color=col_white),
                        bgcolor=col_danger
                    )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ Silme hatası: {str(ex)}", color=col_white),
                    bgcolor=col_danger
                )
                page.snack_bar.open = True
                page.update()

        def export_to_excel(e):
            """Faturalari Excel'e aktar"""
            try:
                current_invoice_type = state.get("invoice_type", "income")
                db_type = 'outgoing' if current_invoice_type == 'income' else 'incoming'
                
                invoices = backend_instance.handle_invoice_operation(
                    operation='get',
                    invoice_type=db_type,
                    limit=1000
                )
                
                if not invoices:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ Dışa aktarılacak fatura bulunamadı!", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                # Ayarlardan klasör yolunu al
                export_folder = state.get("excel_export_path", os.path.join(os.getcwd(), "ExcelReports"))
                os.makedirs(export_folder, exist_ok=True)
                
                # Dosya yolu oluştur
                type_name = "GelirleFaturalari" if current_invoice_type == "income" else "GiderFaturalari"
                timestamp = datetime.now().strftime("%d-%m-%Y")
                file_path = os.path.join(export_folder, f"{type_name}_{timestamp}.xlsx")
                
                # Excel'e aktar
                success = excel_exporter.export_invoices_to_excel(invoices, type_name, file_path)
                
                if success:
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {len(invoices)} fatura Excel'e aktarıldı!\n{file_path}", color=col_white), bgcolor=col_success)
                    page.snack_bar.open = True
                    page.update()
                else:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ Excel aktarımı başarısız!", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    
            except Exception as ex:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ Excel hatası: {str(ex)}", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()

        def export_to_pdf(e):
            """Faturalari PDF'e aktar"""
            try:
                current_invoice_type = state.get("invoice_type", "income")
                db_type = 'outgoing' if current_invoice_type == 'income' else 'incoming'
                
                invoices = backend_instance.handle_invoice_operation(
                    operation='get',
                    invoice_type=db_type,
                    limit=1000
                )
                
                if not invoices:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ Dışa aktarılacak fatura bulunamadı!", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                # Ayarlardan klasör yolunu al
                export_folder = state.get("pdf_export_path", os.path.join(os.getcwd(), "PDFExports"))
                os.makedirs(export_folder, exist_ok=True)
                
                # Dosya yolu oluştur
                type_name = "GelirleFaturalari" if current_invoice_type == "income" else "GiderFaturalari"
                timestamp = datetime.now().strftime("%d-%m-%Y")
                file_path = os.path.join(export_folder, f"{type_name}_{timestamp}.pdf")
                
                # PDF'e aktar
                success = pdf_exporter.export_invoices_to_pdf(invoices, db_type, file_path)
                
                if success:
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {len(invoices)} fatura PDF'e aktarıldı!\n{file_path}", color=col_white), bgcolor=col_success)
                    page.snack_bar.open = True
                    page.update()
                else:
                    page.snack_bar = ft.SnackBar(content=ft.Text("❌ PDF aktarımı başarısız!", color=col_white), bgcolor=col_danger)
                    page.snack_bar.open = True
                    page.update()
                    
            except Exception as ex:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ PDF hatası: {str(ex)}", color=col_white), bgcolor=col_danger)
                page.snack_bar.open = True
                page.update()

        # Butonları oluştur
        btn_clear = AestheticButton("Yeni / Temizle", "refresh", "#7F8C8D", width=145, on_click=clear_inputs)
        btn_add = AestheticButton("Ekle", "add", col_success, width=110, on_click=add_invoice)
        btn_update = AestheticButton("Güncelle", "update", col_blue_donut, width=125, on_click=update_invoice)
        
        # Sil butonu - seçili sayı ile
        btn_delete_container = ft.Row([
            AestheticButton("Sil", "delete", col_danger, width=110, on_click=delete_invoice),
            selected_count_text
        ], spacing=5, alignment=ft.MainAxisAlignment.START)
        
        operation_buttons = ft.Row([btn_clear, btn_add, btn_update, btn_delete_container], spacing=15)

        # Sağ üst butonlar - Excel, PDF export
        btn_excel = ScaleButton("table_view", "#217346", "Excel Olarak İndir", width=50, height=45)
        btn_excel.on_click = export_to_excel
        
        btn_pdf = ScaleButton("picture_as_pdf", "#D32F2F", "PDF Olarak İndir", width=50, height=45)
        btn_pdf.on_click = export_to_pdf
        
        right_buttons_row = ft.Row([ScaleButton("qr_code_scanner", "#3498DB", "Kamerayı Aç / QR Ekle", width=50, height=45), btn_excel, btn_pdf, ScaleButton("print", "#607D8B", "Yazdır", width=50, height=45)], spacing=10)
        
        right_buttons_container = ft.Container(content=right_buttons_row, padding=ft.padding.only(right=25))

        sort_dropdown = ft.Container(padding=ft.padding.only(left=20), content=ft.Dropdown(options=[ft.dropdown.Option("newest", "Son Eklenen"), ft.dropdown.Option("date_desc", "Yeniden Eskiye"), ft.dropdown.Option("date_asc", "Eskiden Yeniye")], value="newest", on_change=on_sort_change, width=160, text_size=13, label="Sıralama", border_radius=10, content_padding=10, bgcolor=col_white, border_color=col_border))

        controls_row = ft.Row([type_toggle_btn, sort_dropdown, ft.Container(expand=True), right_buttons_container], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Input satırları - TextField referanslarını kullan
        input_line_1 = ft.Row([
            ft.Column([ft.Text("Fatura No", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_fatura_no, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("İrsaliye", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_irsaliye, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("Tarih", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_tarih, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("Firma", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_firma, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=2)
        ], spacing=15)
        
        input_line_2 = ft.Row([
            ft.Column([ft.Text("Malzeme/Hizmet", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_malzeme, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=2),
            ft.Column([ft.Text("Miktar", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_miktar, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("Tutar", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_tutar, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("Para Birimi", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_para_birimi, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("KDV Tutarı", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_kdv, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1)
        ], spacing=15)
        
        # Manuel döviz kuru satırı (opsiyonel)
        input_line_3 = ft.Row([
            ft.Column([ft.Text("USD Kuru (1 USD = ? TL)", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_usd_kur, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Column([ft.Text("EUR Kuru (1 EUR = ? TL)", size=12, weight="w500", color=col_text_secondary), ft.Container(content=input_eur_kur, bgcolor=col_card, border_radius=6, height=42, border=ft.border.all(1, "#E0E0E0"))], spacing=5, expand=1),
            ft.Container(expand=3)  # Boş alan
        ], spacing=15)

        return ft.Container(alignment=ft.alignment.top_center, padding=30, content=ft.Column([
            ft.Row([ft.Text("Fatura Yönetimi", size=28, weight="bold", color=col_text)], width=1200),
            ft.Container(height=15), ft.Container(content=controls_row, width=1200), ft.Container(height=20),
            ft.Container(content=ft.Column([input_line_1, ft.Container(height=5), input_line_2, ft.Container(height=5), input_line_3], spacing=10), width=1200),
            ft.Container(height=10), ft.Container(content=operation_buttons, width=1200, alignment=ft.alignment.center_left, padding=ft.padding.only(left=15)),
            ft.Container(height=20),
            table_container, 
            ft.Container(height=50), 
            ft.Container(content=general_expenses_section, width=1200)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO))

    # Sayfa Yöneticisi
    dashboard_content = ft.Container() 
    faturalar_page = create_invoices_page()
    donemsel_page = create_donemsel_page()
    
    # Ayarlar sayfası
    def create_settings_page():
        """Ayarlar sayfası - Export klasörleri seçimi"""
        
        # Mevcut ayarları yükle
        def load_settings():
            try:
                cursor = backend_instance.db.settings_conn.cursor()
                cursor.execute("SELECT key, value FROM settings WHERE key IN ('excel_export_path', 'pdf_export_path')")
                settings = cursor.fetchall()
                for key, value in settings:
                    state[key] = value
            except:
                pass
        
        load_settings()
        
        excel_path_text = ft.Text(
            state.get("excel_export_path", os.path.join(os.getcwd(), "ExcelReports")),
            size=13,
            color=col_text,
            weight="w500"
        )
        
        pdf_path_text = ft.Text(
            state.get("pdf_export_path", os.path.join(os.getcwd(), "PDFExports")),
            size=13,
            color=col_text,
            weight="w500"
        )
        
        def save_setting(key, value):
            """Ayarı database'e kaydet"""
            try:
                cursor = backend_instance.db.settings_conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                backend_instance.db.settings_conn.commit()
                state[key] = value
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ Ayar kaydedildi!", color=col_white),
                    bgcolor=col_success
                )
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ Kaydetme hatası: {str(e)}", color=col_white),
                    bgcolor=col_danger
                )
                page.snack_bar.open = True
                page.update()
        
        def pick_excel_folder(e):
            def on_result(e: ft.FilePickerResultEvent):
                if e.path:
                    excel_path_text.value = e.path
                    save_setting("excel_export_path", e.path)
                    excel_path_text.update()
            
            file_picker = ft.FilePicker(on_result=on_result)
            page.overlay.append(file_picker)
            page.update()
            file_picker.get_directory_path(dialog_title="Excel Klasörünü Seç")
        
        def pick_pdf_folder(e):
            def on_result(e: ft.FilePickerResultEvent):
                if e.path:
                    pdf_path_text.value = e.path
                    save_setting("pdf_export_path", e.path)
                    pdf_path_text.update()
            
            file_picker = ft.FilePicker(on_result=on_result)
            page.overlay.append(file_picker)
            page.update()
            file_picker.get_directory_path(dialog_title="PDF Klasörünü Seç")
        
        return ft.Container(
            alignment=ft.alignment.top_center,
            padding=30,
            content=ft.Column([
                ft.Text("Ayarlar", size=28, weight="bold", color=col_text),
                ft.Container(height=30),
                
                # Excel Export Klasörü
                ft.Container(
                    width=800,
                    bgcolor=col_white,
                    border_radius=12,
                    padding=20,
                    shadow=ft.BoxShadow(blur_radius=10, color="#1A000000", offset=ft.Offset(0, 3)),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("table_view", color=col_primary, size=28),
                            ft.Text("Excel Export Klasörü", size=18, weight="bold", color=col_text)
                        ], spacing=10),
                        ft.Container(height=10),
                        ft.Container(
                            bgcolor=col_bg,
                            border_radius=8,
                            padding=15,
                            content=excel_path_text
                        ),
                        ft.Container(height=10),
                        ft.ElevatedButton(
                            "Klasör Seç",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=pick_excel_folder,
                            bgcolor=col_primary,
                            color=col_white,
                            height=40
                        )
                    ], spacing=5)
                ),
                
                ft.Container(height=20),
                
                # PDF Export Klasörü
                ft.Container(
                    width=800,
                    bgcolor=col_white,
                    border_radius=12,
                    padding=20,
                    shadow=ft.BoxShadow(blur_radius=10, color="#1A000000", offset=ft.Offset(0, 3)),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("picture_as_pdf", color=col_danger, size=28),
                            ft.Text("PDF Export Klasörü", size=18, weight="bold", color=col_text)
                        ], spacing=10),
                        ft.Container(height=10),
                        ft.Container(
                            bgcolor=col_bg,
                            border_radius=8,
                            padding=15,
                            content=pdf_path_text
                        ),
                        ft.Container(height=10),
                        ft.ElevatedButton(
                            "Klasör Seç",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=pick_pdf_folder,
                            bgcolor=col_danger,
                            color=col_white,
                            height=40
                        )
                    ], spacing=5)
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    
    settings_page = create_settings_page()

    def change_view(e):
        clicked_btn_data = e.control.data
        
        if state["current_page"] == "home" and clicked_btn_data != "home":
             state["animation_completed"] = True 
        
        state["current_page"] = clicked_btn_data
        
        # Nested Column yapısında butonları güncelle
        for col in sidebar_column.controls:
            if isinstance(col, ft.Column):
                for btn in col.controls:
                    if isinstance(btn, SidebarButton):
                        btn.is_selected = (btn.data == clicked_btn_data)
                        btn.update_visuals()
        
        if clicked_btn_data == "home":
            content_area.content = dashboard_content
            threading.Thread(target=start_animations, daemon=True).start()
            # Ana sayfa yüklendiğinde verileri güncelle
            if state["update_callbacks"]["home_page"]:
                state["update_callbacks"]["home_page"]()
        elif clicked_btn_data == "faturalar":
            state["current_page"] = "invoices"  # Fatura sayfası için doğru key
            content_area.content = faturalar_page
            # Fatura sayfası yüklendiğinde tabloyu güncelle
            if state["update_callbacks"]["invoice_page"]:
                state["update_callbacks"]["invoice_page"]()
        elif clicked_btn_data == "raporlar":
            state["current_page"] = "donemsel"  # Dönemsel sayfa için doğru key
            content_area.content = donemsel_page
            # Dönemsel sayfa yüklendiğinde tabloyu güncelle
            if state["update_callbacks"]["donemsel_page"]:
                state["update_callbacks"]["donemsel_page"]()
        elif clicked_btn_data == "ayarlar":
            content_area.content = settings_page
        
        content_area.update()

    
    logo_text = ft.Text("Excellent", size=24, weight="bold", color=col_text, visible=False)
    menu_icon = ft.IconButton(icon="menu", icon_color=col_text, on_click=toggle_sidebar)
    menu_row = ft.Row([menu_icon, logo_text], spacing=5, alignment=ft.MainAxisAlignment.CENTER)

    btn_home = SidebarButton("home_rounded", "Giriş", "home", False)  # Başlangıçta False
    btn_faturalar = SidebarButton("receipt_long_rounded", "Faturalar", "faturalar")
    btn_raporlar = SidebarButton("bar_chart_rounded", "Raporlar", "raporlar")
    btn_ayarlar = SidebarButton("settings", "Ayarlar", "ayarlar")
    btn_home.on_click = change_view
    btn_faturalar.on_click = change_view
    btn_raporlar.on_click = change_view
    btn_ayarlar.on_click = change_view
    
    # Ev butonunu başlangıçta seçili yap
    btn_home.is_selected = True
    btn_home.update_visuals(run_update=False)

    # Sidebar'ı MainAxisAlignment.SPACE_BETWEEN ile düzenle - Ayarlar en altta
    sidebar_column = ft.Column([
        ft.Column([
            ft.Container(height=20),
            menu_row,
            ft.Container(height=30),
            btn_home,
            btn_faturalar,
            btn_raporlar
        ], spacing=15),
        ft.Column([
            btn_ayarlar,
            ft.Container(height=20)
        ], spacing=15)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    sidebar_container = ft.Container(width=90, height=900, bgcolor=col_white, padding=ft.padding.symmetric(horizontal=15, vertical=20), content=sidebar_column, animate=ft.Animation(300, "easeOut"), shadow=ft.BoxShadow(blur_radius=10, color="#05000000"))

    # --- DASHBOARD İÇERİK ---
    def change_currency(currency_code):
        state["current_currency"] = currency_code
        currency_selector_container.content = create_currency_selector()
        currency_selector_container.update()

    def create_currency_selector():
        curr = state["current_currency"]
        return ft.Container(bgcolor=col_bg, border_radius=12, padding=4, content=ft.Row([currency_button("₺ TRY", "TRY", curr, change_currency), currency_button("$ USD", "USD", curr, change_currency), currency_button("€ EUR", "EUR", curr, change_currency)], spacing=0, tight=True))
    currency_selector_container = ft.Container(content=create_currency_selector())

    # Kur bilgisi text'i dinamik olarak oluştur
    exchange_rate_text = ft.Text(get_exchange_rate_display(), size=13, color=col_text_light, weight="w600")
    
    header = ft.Row([ft.Text("Genel Durum Paneli", size=26, weight="bold", color=col_text), ft.Row([ft.Container(bgcolor="#EAF2F8", padding=ft.padding.symmetric(horizontal=15, vertical=10), border_radius=8, content=ft.Row([ft.Icon("currency_exchange", size=16, color=col_blue_donut), exchange_rate_text], spacing=10)), currency_selector_container], spacing=20)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Backend'den gerçek verileri çek
    def get_dashboard_stats(year=None):
        """Dashboard için istatistikleri hesapla - isteğe bağlı yıl filtresi"""
        try:
            # Giden faturalar (Gelir)
            income_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='outgoing',
                limit=1000,
                offset=0
            ) or []
            
            # Gelen faturalar (Gider)
            expense_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='incoming',
                limit=1000,
                offset=0
            ) or []
            
            # Eğer yıl filtresi varsa, sadece o yıla ait faturaları al
            if year:
                income_invoices = [inv for inv in income_invoices if inv.get('tarih', '').endswith(str(year))]
                expense_invoices = [inv for inv in expense_invoices if inv.get('tarih', '').endswith(str(year))]
            
            # Toplam gelir (TL)
            total_income = sum(float(inv.get('toplam_tutar_tl', 0)) for inv in income_invoices)
            
            # Toplam gider (TL)
            total_expense = sum(float(inv.get('toplam_tutar_tl', 0)) for inv in expense_invoices)
            
            # Genel giderleri ekle
            if year:
                general_expenses = backend_instance.db.get_yearly_expenses(year)
                if general_expenses:
                    month_keys = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
                    for month_key in month_keys:
                        if month_key in general_expenses:
                            total_expense += float(general_expenses[month_key] or 0)
            
            # Net kâr
            net_profit = total_income - total_expense
            
            # Aylık ortalama (son 12 ay gelir ortalaması)
            import datetime
            current_year = datetime.datetime.now().year
            current_month = datetime.datetime.now().month
            
            # Eğer seçili yıl geçmiş yılsa, 12 aya böl
            if year and year < current_year:
                monthly_avg = total_income / 12
            else:
                monthly_avg = total_income / max(current_month, 1)
            
            return {
                'net_profit': net_profit,
                'total_income': total_income,
                'total_expense': total_expense,
                'monthly_avg': monthly_avg,
                'income_count': len(income_invoices),
                'expense_count': len(expense_invoices)
            }
        except Exception as e:
            return {
                'net_profit': 0,
                'total_income': 0,
                'total_expense': 0,
                'monthly_avg': 0,
                'income_count': 0,
                'expense_count': 0
            }
    
    # İstatistikleri al
    stats = get_dashboard_stats()
    
    # Trend hesapla (basit - önceki aya göre %15 artış varsayımı)
    net_profit_trend = "+15%" if stats['net_profit'] > 0 else "0%"
    income_trend = "+4%" if stats['total_income'] > 0 else "0%"
    expense_trend = "-2%" if stats['total_expense'] > 0 else "0%"
    avg_trend = "+1%" if stats['monthly_avg'] > 0 else "0%"
    
    # Her donut için kendi max değerini hesapla (değerin %120'si, min 10K)
    profit_max = max(abs(stats['net_profit']) * 1.2, 10000)
    income_max = max(stats['total_income'] * 1.2, 10000)
    expense_max = max(stats['total_expense'] * 1.2, 10000)
    avg_max = max(stats['monthly_avg'] * 1.2, 10000)
    
    stats_row = ft.Row([
        DonutStatCard("Anlık Net Kâr", "attach_money", col_blue_donut, net_profit_trend, 
                     abs(stats['net_profit']), profit_max, format_currency(stats['net_profit'], compact=True)),
        DonutStatCard("Toplam Gelir", "arrow_upward", col_success, income_trend, 
                     stats['total_income'], income_max, format_currency(stats['total_income'], compact=True)),
        DonutStatCard("Toplam Gider", "arrow_downward", col_secondary, expense_trend, 
                     stats['total_expense'], expense_max, format_currency(stats['total_expense'], compact=True)),
        DonutStatCard("Aylık Ortalama", "pie_chart", "#FF5B5B", avg_trend, 
                     stats['monthly_avg'], avg_max, format_currency(stats['monthly_avg'], compact=True))
    ], spacing=20)
    
    # Son işlemleri backend'den çek
    def get_recent_transactions():
        """Son faturaları getir"""
        try:
            # Hem gelir hem gider faturalarını al
            income_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='outgoing',
                limit=10,
                offset=0,
                order_by='id DESC'
            ) or []
            
            expense_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='incoming',
                limit=10,
                offset=0,
                order_by='id DESC'
            ) or []
            
            # Birleştir ve formatla - ortak fonksiyon kullan
            transactions = []
            transactions.extend(_process_invoices(income_invoices[:5], is_income=True))
            transactions.extend(_process_invoices(expense_invoices[:5], is_income=False))
            
            # Tarihe göre sırala
            transactions.sort(key=lambda x: x['date'], reverse=True)
            return transactions[:8]
            
        except Exception as e:
            return []
    
    def _process_invoices(invoices, is_income):
        """Fatura listesini transaction formatına çevirir - tekrar eden kodu birleştirir"""
        from datetime import datetime
        transactions = []
        
        for inv in invoices:
            # updated_at var mı kontrol et (güncellenmiş fatura)
            is_updated = bool(inv.get('updated_at'))
            
            # İşlem tarihi (created_at) ve fatura tarihi (tarih) farklı olabilir
            operation_date = inv.get('created_at', '')
            invoice_date = inv.get('tarih', '')
            
            # created_at ISO format'ta ise sadece tarihi al
            if operation_date and 'T' in operation_date:
                try:
                    dt = datetime.fromisoformat(operation_date)
                    operation_date = dt.strftime('%d.%m.%Y')
                except:
                    operation_date = invoice_date  # Hata durumunda fatura tarihini kullan
            
            # Eğer işlem tarihi yoksa fatura tarihini kullan
            if not operation_date:
                operation_date = invoice_date
            
            transactions.append({
                'title': inv.get('firma', 'Firma'),
                'display_date': operation_date,
                'invoice_date': invoice_date,
                'amount': f"{float(inv.get('toplam_tutar_tl', 0)):,.2f}",
                'income': is_income,
                'date': operation_date,  # Sıralama için
                'is_updated': is_updated
            })
        
        return transactions
    
    transactions_column = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    current_filter_date = None  # Aktif tarih filtresini sakla

    def update_transactions(filter_date=None):
        """Geçmiş işlemleri günceller - filtre varsa veritabanından çeker"""
        nonlocal current_filter_date
        
        # Eğer parametre verilmediyse, mevcut filtreyi kullan
        if filter_date is None and current_filter_date is not None:
            filter_date = current_filter_date
        else:
            current_filter_date = filter_date
        
        transactions_column.controls.clear()
        filtered_data = []
        
        if filter_date:
            # Tarih filtresi varsa veritabanından o tarihteki faturaları çek
            str_date = filter_date.strftime("%d.%m.%Y")
            
            # Gelir faturalarını çek
            income_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='outgoing'
            ) or []
            
            # Gider faturalarını çek
            expense_invoices = backend_instance.handle_invoice_operation(
                operation='get',
                invoice_type='incoming'
            ) or []
            
            # Seçili tarihe göre filtrele - ortak fonksiyon kullan
            filtered_income = [inv for inv in income_invoices if inv.get('tarih', '') == str_date]
            filtered_expense = [inv for inv in expense_invoices if inv.get('tarih', '') == str_date]
            
            filtered_data.extend(_process_invoices(filtered_income, is_income=True))
            filtered_data.extend(_process_invoices(filtered_expense, is_income=False))
        else:
            # Filtre yoksa son işlemleri yeniden çek (dinamik)
            filtered_data = get_recent_transactions()

        if not filtered_data:
            transactions_column.controls.append(ft.Container(content=ft.Text("Bu tarihte işlem bulunamadı.", color=col_text_light), alignment=ft.alignment.center, padding=20))
        else:
            for t in filtered_data:
                transactions_column.controls.append(
                    TransactionRow(
                        t["title"], 
                        t["display_date"], 
                        t["amount"], 
                        t["income"],
                        is_updated=t.get("is_updated", False),
                        invoice_date=t.get("invoice_date")
                    )
                )
        
        try:
            if transactions_column.page: 
                transactions_column.update()
        except:
            pass

    update_transactions()

    def handle_date_change(e):
        if e.control.value: update_transactions(e.control.value)

    date_picker = ft.DatePicker(on_change=handle_date_change, cancel_text="İptal", confirm_text="Seç", help_text="İşlem Tarihini Seçin")
    page.overlay.append(date_picker)

    def reset_transactions(e): update_transactions(None)

    transactions_list_content = ft.Column([ft.Row([ft.Text("Son İşlemler", size=18, weight="bold", color=col_text), ft.Row([ft.IconButton(icon="calendar_month", icon_color=col_text_light, tooltip="Tarihe Göre Git", on_click=lambda _: setattr(date_picker, 'open', True) or page.update()), ft.TextButton("En Son Girilenler", style=ft.ButtonStyle(color=col_primary), on_click=reset_transactions)])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=15), transactions_column], spacing=5)

    transactions_list = ft.Container(bgcolor=col_white, border_radius=20, padding=25, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450, content=transactions_list_content)

    # Yıl dropdown'ı için dinamik seçenekler oluştur - tüm veritabanı yıllarını çek
    available_years = get_all_available_years()
    year_dropdown_options = [ft.dropdown.Option(str(year)) for year in available_years]
    default_year = str(available_years[0]) if available_years else str(datetime.now().year)
    
    # Dropdown'ı değişkene ata (refresh fonksiyonunda kullanmak için)
    year_dropdown_ref = ft.Dropdown(width=100, options=year_dropdown_options, value=default_year, on_change=on_year_change, border_radius=10, text_size=13, content_padding=10)
    
    chart_container = ft.Container(bgcolor=col_white, border_radius=20, padding=ft.padding.only(left=30, right=30, top=30, bottom=10), expand=2, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450, content=ft.Column([ft.Row([ft.Column([ft.Text("Performans Analizi", size=20, weight="bold", color=col_text), ft.Text("Yıllık gelir ve gider karşılaştırması", size=13, color=col_text_light)]), year_dropdown_ref], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=20), ft.Container(content=line_chart, expand=True), ft.Row([ft.Row([ft.Container(width=10, height=10, bgcolor=col_primary, border_radius=2), ft.Text("Gelir", size=12, color="grey")], spacing=5), ft.Row([ft.Container(width=10, height=10, bgcolor=col_secondary, border_radius=2), ft.Text("Gider", size=12, color="grey")], spacing=5)], alignment=ft.MainAxisAlignment.CENTER)]))

    dashboard_layout = ft.Column([header, ft.Container(height=10), stats_row, ft.Container(height=10), ft.Row([chart_container, ft.Container(content=transactions_list, expand=1)], expand=True, spacing=20)], spacing=10)

    dashboard_content.content = dashboard_layout
    content_area = ft.Container(expand=True, padding=30, content=dashboard_content)

    layout = ft.Row([sidebar_container, content_area], expand=True, spacing=0)
    page.add(layout)
    
    def start_animations():
        time.sleep(0.5) 
        for donut in state["donuts"]: donut.start_animation()
        # İlk yüklemede varsayılan yılı çiz
        if available_years:
            first_year = available_years[0]
            draw_snake_chart(first_year)
        
        # Animasyonlar başladıktan sonra callback'leri kaydet
        time.sleep(0.3)  # Animasyonların tamamlanmasını bekle
        
        # Ana sayfa için birleşik callback - hem grafikler hem işlem geçmişi
        def home_page_full_update():
            refresh_charts_and_data()
            update_transactions()  # İşlem geçmişini de güncelle
        
        state["update_callbacks"]["home_page"] = home_page_full_update

    threading.Thread(target=start_animations, daemon=True).start()

ft.app(target=main)


