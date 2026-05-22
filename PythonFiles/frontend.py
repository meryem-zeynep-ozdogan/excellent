# ruff: noqa: E402
# Frontend.py - Flet Arayüzü
# -*- coding: utf-8 -*-
"""
KULLANICI ARAYÜZÜ (UI) MODÜLÜ

Bu modül, Flet kütüphanesi kullanılarak oluşturulan modern ve responsive
kullanıcı arayüzünü içerir. Backend ile asenkron olarak haberleşir.
"""

# Merkezi imports'tan gerekli kütüphaneleri al
from imports import (
    ft,
    datetime,
    time,
    threading,
    os,
    sys,
    socket,
    win32event,
    win32api,
    winerror,
    ctypes,
    traceback,
)

# Define project root
# Veritabanı ve çıktı (Excel, PDF vb.) dosyalarının ana dizini
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Uygulamanın çalışma dizinini PROJECT_ROOT olarak ayarla
# Bu, PyInstaller ile derlendiğinde (.exe konumunda) veya temp olarak çalıştığında
# Rust_DB ve diğer tüm bağlı göreceli yolların geçici MEIPASS yerine .exe klasörüne (.db vb.) kurulmasını sağlar.
os.chdir(PROJECT_ROOT)

# Windows görev çubuğu simgesi için AppUserModelID ayarla (en başta yapılmalı)
try:
    myappid = "excellent.dashboard.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# Backend modüllerini import et
from backend import Backend
from locales import get_text

# Tek instance kontrolü (Uygulamanın ikinci kez açılmasını engeller)
mutex = win32event.CreateMutex(None, False, "Global\\ExcellentMVPSingleInstance")
last_error = win32api.GetLastError()

if last_error == winerror.ERROR_ALREADY_EXISTS:
    # Uygulama zaten çalışıyor
    ctypes.windll.user32.MessageBoxW(
        0, "Excellent uygulaması zaten çalışıyor!", "Uyarı", 0x30
    )
    sys.exit(0)

# Backend instance oluştur (Tüm uygulama boyunca tek bir instance kullanılır)
backend_instance = Backend()


# Backend callback'lerini ayarla (Flet uyumlu)
def on_backend_data_updated():
    """
    Backend'den veri güncellendiğinde (örn: yeni fatura eklendiğinde)
    tüm sayfalardaki ilgili bileşenleri (tablolar, grafikler) günceller.
    """
    try:
        # Tüm kayıtlı callback'leri çağır
        for page_name, callback in state["update_callbacks"].items():
            if callback is not None:
                try:
                    callback()
                except Exception:
                    pass
    except Exception:
        pass


def on_backend_status_updated(message, duration):
    """Backend'den status mesajı geldiğinde çağrılır"""
    warning_widget = state.get("internet_warning")
    if warning_widget is None:
        return
    try:
        is_internet_down = any(w in message.lower() for w in ["bağlantı", "varsayılan", "önceki gün", "kaydedilen"])
        warning_widget.visible = is_internet_down
        warning_widget.update()
    except Exception:
        pass


backend_instance.on_data_updated = on_backend_data_updated
backend_instance.on_status_updated = on_backend_status_updated

# ============================================================================
# RENK PALETİ (Modern Dashboard Teması)
# ============================================================================

col_primary = "#6C5DD3"  # Mor (Ana aksiyon rengi)
col_secondary = "#FF9F43"  # Turuncu (İkincil vurgular)
col_success = "#4CD964"  # Yeşil (Başarılı işlemler, gelirler)
col_danger = "#FF3B30"  # Kırmızı (Hatalar, giderler)
col_bg = "#F4F5FA"  # Arka Plan (Açık gri)
col_white = "#FFFFFF"  # Beyaz (Kartlar ve paneller)
col_text = "#1A1D1F"  # Koyu Metin (Başlıklar)
col_text_light = "#9AA1B9"  # Gri Metin (Açıklamalar)
col_blue_donut = "#2D9CDB"
col_border = "#E6E8EC"
col_table_header_bg = "#5A5278"
col_selected_row = "#E8F5E9"
col_input_bg = "#FFFFFF"
col_text_secondary = "#6B7280"
col_card = "#FFFFFF"


def create_styled_icon_button(icon, color, tooltip, on_click):
    return ScaleButton(
        icon=icon,
        color=color,
        tooltip_text=tooltip,
        width=42,
        height=42,
        on_click=on_click,
    )


# Şeffaf Renkler (Grafik ve efektler için)
col_primary_50 = "#806C5DD3"
col_secondary_50 = "#80FF9F43"
transparent_white = "#00FFFFFF"
tooltip_bg = "inverseSurface"

# ============================================================================
# GLOBAL DURUM (STATE)
# ============================================================================

# Uygulama genelinde paylaşılan veriler
state = {
    "sidebar_expanded": False,
    "current_currency": "TRY",
    "donuts": [],
    "invoice_type": "income",
    "selected_row": None,
    "current_page": "home",
    "invoice_sort_option": "newest",
    "animation_completed": False,
    "editing_invoice_id": None,
    "current_language": "tr",
    "excel_export_path": os.path.join(PROJECT_ROOT, "ExcelReports"),
    "pdf_export_path": os.path.join(PROJECT_ROOT, "PDFExports"),
    # Dinamik güncelleme için referanslar (Sayfalar arası iletişim)
    "update_callbacks": {
        "home_page": None,
        "donemsel_page": None,
        "invoice_page": None,
        "general_expenses": None,
        "transaction_history": None,
    },
}


def tr(key):
    """Mevcut duruma göre çevrilmiş metni almak için yardımcı fonksiyon"""
    return get_text(key, state.get("current_language", "tr"))


# ============================================================================
# BACKEND YARDIMCI FONKSİYONLAR
# ============================================================================


def resource_path(relative_path):
    """Kaynağa mutlak yolu al, geliştirme ve PyInstaller için çalışır"""
    try:
        # PyInstaller geçici bir klasör oluşturur ve yolu _MEIPASS içinde saklar
        base_path = sys._MEIPASS
    except Exception:
        # PythonFiles klasöründen bir üst dizine (root) çık
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)


def get_exchange_rates():
    """Backend'den güncel döviz kurlarını al"""
    return backend_instance.exchange_rates


def convert_currency(amount, from_currency, to_currency):
    """Para birimi dönüşümü yap"""
    return backend_instance.convert_currency(amount, from_currency, to_currency)


def process_invoice(invoice_data):
    """Fatura verilerini işle ve KDV hesapla"""
    return backend_instance.invoice_processor.process_invoice_data(invoice_data)


def format_currency(amount, currency="TRY", compact=False, target_currency=None):
    """Para birimi formatla - compact=True ise K/M formatında göster

    Args:
        amount: Tutar
        currency: Tutarın mevcut birimi (TL/TRY, USD, EUR)
        compact: True ise K/M formatında göster
        target_currency: Hedef birim (None ise currency kullanılır, dönüşüm yapar)
    """
    # Currency normalizasyonu
    if currency == "TL":
        currency = "TRY"
    if target_currency == "TL":
        target_currency = "TRY"

    # Hedef birim belirtilmemişse kaynak birimle aynı
    if target_currency is None:
        target_currency = currency

    # Döviz dönüştürme
    converted_amount = amount
    if currency != target_currency:
        rates = get_exchange_rates()

        # TL'den hedef birime
        if currency == "TRY":
            if target_currency == "USD":
                converted_amount = amount * rates.get("USD", 1)
            elif target_currency == "EUR":
                converted_amount = amount * rates.get("EUR", 1)
        # USD'den
        elif currency == "USD":
            if target_currency == "TRY":
                converted_amount = (
                    amount / rates.get("USD", 1) if rates.get("USD", 0) > 0 else amount
                )
            elif target_currency == "EUR":
                usd_to_tl = (
                    amount / rates.get("USD", 1) if rates.get("USD", 0) > 0 else amount
                )
                converted_amount = usd_to_tl * rates.get("EUR", 1)
        # EUR'den
        elif currency == "EUR":
            if target_currency == "TRY":
                converted_amount = (
                    amount / rates.get("EUR", 1) if rates.get("EUR", 0) > 0 else amount
                )
            elif target_currency == "USD":
                eur_to_tl = (
                    amount / rates.get("EUR", 1) if rates.get("EUR", 0) > 0 else amount
                )
                converted_amount = eur_to_tl * rates.get("USD", 1)

    # Sembol belirleme
    symbol = "₺"
    if target_currency == "USD":
        symbol = "$"
    elif target_currency == "EUR":
        symbol = "€"

    if compact:
        # Kompakt format (K/M ile)
        if converted_amount >= 1000000:
            return f"{symbol} {converted_amount / 1000000:.1f}M"
        elif converted_amount >= 1000:
            return f"{symbol} {converted_amount / 1000:.1f}K"
        else:
            return f"{symbol} {converted_amount:.0f}"

    # Normal format - büyük sayılar için binlik ayracı
    if target_currency == "TRY":
        return f"{converted_amount:,.2f} ₺"
    elif target_currency == "USD":
        return f"${converted_amount:,.2f}"
    elif target_currency == "EUR":
        return f"€{converted_amount:,.2f}"
    return f"{converted_amount:,.2f} {target_currency}"


def get_exchange_rate_display():
    """Kur bilgilerini string olarak döndür"""
    rates = get_exchange_rates()
    usd_rate = rates.get("USD", 0)
    eur_rate = rates.get("EUR", 0)

    if usd_rate > 0 and eur_rate > 0:
        usd_tl = 1 / usd_rate
        eur_tl = 1 / eur_rate
        return f"1 USD = {usd_tl:.2f} TL | 1 EUR = {eur_tl:.2f} TL"
    return "Kur bilgisi yükleniyor..."


# ============================================================================
# YARDIMCI BİLEŞENLER
# ============================================================================


class ScaleButton(ft.Container):
    def __init__(self, icon, color, tooltip_text, width=35, height=35, on_click=None):
        super().__init__()
        self.bgcolor = color
        self.border_radius = 8
        self.border = ft.border.all(1, "#22FFFFFF")
        self.width = width
        self.height = height
        self.tooltip = (
            ft.Tooltip(
                message=tooltip_text,
                wait_duration=0,
                show_duration=4000,
                bgcolor=tooltip_bg,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                prefer_below=False,
            )
            if tooltip_text
            else None
        )
        self.alignment = ft.alignment.center
        self.animate_scale = ft.Animation(200, ft.AnimationCurve.EASE_OUT_BACK)
        self.animate = ft.Animation(200, "easeOut")
        self.ink = True
        self._user_on_click = on_click

        hex_code = color.lstrip("#")
        shadow_color = f"#80{hex_code}"
        self.shadow = ft.BoxShadow(
            blur_radius=10, color=shadow_color, offset=ft.Offset(0, 4)
        )
        self.content = ft.Icon(icon, color=col_white, size=18)
        self.on_hover = self.hover_effect
        self.on_click = self.click_effect
        self.scale = 1.0

    def reset_visual_state(self):
        self.scale = 1.0
        self.shadow.blur_radius = 10
        self.shadow.offset = ft.Offset(0, 4)
        self.border = ft.border.all(1, "#22FFFFFF")
        self.update()

    def hover_effect(self, e):
        if e.data == "true":
            self.scale = 1.18
            self.shadow.blur_radius = 22
            self.shadow.offset = ft.Offset(0, 8)
            self.border = ft.border.all(1, "#55FFFFFF")
        else:
            self.scale = 1.0
            self.shadow.blur_radius = 10
            self.shadow.offset = ft.Offset(0, 4)
            self.border = ft.border.all(1, "#22FFFFFF")
        self.update()

    def click_effect(self, e):
        self.reset_visual_state()
        if self._user_on_click:
            self._user_on_click(e)


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
        self.shadow = ft.BoxShadow(
            blur_radius=8, color=f"#4D{hex_code}", offset=ft.Offset(0, 3)
        )

        self.content = ft.Row(
            [
                ft.Icon(icon, color=col_white, size=18),
                ft.Text(text, color=col_white, weight="bold", size=12),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=5,
        )
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


def format_date_input(date_str):
    """
    Esnek tarih girişini standart formata (gg.aa.yyyy) çevirir.
    Desteklenen formatlar:
    - 121225 -> 12.12.2025 (ggaayy)
    - 12122025 -> 12.12.2025 (ggaayyyy)
    - 12.12.2025, 12/12/2025, 12-12-2025 (ayırıcılı formatlar)
    """
    if not date_str or not isinstance(date_str, str):
        return date_str

    date_str = date_str.strip()

    # Sadece rakamları al
    cleaned = "".join(c for c in date_str if c.isdigit())

    # 6 karakterlik format: ggaayy -> gg.aa.20yy
    if len(cleaned) == 6:
        gun = cleaned[:2]
        ay = cleaned[2:4]
        yil_short = cleaned[4:6]
        yil = "20" + yil_short
        try:
            # Geçerli tarih mi kontrol et
            datetime(int(yil), int(ay), int(gun))
            return f"{gun}.{ay}.{yil}"
        except ValueError:
            return date_str

    # 8 karakterlik format: ggaayyyy -> gg.aa.yyyy
    elif len(cleaned) == 8:
        # İlk 4 karakter yıl gibi görünüyorsa (2000-2099 arası)
        if cleaned[:4].startswith("20"):
            # yyyyaagg formatı
            yil = cleaned[:4]
            ay = cleaned[4:6]
            gun = cleaned[6:8]
        else:
            # ggaayyyy formatı
            gun = cleaned[:2]
            ay = cleaned[2:4]
            yil = cleaned[4:8]
        try:
            datetime(int(yil), int(ay), int(gun))
            return f"{gun}.{ay}.{yil}"
        except ValueError:
            return date_str

    # Zaten formatlanmış veya ayırıcı içeren tarihler
    for sep in [".", "/", "-"]:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    gun, ay, yil = parts
                    # 2 basamaklı yıl ise 20xx'e çevir
                    if len(yil) == 2:
                        yil = "20" + yil
                    datetime(int(yil), int(ay), int(gun))
                    return f"{gun.zfill(2)}.{ay.zfill(2)}.{yil}"
                except (ValueError, TypeError):
                    pass

    return date_str


def create_vertical_input(
    label, hint, width=None, expand=True, is_dropdown=False, dropdown_options=None
):
    if is_dropdown:
        input_control = ft.Dropdown(
            options=[ft.dropdown.Option(opt) for opt in dropdown_options]
            if dropdown_options
            else [],
            text_size=13,
            color="onBackground",
            border_color="transparent",
            bgcolor="transparent",
            content_padding=ft.padding.only(left=10, bottom=5),
            hint_text=hint,
            hint_style=ft.TextStyle(color="onSurfaceVariant", size=12),
        )
    else:
        input_control = ft.TextField(
            hint_text=hint,
            hint_style=ft.TextStyle(color="onSurfaceVariant", size=12),
            text_size=13,
            color="onBackground",
            border_color="transparent",
            bgcolor="transparent",
            content_padding=ft.padding.only(left=10, bottom=12),
        )

    return ft.Column(
        [
            ft.Text(label, size=12, color="onSurfaceVariant", weight="bold"),
            ft.Container(
                content=input_control,
                bgcolor="surface",
                border=ft.border.all(1, "outline"),
                border_radius=8,
                height=38,
                width=width,
            ),
        ],
        spacing=3,
        expand=expand,
    )


# --- FATURA VERİSİ ---
# Frontend sample invoice data removed to avoid embedded backend/test scaffolding.
# Integrate a backend data source and supply rows dynamically when ready.


# ============================================================================
# FATURA TABLOSU OLUŞTURMA
# ============================================================================
def create_invoice_table_content(
    sort_option="newest",
    invoice_type="income",
    on_select_changed=None,
    invoice_list=None,
    theme_mode=None,
    container_width=None,
    limit=100,
    offset=0,
):
    """Backend'den fatura verilerini çekerek DataTable oluşturur."""
    _CHECKBOX_W = 18
    _N_COLS = 9
    _COLUMN_SPACING = 4
    _SPACING_TOTAL = (_N_COLS - 1) * _COLUMN_SPACING
    _PADDING = 10
    _VAT_EXTRA_W = 58
    if container_width and container_width > 400:
        COL_W = max(
            76,
            int(
                (
                    container_width
                    - _CHECKBOX_W
                    - _SPACING_TOTAL
                    - _PADDING
                    - _VAT_EXTRA_W
                )
                / _N_COLS
            ),
        )
    else:
        COL_W = 124
    VAT_COL_W = COL_W + _VAT_EXTRA_W
    ROW_H = 56
    ROW_MAX_H = 96
    vert_color = "#40FFFFFF" if theme_mode == ft.ThemeMode.DARK else "#28000000"

    def header(t, numeric=False, size=12, width=None):
        return ft.DataColumn(
            ft.Container(
                content=ft.Text(t, weight="bold", color=col_white, size=size, no_wrap=True),
                width=width or COL_W,
                alignment=ft.alignment.center_right if numeric else ft.alignment.center_left,
            ),
            numeric=numeric,
        )

    # Backend'den faturaları çek (eğer liste verilmediyse)
    rows = []
    invoices = invoice_list  # Liste cache'i için

    try:
        if invoices is None:
            # invoice_type'a göre doğru veritabanını belirle
            db_type = "outgoing" if invoice_type == "income" else "incoming"

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
                operation="get",
                invoice_type=db_type,
                limit=limit,
                offset=offset,
                order_by=order_by,
            )

        # DataTable satırlarını oluştur
        if invoices:
            for inv in invoices:

                def cell(text, color="onBackground", width=None, wrap=False):
                    return ft.DataCell(
                        ft.Container(
                            content=ft.Text(
                                str(text),
                                size=12,
                                color=color,
                                overflow=ft.TextOverflow.CLIP if wrap else ft.TextOverflow.ELLIPSIS,
                                max_lines=3 if wrap else 1,
                                no_wrap=not wrap,
                            ),
                            width=width or COL_W,
                            height=None if wrap else ROW_H,
                            padding=ft.padding.symmetric(vertical=8),
                            alignment=ft.alignment.center_left,
                            border=ft.border.only(right=ft.border.BorderSide(1, vert_color)),
                        )
                    )

                # Checkbox hücresi - manuel seçim için
                checkbox = ft.Checkbox(
                    value=False,
                    on_change=on_select_changed if on_select_changed else None,
                )
                checkbox_cell = ft.DataCell(
                    ft.Container(
                        content=ft.Container(content=checkbox, scale=0.82),
                        width=_CHECKBOX_W,
                        alignment=ft.alignment.center_left,
                        padding=0,
                    )
                )

                # Kur bilgilerini al (None kontrolü yap)
                usd_rate = inv.get("usd_rate")
                eur_rate = inv.get("eur_rate")

                usd_rate_val = float(usd_rate) if usd_rate is not None else 0.0
                eur_rate_val = float(eur_rate) if eur_rate is not None else 0.0

                # KDV hesaplama
                kdv_tutari = float(inv.get("kdv_tutari", 0))
                kdv_yuzdesi = float(inv.get("kdv_yuzdesi", 0))
                kdv_text = f"{kdv_tutari:,.2f} (%{kdv_yuzdesi:.0f})"

                # Matrah (Base Amount) hesaplama
                matrah = float(inv.get("matrah", 0) or 0)
                toplam_tl = float(inv.get("toplam_tutar_tl", 0) or 0)

                # Eski kayıtlar için fallback: Matrah yoksa Toplam - KDV
                if matrah <= 0 and toplam_tl > 0:
                    matrah = toplam_tl - kdv_tutari

                # Döviz bazlı matrah hesaplama
                base_usd = 0.0
                if usd_rate_val > 0:
                    base_usd = matrah / usd_rate_val

                base_eur = 0.0
                if eur_rate_val > 0:
                    base_eur = matrah / eur_rate_val

                usd_display = f"{base_usd:,.2f}"
                eur_display = f"{base_eur:,.2f}"

                def create_currency_cell(amount_text, rate_val, width=None):
                    if rate_val > 0:
                        return ft.DataCell(
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(amount_text, size=12, color="onBackground", weight="bold"),
                                        ft.Text(tr("rate_label").format(rate_val), size=10, color="onSurfaceVariant"),
                                    ],
                                    spacing=2,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.START,
                                ),
                                width=width or COL_W,
                                height=ROW_H,
                                alignment=ft.alignment.center_left,
                                border=ft.border.only(right=ft.border.BorderSide(1, vert_color)),
                            )
                        )
                    return ft.DataCell(
                        ft.Container(
                            content=ft.Text(amount_text, size=12, color="onBackground"),
                            width=width or COL_W,
                            height=ROW_H,
                            alignment=ft.alignment.center_left,
                            border=ft.border.only(right=ft.border.BorderSide(1, vert_color)),
                        )
                    )

                # Her satıra invoice verilerini data olarak ekle
                row = ft.DataRow(
                    data=inv,  # Tüm invoice verisini data olarak sakla
                    cells=[
                        checkbox_cell,  # İlk hücre checkbox
                        cell(inv.get("fatura_no", "")),
                        cell(inv.get("tarih", "")),
                        cell(inv.get("firma", ""), wrap=True),
                        cell(inv.get("malzeme", ""), wrap=True),
                        cell(inv.get("miktar", ""), wrap=True),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"{matrah:,.2f}", size=12, color="onBackground", weight="bold"),
                                width=COL_W,
                                height=ROW_H,
                                alignment=ft.alignment.center_left,
                                border=ft.border.only(right=ft.border.BorderSide(1, vert_color)),
                            )
                        ),
                        create_currency_cell(usd_display, usd_rate_val),
                        create_currency_cell(eur_display, eur_rate_val),
                        cell(kdv_text, width=VAT_COL_W, wrap=True),
                    ],
                )
                rows.append(row)
    except Exception:
        pass

    # Select All Checkbox Logic
    def on_select_all(e):
        is_selected = e.control.value
        for row in table.rows:
            if len(row.cells) > 0:
                try:
                    cb = row.cells[0].content.content.content
                    if isinstance(cb, ft.Checkbox):
                        cb.value = is_selected
                except (AttributeError, TypeError):
                    pass

        if on_select_changed:
            on_select_changed(e)

        table.update()

    select_all_checkbox = ft.Checkbox(
        value=False,
        on_change=on_select_all,
        fill_color=col_white,
        check_color=col_primary,
    )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(
                ft.Container(
                    content=ft.Container(content=select_all_checkbox, scale=0.82),
                    width=_CHECKBOX_W,
                    alignment=ft.alignment.center_left,
                    padding=0,
                )
            ),
            header(tr("col_invoice_no")),
            header(tr("col_date")),
            header(tr("col_company")),
            header(tr("col_item")),
            header(tr("col_amount")),
            header(tr("col_total_tl")),
            header(tr("col_total_usd")),
            header(tr("col_total_eur")),
            header(tr("col_vat"), size=12, width=VAT_COL_W),
        ],
        rows=rows,
        heading_row_color=col_table_header_bg,
        heading_row_height=42,
        data_row_min_height=56,
        data_row_max_height=ROW_MAX_H,
        vertical_lines=ft.border.BorderSide(0, "transparent"),
        horizontal_lines=ft.border.BorderSide(1, "#28808080"),
        column_spacing=_COLUMN_SPACING,
        horizontal_margin=0,
        checkbox_horizontal_margin=0,
        expand=True,
    )

    # Tablo boşsa başlıkları göster + boş durum mesajı altta
    if not rows:
        return ft.Column(
            [
                table,
                ft.Container(
                    height=220,
                    padding=ft.padding.only(top=18, bottom=26),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=56, color="onSurfaceVariant"),
                            ft.Text(
                                tr("table_empty_title"),
                                size=15,
                                weight="bold",
                                color="onSurfaceVariant",
                            ),

                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ),
            ],
            data={"row_count": 0},
            expand=True,
            spacing=0,
        )

    table.data = {"row_count": len(rows)}
    return table


# ============================================================================
# DÖNEMSEL TABLO OLUŞTURMA
# ============================================================================
def create_donemsel_table(year=None, tax_fields=None, on_tax_change=None):
    """Dönemsel gelir/gider tablosu - Gerçek verilerle dolu"""
    if year is None:
        year = datetime.now().year

    months = [
        tr("month_jan"),
        tr("month_feb"),
        tr("month_mar"),
        tr("month_apr"),
        tr("month_may"),
        tr("month_jun"),
        tr("month_jul"),
        tr("month_aug"),
        tr("month_sep"),
        tr("month_oct"),
        tr("month_nov"),
        tr("month_dec"),
    ]
    quarter_colors = [col_danger, col_success, col_secondary, col_blue_donut]

    def header(t):
        return ft.DataColumn(
            ft.Text(t, weight="bold", color="onPrimaryContainer", size=12)
        )

    def cell(t):
        return ft.DataCell(ft.Text(t, color="onSurface", size=12))

    # Backend'den verileri çek
    try:
        income_invoices = (
            backend_instance.handle_invoice_operation("get", "outgoing") or []
        )
        expense_invoices = (
            backend_instance.handle_invoice_operation("get", "incoming") or []
        )

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
            tarih = invoice.get("tarih", "")
            if not tarih:
                continue

            parts = tarih.split(".")
            if len(parts) != 3:
                continue

            try:
                month = int(parts[1])
                invoice_year = int(parts[2])

                if invoice_year == year:
                    amount_tl = float(invoice.get("toplam_tutar_tl", 0))
                    kdv_tl = float(invoice.get("kdv_tutari", 0))
                    monthly_income[month - 1] += amount_tl
                    monthly_income_kdv[month - 1] += kdv_tl
            except (ValueError, IndexError):
                continue

        # Gider faturalarını işle
        for invoice in expense_invoices:
            tarih = invoice.get("tarih", "")
            if not tarih:
                continue

            parts = tarih.split(".")
            if len(parts) != 3:
                continue

            try:
                month = int(parts[1])
                invoice_year = int(parts[2])

                if invoice_year == year:
                    amount_tl = float(invoice.get("toplam_tutar_tl", 0))
                    kdv_tl = float(invoice.get("kdv_tutari", 0))
                    monthly_expense[month - 1] += amount_tl
                    monthly_expense_kdv[month - 1] += kdv_tl
            except (ValueError, IndexError):
                continue

        # Genel giderleri ay ay ekle
        month_keys = [
            "ocak",
            "subat",
            "mart",
            "nisan",
            "mayis",
            "haziran",
            "temmuz",
            "agustos",
            "eylul",
            "ekim",
            "kasim",
            "aralik",
        ]
        for month_idx in range(12):
            month_key = month_keys[month_idx]
            if month_key in general_expenses:
                monthly_general[month_idx] = float(general_expenses[month_key] or 0)
            if month_key in corporate_tax_data:
                monthly_corporate_tax[month_idx] = float(
                    corporate_tax_data[month_key] or 0
                )

        # --- TABLO OLUŞTURMA (YENİ TASARIM - 3 AYLIK GRUPLAMA) ---

        # Sütun Genişlikleri
        w_donem = 90
        w_gelir = 140
        w_gider = 140
        w_kdv_farki = 120
        w_kurumlar = 140

        # Header
        header_row = ft.Container(
            bgcolor="primaryContainer",
            padding=ft.padding.symmetric(vertical=12, horizontal=8), # Padding eklendi hizalama için
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
            content=ft.Row(
                [
                    ft.Container(
                        width=w_donem,
                        padding=ft.padding.only(left=8),
                        content=ft.Text(
                            tr("col_period"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                        ),
                    ),
                    ft.Container(
                        width=w_gelir,
                        content=ft.Text(
                            tr("col_income_billed"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                        ),
                    ),
                    ft.Container(
                        width=w_gider,
                        content=ft.Text(
                            tr("col_expense_total"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                        ),
                    ),
                    ft.Container(
                        width=w_kdv_farki,
                        alignment=ft.alignment.center,
                        content=ft.Text(
                            tr("col_vat_diff"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                        ),
                    ),
                    ft.Container(
                        width=w_kurumlar,
                        content=ft.Text(
                            tr("col_corp_tax"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Text(
                            tr("col_tax_payable"),
                            weight="bold",
                            color="onPrimaryContainer",
                            size=11,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ),
                ],
                spacing=8,
            ),
        )

        quarter_blocks = []

        total_income = 0.0
        total_expense = 0.0
        total_general = 0.0
        total_income_kdv = 0.0
        total_expense_kdv = 0.0
        total_kurumlar_vergisi = 0.0

        # 4 Çeyrek Döngüsü
        for q in range(4):
            start_month = q * 3
            quarter_kurumlar_total = 0.0  # Çeyrek Kurumlar Vergisi toplamı

            left_rows = []

            # Çeyrek içindeki 3 ay
            for i in range(start_month, start_month + 3):
                m = months[i]
                current_color = quarter_colors[q]

                income = monthly_income[i]
                expense = monthly_expense[i]
                general = monthly_general[i]
                income_kdv = monthly_income_kdv[i]
                expense_kdv = monthly_expense_kdv[i]

                tax_percentage = monthly_corporate_tax[i]
                total_month_expense = expense + general

                # Kurumlar vergisi: Gelir - Gider üzerinden hesaplanır
                # Negatif değerler de gösterilir (zarar durumu)
                taxable_base = income - total_month_expense
                kurumlar_vergisi = (
                    (taxable_base * tax_percentage / 100) if tax_percentage > 0 else 0
                )

                # Toplamları güncelle
                total_income += income
                total_expense += total_month_expense
                total_general += general
                total_income_kdv += income_kdv
                total_expense_kdv += expense_kdv
                total_kurumlar_vergisi += kurumlar_vergisi

                # Çeyrek içindeki kurumlar vergisi toplamını güncelle
                quarter_kurumlar_total += kurumlar_vergisi

                # Sol taraf satırı (Ay detayları)
                month_cell = ft.Container(
                    width=w_donem,
                    content=ft.Text(m, color=current_color, weight="bold", size=12),
                    padding=ft.padding.only(left=8),
                    border=ft.border.only(left=ft.border.BorderSide(3, current_color)),
                    alignment=ft.alignment.center_left,
                )

                # Gelir bölümü: Tutar ve altında KDV
                gelir_content = ft.Column(
                    [
                        ft.Text(
                            f"{income:,.2f} TL",
                            size=12,
                            color="onSurface",
                            weight="bold",
                        ),
                        ft.Text(
                            f"{tr('vat_label')}: {income_kdv:,.2f} TL",
                            size=9,
                            color="onSurfaceVariant",
                        ),
                    ],
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                )

                # Gider bölümü: Tutar ve altında KDV
                gider_content = ft.Column(
                    [
                        ft.Text(
                            f"{total_month_expense:,.2f} TL",
                            size=12,
                            color="onSurface",
                            weight="bold",
                        ),
                        ft.Text(
                            f"{tr('vat_label')}: {expense_kdv:,.2f} TL",
                            size=9,
                            color="onSurfaceVariant",
                        ),
                    ],
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                )

                # KDV Farkı hesapla (Gelir KDV - Gider KDV)
                kdv_farki = income_kdv - expense_kdv
                kdv_farki_color = "#28a745" if kdv_farki >= 0 else "#dc3545"
                kdv_farki_content = ft.Text(
                    f"{kdv_farki:,.2f} TL",
                    size=12,
                    color=kdv_farki_color,
                    weight="bold",
                )

                # Kurumlar vergisi bölümü: Sadece TextField (yüzde girişi)
                if tax_fields and i < len(tax_fields):
                    kurumlar_content = tax_fields[i]
                else:
                    kurumlar_content = ft.Text(
                        f"%{tax_percentage:.0f}" if tax_percentage > 0 else "-",
                        size=12,
                        color="onSurface",
                    )

                row = ft.Container(
                    height=48,  # Satır yüksekliği normale döndü
                    padding=ft.padding.symmetric(vertical=5),
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, "outlineVariant")
                    )
                    if i % 3 != 2
                    else None,
                    content=ft.Row(
                        [
                            month_cell,
                            ft.Container(width=w_gelir, content=gelir_content),
                            ft.Container(width=w_gider, content=gider_content),
                            ft.Container(
                                width=w_kdv_farki,
                                content=kdv_farki_content,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(
                                width=w_kurumlar,
                                content=kurumlar_content,
                                alignment=ft.alignment.center,
                            ),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                )
                left_rows.append(row)

            # Sol Kolon (3 Satır)
            left_column = ft.Column(left_rows, spacing=0)

            # Sağ Kolon (Tek Büyük Hücre) - Kurumlar Vergisi toplamı gösterilir
            quarter_color = "#28a745" if quarter_kurumlar_total >= 0 else "#dc3545"
            right_cell = ft.Container(
                expand=True,
                height=144,  # 3 * 48 (satır yüksekliği güncellendi)
                content=ft.Column(
                    [
                        ft.Text(
                            tr("quarter_total"),
                            size=10,
                            color="onSurfaceVariant",
                            weight="bold",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            f"{quarter_kurumlar_total:,.2f} TL",
                            size=16,
                            weight="bold",
                            color=quarter_color,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                border=ft.border.only(left=ft.border.BorderSide(1, "outline")),
                bgcolor="surfaceContainerHighest",
            )

            # Çeyrek Bloğu
            quarter_block = ft.Container(
                content=ft.Row([left_column, right_cell], spacing=10),
                border=ft.border.all(1, "outline"),
                border_radius=8,
                margin=ft.margin.only(bottom=10),
                bgcolor="surface",
                padding=8, # Padding eklendi
            )
            quarter_blocks.append(quarter_block)

        return ft.Column([header_row] + quarter_blocks)

    except Exception:
        return ft.Text(tr("error_loading_data"))


# ============================================================================
# GENEL GİDERLER TABLOSU (General Expenses Grid)
# ============================================================================
def create_grid_expenses(page):
    months = [
        tr("month_jan"),
        tr("month_feb"),
        tr("month_mar"),
        tr("month_apr"),
        tr("month_may"),
        tr("month_jun"),
        tr("month_jul"),
        tr("month_aug"),
        tr("month_sep"),
        tr("month_oct"),
        tr("month_nov"),
        tr("month_dec"),
    ]
    month_keys = [
        "ocak",
        "subat",
        "mart",
        "nisan",
        "mayis",
        "haziran",
        "temmuz",
        "agustos",
        "eylul",
        "ekim",
        "kasim",
        "aralik",
    ]

    # Yıl seçenekleri
    current_year = datetime.now().year
    year_options = [
        ft.dropdown.Option(str(y)) for y in range(current_year - 2, current_year + 2)
    ]

    year_dropdown = ft.Dropdown(
        options=year_options,
        value=str(current_year),
        text_size=12,
        content_padding=10,
        width=95,
        bgcolor="surface",
        border_color="outline",
        border_radius=8,
    )

    # Para birimi seçenekleri
    currency_options = [
        ft.dropdown.Option("TL"),
        ft.dropdown.Option("USD"),
        ft.dropdown.Option("EUR"),
    ]
    currency_dropdown = ft.Dropdown(
        options=currency_options,
        value="TL",
        text_size=12,
        content_padding=10,
        width=80,
        bgcolor="surface",
        border_color="outline",
        border_radius=8,
        hint_text=tr("currency"),
    )

    # TextField'ları sakla
    expense_fields = {}
    expense_cards = []

    for i, m in enumerate(months):
        text_field = ft.TextField(
            value="0",
            text_size=14,
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            color="onBackground",
            text_align=ft.TextAlign.CENTER,
            border_color="outline",
            focused_border_color=col_primary,
            height=35,
            content_padding=5,
            bgcolor="surface",
            prefix_text="₺ ",
        )
        expense_fields[month_keys[i]] = text_field

        card = ft.Container(
            bgcolor="surface",
            border_radius=12,
            padding=10,
            width=140,
            height=85,
            shadow=ft.BoxShadow(
                blur_radius=5, color="#08000000", offset=ft.Offset(0, 3)
            ),
            border=ft.border.all(1, "outlineVariant"),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(m, size=13, weight="bold", color=col_primary),
                        alignment=ft.alignment.center,
                    ),
                    ft.Divider(height=5, color="transparent"),
                    text_field,
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        expense_cards.append(card)

    # Seçili yılın verilerini yükle
    def load_year_data(year=None):
        if year is None:
            year = int(year_dropdown.value)
        yearly_data = backend_instance.db.get_yearly_expenses(year)

        current_curr = currency_dropdown.value
        symbol = (
            "₺ " if current_curr == "TL" else ("$ " if current_curr == "USD" else "€ ")
        )

        if yearly_data:
            for month_key in month_keys:
                amount_tl = yearly_data.get(month_key, 0)
                if amount_tl:
                    if current_curr == "TL":
                        val = amount_tl
                    else:
                        # TL'den seçili para birimine çevir (Görüntüleme için)
                        val = backend_instance.convert_currency(
                            amount_tl, "TRY", current_curr
                        )

                    expense_fields[month_key].value = f"{val:.2f}"
                else:
                    expense_fields[month_key].value = "0"
        else:
            # Veri yoksa sıfırla
            for month_key in month_keys:
                expense_fields[month_key].value = "0"

        # Prefix güncelle
        for field in expense_fields.values():
            field.prefix_text = symbol
            if field.page:
                field.update()

        if page:
            try:
                page.update()
            except Exception:
                pass

    # Yıl değiştiğinde verileri yükle
    def on_year_change(e):
        load_year_data(int(e.control.value))

    year_dropdown.on_change = on_year_change

    # Para birimi değiştiğinde verileri yükle
    def on_currency_change(e):
        load_year_data()

    currency_dropdown.on_change = on_currency_change

    # Kaydet butonu fonksiyonu
    def save_expenses(e):
        """Genel giderleri database'e kaydet"""
        try:
            selected_year = int(year_dropdown.value)
            current_curr = currency_dropdown.value
            monthly_data = {}

            # Tüm ayların değerlerini topla
            for month_key in month_keys:
                value = expense_fields[month_key].value
                try:
                    amount = float(value) if value else 0

                    if current_curr != "TL":
                        # Seçili para biriminden TL'ye çevir (Kayıt için)
                        # Bu işlem o anki kur ile yapılır ve sabitlenir (Historik)
                        amount_tl = backend_instance.convert_currency(
                            amount, current_curr, "TRY"
                        )
                        monthly_data[month_key] = amount_tl
                    else:
                        monthly_data[month_key] = amount

                except ValueError:
                    monthly_data[month_key] = 0

            # Database'e kaydet
            result = backend_instance.db.add_or_update_yearly_expenses(
                selected_year, monthly_data
            )

            if result:
                # Veri güncelleme callback'ini çağır
                if backend_instance.on_data_updated:
                    backend_instance.on_data_updated()

                msg = tr("msg_expenses_saved").format(selected_year)
                if current_curr != "TL":
                    msg += f" {tr('converted_to_tl').format(current_curr)}"

                page.open(ft.SnackBar(content=ft.Text(msg, color=col_white), bgcolor=col_success))
                page.update()

                # Kaydettikten sonra TL moduna dönmek mantıklı olabilir, ama kullanıcı aynı birimde devam etmek isteyebilir.
                # Verileri yeniden yükleyerek (TL'den çevirerek) tutarlılığı gösterelim
                load_year_data()

            else:
                page.open(ft.SnackBar(content=ft.Text(tr("msg_save_error"), color=col_white), bgcolor=col_danger,))
                page.update()

        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(
                    tr("msg_error_prefix").format(str(ex)), color=col_white
                ), bgcolor=col_danger,))
            page.update()

    def export_general_expenses_excel(e):
        """Genel giderleri Excel'e aktar - Aylık format"""
        print("DEBUG: export_general_expenses_excel (Topbar) clicked")
        try:
            expenses = backend_instance.handle_genel_gider_operation("get")
            print(f"DEBUG: expenses count={len(expenses) if expenses else 0}")

            if not expenses:
                page.open(ft.SnackBar(content=ft.Text(tr("msg_no_expenses_export"), color=col_white), bgcolor=col_danger,))
                page.update()
                return

            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    file_path = e.path
                    selected_year = int(year_dropdown.value)

                    # Aylık formatta Excel'e aktar
                    from toexcel import export_monthly_general_expenses_to_excel

                    current_lang = state.get("current_language", "tr")
                    success = export_monthly_general_expenses_to_excel(
                        expenses,
                        year=selected_year,
                        file_path=file_path,
                        lang=current_lang,
                    )

                    if success:

                        def close_success_dlg(e):
                            success_dlg.open = False
                            page.update()

                        success_dlg = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(tr("success")),
                            content=ft.Text(tr("msg_file_saved").format(file_path)),
                            actions=[
                                ft.ElevatedButton(
                                    tr("ok"),
                                    on_click=close_success_dlg,
                                    bgcolor=col_primary,
                                    color=col_white,
                                ),
                            ],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.overlay.append(success_dlg)
                        success_dlg.open = True
                        page.update()
                    else:
                        page.open(ft.SnackBar(content=ft.Text(
                                tr("msg_excel_export_error"), color=col_white
                            ), bgcolor=col_danger,))
                        page.update()

            # Dosya yolu oluştur
            selected_year = int(year_dropdown.value)
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            state.get("current_language", "tr")
            filename = (
                f"{tr('filename_monthly_expenses')}_{selected_year}_{timestamp}.xlsx"
            )

            save_file_picker = ft.FilePicker(on_result=on_save_result)
            page.overlay.append(save_file_picker)
            page.update()
            save_file_picker.save_file(
                dialog_title=tr("title_save_excel"),
                file_name=filename,
                allowed_extensions=["xlsx"],
            )

        except Exception as ex:
            if "cancelled" not in str(ex).lower():
                page.open(ft.SnackBar(content=ft.Text(
                        tr("msg_excel_error_prefix").format(str(ex)), color=col_white
                    ), bgcolor=col_danger,))
                page.update()

    def export_general_expenses_pdf(e):
        """Genel giderleri PDF'e aktar - Aylık format"""
        print("DEBUG: export_general_expenses_pdf (Topbar) clicked")
        try:
            expenses = backend_instance.handle_genel_gider_operation("get")
            print(f"DEBUG: expenses count={len(expenses) if expenses else 0}")

            if not expenses:
                page.open(ft.SnackBar(content=ft.Text(tr("msg_no_expenses_export"), color=col_white), bgcolor=col_danger,))
                page.update()
                return

            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    file_path = e.path
                    selected_year = int(year_dropdown.value)

                    # Aylık formatta PDF'e aktar
                    from topdf import export_monthly_general_expenses_to_pdf

                    current_lang = state.get("current_language", "tr")
                    success = export_monthly_general_expenses_to_pdf(
                        expenses,
                        year=selected_year,
                        file_path=file_path,
                        lang=current_lang,
                    )

                    if success:

                        def close_success_dlg(e):
                            success_dlg.open = False
                            page.update()

                        success_dlg = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(tr("success")),
                            content=ft.Text(tr("msg_file_saved").format(file_path)),
                            actions=[
                                ft.ElevatedButton(
                                    tr("ok"),
                                    on_click=close_success_dlg,
                                    bgcolor=col_primary,
                                    color=col_white,
                                ),
                            ],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.overlay.append(success_dlg)
                        success_dlg.open = True
                        page.update()
                    else:
                        page.open(ft.SnackBar(content=ft.Text(
                                tr("msg_pdf_export_error"), color=col_white
                            ), bgcolor=col_danger,))
                        page.update()

            # Dosya yolu oluştur
            selected_year = int(year_dropdown.value)
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            state.get("current_language", "tr")
            filename = (
                f"{tr('filename_monthly_expenses')}_{selected_year}_{timestamp}.pdf"
            )

            save_file_picker = ft.FilePicker(on_result=on_save_result)
            page.overlay.append(save_file_picker)
            page.update()
            save_file_picker.save_file(
                dialog_title=tr("title_save_pdf"),
                file_name=filename,
                allowed_extensions=["pdf"],
            )

        except Exception as ex:
            if "cancelled" not in str(ex).lower():
                page.open(ft.SnackBar(content=ft.Text(
                        tr("msg_pdf_error_prefix").format(str(ex)), color=col_white
                    ), bgcolor=col_danger,))
                page.update()

    # Sayfa yüklendiğinde mevcut verileri yükle
    load_year_data()

    # Dinamik güncelleme için callback oluştur
    def refresh_general_expenses():
        """Genel giderleri yeniden yükle"""
        try:
            load_year_data()
        except Exception:
            pass

    state["update_callbacks"]["general_expenses"] = refresh_general_expenses

    # Butonları event handler'larla oluştur
    btn_save = create_styled_icon_button(
        ft.Icons.SAVE, "#4CD964", tr("save"), save_expenses
    )

    btn_excel = create_styled_icon_button(
        ft.Icons.TABLE_VIEW,
        "#217346",
        tr("export_excel"),
        export_general_expenses_excel,
    )

    btn_pdf = create_styled_icon_button(
        ft.Icons.PICTURE_AS_PDF,
        "#D32F2F",
        tr("export_pdf"),
        export_general_expenses_pdf,
    )

    expense_buttons = ft.Container(
        padding=ft.padding.only(right=40, top=8, bottom=6),
        content=ft.Row(
            [
                ft.Container(height=35, content=year_dropdown),
                ft.Container(height=35, content=currency_dropdown),
                btn_save,
                btn_excel,
                btn_pdf,
            ],
            spacing=5,
        ),
    )

    return ft.Container(
        alignment=ft.alignment.top_center,
        padding=ft.padding.only(top=15),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon("calendar_month", color=col_secondary, size=20),
                                ft.Text(
                                    tr("yearly_general_expenses"),
                                    size=16,
                                    weight="bold",
                                    color="onBackground",
                                ),
                            ],
                            spacing=8,
                        ),
                        expense_buttons,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=10),
                ft.Container(
                    alignment=ft.alignment.top_center,
                    content=ft.Row(
                        controls=expense_cards,
                        wrap=True,
                        spacing=15,
                        run_spacing=15,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


class AnimatedDonut(ft.Stack):
    def __init__(self, value, total, color, text_value):
        super().__init__()
        self.width = 110
        self.height = 110
        self.alignment = ft.alignment.center
        hex_code = color.lstrip("#")
        shadow_color = f"#66{hex_code}"
        remainder_color = f"#1A{hex_code}"
        
        # Eğer animasyon zaten tamamlanmışsa başlangıç değerlerini nihai hallerine çek
        is_completed = state.get("animation_completed", False)
        self.chart_rotate = ft.Rotate(0 if is_completed else -3.14, alignment=ft.alignment.center)
        
        self.chart = ft.PieChart(
            sections=[
                ft.PieChartSection(value=value, color=color, radius=14, title=""),
                ft.PieChartSection(
                    value=total - value, color=remainder_color, radius=14, title=""
                ),
            ],
            center_space_radius=38,
            sections_space=0,
            start_degree_offset=-90,
        )
        self.chart_container = ft.Container(
            content=self.chart,
            width=110,
            height=110,
            bgcolor="surface",
            shape=ft.BoxShape.CIRCLE,
            shadow=ft.BoxShadow(
                blur_radius=20,
                spread_radius=2,
                color=shadow_color,
                offset=ft.Offset(0, 8),
            ),
            rotate=self.chart_rotate,
            opacity=1 if is_completed else 0,
            animate_opacity=None if is_completed else ft.Animation(800, "easeIn"),
            animate_rotation=None if is_completed else ft.Animation(1500, "easeOutBack"),
        )
        self.text_container = ft.Container(
            content=ft.Text(
                text_value,
                size=15,
                weight="bold",
                color="onBackground",
                text_align="center",
            ),
            alignment=ft.alignment.center,
            rotate=ft.Rotate(0, alignment=ft.alignment.center),
        )
        self.controls = [self.chart_container, self.text_container]
        state["donuts"].append(self)

    def did_mount(self):
        # Sayfa her yüklendiğinde; eğer uygulama bir kez başladıysa animasyonsuz, değilse animasyonlu
        if not state.get("animation_completed", False):
            self.start_animation()

    def start_animation(self):
        try:
            # Sayfa yüklü değilse veya obje sayfada değilse çalışma
            if not self.chart_container.page:
                return

            # Eğer animasyon zaten tamamlanmışsa doğrudan görünür yap (güvenlik amaçlı)
            if state.get("animation_completed", False):
                self.chart_container.opacity = 1
                self.chart_container.rotate.angle = 0
                self.chart_container.update()
            else:
                # İlk kez çalışıyorsa animasyonlu yap
                self.chart_container.rotate.angle = 0
                self.chart_container.opacity = 1
                self.chart_container.update()
        except Exception:
            pass

    def update_value(self, new_value, new_total, new_text):
        """Donut değerlerini günceller"""
        try:
            # Chart sections'ı güncelle
            self.chart.sections[0].value = new_value
            self.chart.sections[1].value = max(0, new_total - new_value)

            # Text'i güncelle
            self.text_container.content.value = new_text

            if not self.chart_container.page:
                return

            # Güncellemeyi uygula
            self.chart_container.update()
            self.text_container.update()
        except Exception:
            pass


class DonutStatCard(ft.Container):
    def __init__(
        self, title, icon, color, trend_text, donut_val, donut_total, display_text
    ):
        super().__init__()
        self.bgcolor = "surface"
        self.border_radius = 24
        self.padding = ft.padding.all(20)
        self.expand = 1
        self.shadow = ft.BoxShadow(
            blur_radius=15, color="shadow", offset=ft.Offset(0, 5)
        )
        self.donut = AnimatedDonut(
            value=donut_val, total=donut_total, color=color, text_value=display_text
        )
        self.content = ft.Row(
            [
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=col_white, size=24),
                            bgcolor=color,
                            border_radius=14,
                            width=48,
                            height=48,
                            alignment=ft.alignment.center,
                            shadow=ft.BoxShadow(
                                blur_radius=10,
                                color=f"#4D{color.lstrip('#')}",
                                offset=ft.Offset(0, 4),
                            ),
                        ),
                        ft.Container(height=5),
                        ft.Text(
                            title, size=14, color="onSurfaceVariant", weight="w600"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                ),
                ft.Container(content=self.donut, alignment=ft.alignment.center_right),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )


class TransactionRow(ft.Container):
    def __init__(
        self,
        title,
        date,
        amount,
        is_income=True,
        is_updated=False,
        is_deleted=False,
        invoice_date=None,
        operation_type="EKLEME",
        currency="TL",
        current_currency="TL",
    ):
        super().__init__()
        self.padding = ft.padding.all(10)
        self.border_radius = 12
        self.bgcolor = "surface"
        self.border = ft.border.all(1, "outlineVariant")
        self.margin = ft.margin.only(bottom=5)

        # İşlem tipine göre ikon ve renk belirleme
        if is_deleted or operation_type == "SİLME":
            icon_name = ft.Icons.DELETE_OUTLINE
            icon_color = "onSurfaceVariant"  # Gri
            bg_color = "surfaceContainerHighest"
            op_text = tr("op_deleted")
            amount_color = "onSurfaceVariant"
        elif is_updated or operation_type == "GÜNCELLEME":
            icon_name = ft.Icons.EDIT
            icon_color = "primary"  # Mavi
            bg_color = "primaryContainer"
            op_text = tr("op_updated")
            amount_color = "primary"
        else:  # EKLEME
            if is_income:
                icon_name = ft.Icons.ARROW_UPWARD
                icon_color = "tertiary"  # Yeşil
                bg_color = "tertiaryContainer"
                op_text = tr("op_income_added")
                amount_color = "tertiary"
            else:
                icon_name = ft.Icons.ARROW_DOWNWARD
                icon_color = "error"  # Kırmızı
                bg_color = "errorContainer"
                op_text = tr("op_expense_added")
                amount_color = "error"

        # İkon Konteyneri
        icon_container = ft.Container(
            content=ft.Icon(icon_name, color=icon_color, size=20),
            width=40,
            height=40,
            bgcolor=bg_color,
            border_radius=10,
            alignment=ft.alignment.center,
        )

        # Tarih Formatlama Yardımcısı
        def format_date_str(d_str):
            if not d_str:
                return ""
            try:
                # YYYY-MM-DD -> DD.MM.YYYY
                if "-" in d_str:
                    parts = d_str.split("-")
                    if len(parts) == 3:
                        return f"{parts[2]}.{parts[1]}.{parts[0]}"
            except Exception:
                pass
            return d_str

        # İşlem Tarihi (Giriş Tarihi)
        op_date_str = str(date)

        # Fatura Tarihi
        inv_date_str = format_date_str(invoice_date) if invoice_date else ""

        # Metin Stilleri
        text_decoration = (
            ft.TextDecoration.LINE_THROUGH if is_deleted else ft.TextDecoration.NONE
        )
        title_color = "onSurfaceVariant" if is_deleted else "onSurface"

        # Tutar Metni - Döviz dönüştürme ve formatlama
        sign = (
            "+"
            if is_income and not is_deleted
            else ("-" if not is_income and not is_deleted else "")
        )

        # Tutarı float'a çevir
        try:
            amount_value = float(str(amount).replace(",", "."))
        except Exception:
            amount_value = 0.0

        # format_currency kullanarak tutarı formatla (büyük sayılar için compact)
        formatted_amount = format_currency(
            amount_value,
            currency=currency,
            target_currency=current_currency,
            compact=False,
        )

        amount_text = ft.Text(
            f"{sign}{formatted_amount}",
            size=14,
            weight="bold",
            color=amount_color,
            style=ft.TextStyle(decoration=text_decoration),
        )

        # İçerik Düzeni
        self.content = ft.Row(
            [
                icon_container,
                ft.Column(
                    [
                        ft.Text(
                            title if title else "—",
                            size=14,
                            weight="bold",
                            color=title_color,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            style=ft.TextStyle(decoration=text_decoration),
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        op_text, size=9, weight="bold", color=icon_color
                                    ),
                                    bgcolor=bg_color,
                                    padding=ft.padding.symmetric(
                                        horizontal=6, vertical=2
                                    ),
                                    border_radius=4,
                                ),
                                ft.Text(
                                    tr("entry_date").format(op_date_str),
                                    size=11,
                                    color="onSurfaceVariant",
                                ),
                            ],
                            spacing=5,
                            wrap=True,
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CALENDAR_TODAY,
                                    size=10,
                                    color="onSurfaceVariant",
                                ),
                                ft.Text(
                                    tr("invoice_date").format(inv_date_str),
                                    size=11,
                                    color="onSurfaceVariant",
                                    weight="w500",
                                ),
                            ],
                            spacing=4,
                            visible=bool(inv_date_str),
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                amount_text,
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )


def currency_button(text, currency_code, current_selection, on_click_handler):
    is_selected = currency_code == current_selection
    return ft.Container(
        content=ft.Text(
            text,
            color=col_primary if is_selected else col_text_light,
            weight="bold" if is_selected else "normal",
        ),
        bgcolor="surface" if is_selected else "transparent",
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=10,
        shadow=ft.BoxShadow(blur_radius=5, color="#10000000", offset=ft.Offset(0, 2))
        if is_selected
        else None,
        on_click=lambda e: on_click_handler(currency_code),
        animate=ft.Animation(200, "easeOut"),
    )


# --- ANA UYGULAMA ---
# ============================================================================
# İNTERNET BAĞLANTI MONİTÖRÜ (Internet Connectivity Monitor)
# ============================================================================
def start_internet_monitor():
    """Her 5 saniyede internet bağlantısını kontrol eder.
    Kesilince üst uyarı widgetını gösterir;
    tekrar bağlanınca hem üstten hem alttan bildirim verir.
    """
    _mon_state = {"prev_online": None}  # None = ilk kontrol henüz yapılmadı

    def _is_online():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("8.8.8.8", 53))
            s.close()
            return True
        except Exception:
            return False

    def _monitor():
        while True:
            time.sleep(5)
            online = _is_online()
            page_ref = state.get("page")
            warning = state.get("internet_warning")
            reconnected = state.get("internet_reconnected_widget")

            if page_ref is None or warning is None:
                continue

            prev = _mon_state["prev_online"]

            if not online and prev is not False:
                # İnternet kesildi
                _mon_state["prev_online"] = False
                try:
                    warning.visible = True
                    warning.update()
                except Exception:
                    pass
                # Alt snackbar - internet kesildi
                try:
                    lang = state.get("current_language", "tr")
                    msg = get_text("no_internet_warning", lang)
                    page_ref.open(ft.SnackBar(
                        content=ft.Text("⚠️ " + msg, color="#FFFFFF"),
                        bgcolor=col_danger,
                        duration=4000,
                    ))
                    page_ref.update()
                except Exception:
                    pass

            elif online and prev is False:
                # İnternet geri geldi
                _mon_state["prev_online"] = True
                try:
                    warning.visible = False
                    warning.update()
                except Exception:
                    pass
                # Üst yeşil bant
                if reconnected is not None:
                    try:
                        reconnected.visible = True
                        reconnected.update()
                    except Exception:
                        pass

                    def _hide_reconnected(widget=reconnected):
                        time.sleep(4)
                        try:
                            widget.visible = False
                            widget.update()
                        except Exception:
                            pass
                    threading.Thread(target=_hide_reconnected, daemon=True).start()
                # Alt snackbar
                try:
                    lang = state.get("current_language", "tr")
                    msg = get_text("internet_reconnected", lang)
                    page_ref.open(ft.SnackBar(
                        content=ft.Text("✅ " + msg, color="#FFFFFF"),
                        bgcolor=col_success,
                        duration=4000,
                    ))
                    page_ref.update()
                except Exception:
                    pass

            elif online and prev is None:
                # İlk kontrol - bağlı, sessiz geç
                _mon_state["prev_online"] = True

    threading.Thread(target=_monitor, daemon=True).start()


# ============================================================================
# ANA UYGULAMA (Main Application)
# ============================================================================
def main(page: ft.Page):
    page.title = "Excellent"
    page.padding = 0
    page.bgcolor = "background"
    state["page"] = page  # SnackBar gibi sayfa düzeyi işlemleri için global erişim
    
    # Pencere Boyutları ve Davranışı
    page.window.width = 1280
    page.window.height = 800
    # Minimum boyut: dikey dikdörtgen yan panel formu
    # (480 × 720) — kullanıcı pencereyi sağa/sola yaslarken
    # form alanları ve tablo birbirine girmeden sığacak minimum alan.
    page.window.min_width = 900
    page.window.min_height = 680
    page.window.resizable = True  # Kullanıcı boyutlandırabilir
    page.window.icon = resource_path("app_icon.ico")

    # Responsive tasarım için genişliği 100% yapıyoruz
    page.expand = True

    # Tema Ayarları
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            background="#F4F5FA",
            surface="#FFFFFF",
            on_background="#1A1D1F",
            on_surface="#1A1D1F",
            primary="#6C5DD3",
            secondary="#FF9F43",
            tertiary="#4CD964",
            error="#FF3B30",
            outline="#E6E8EC",
            on_surface_variant="#9AA1B9",
            shadow="#08000000",  # Çok hafif gölge (Light mode için)
        )
    )
    page.dark_theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            background="#18191A",  # Daha yumuşak siyah (Dark mode background)
            surface="#242526",  # Daha yumuşak yüzey rengi
            on_background="#E4E6EB",
            on_surface="#E4E6EB",
            primary="#6C5DD3",
            secondary="#FF9F43",
            tertiary="#4CD964",
            error="#FF3B30",
            outline="#3A3B3C",
            on_surface_variant="#B0B3B8",
            shadow="#40000000",  # Belirgin ama yumuşak gölge (Dark mode için)
        )
    )
    page.theme_mode = ft.ThemeMode.SYSTEM
    state["page"] = page
    backend_instance.start_timers()

    # ------------------------------------------------------------------------
    # VERİ YARDIMCILARI (Data Helpers)
    # ------------------------------------------------------------------------
    def get_all_available_years():
        """Veritabanındaki tüm yılları döndürür (gelir, gider ve genel gider tablolarından) - sadece veri olan yıllar"""
        years = set()
        try:
            # Gelir faturalarından yılları topla
            income_invoices = (
                backend_instance.handle_invoice_operation("get", "outgoing") or []
            )
            for invoice in income_invoices:
                tarih = invoice.get("tarih", "")
                if tarih:
                    parts = tarih.split(".")
                    if len(parts) == 3:
                        try:
                            years.add(int(parts[2]))
                        except ValueError:
                            pass

            # Gider faturalarından yılları topla
            expense_invoices = (
                backend_instance.handle_invoice_operation("get", "incoming") or []
            )
            for invoice in expense_invoices:
                tarih = invoice.get("tarih", "")
                if tarih:
                    parts = tarih.split(".")
                    if len(parts) == 3:
                        try:
                            years.add(int(parts[2]))
                        except ValueError:
                            pass

            # Genel giderlerden yılları topla (sadece en az bir aya veri girilmişse)
            try:
                all_general_expenses = backend_instance.db.get_all_yearly_expenses()
                month_keys = [
                    "ocak",
                    "subat",
                    "mart",
                    "nisan",
                    "mayis",
                    "haziran",
                    "temmuz",
                    "agustos",
                    "eylul",
                    "ekim",
                    "kasim",
                    "aralik",
                ]

                for expense_data in all_general_expenses:
                    if expense_data and "yil" in expense_data:
                        # En az bir ayda veri var mı kontrol et
                        has_data = False
                        for month in month_keys:
                            if (
                                expense_data.get(month)
                                and float(expense_data.get(month, 0) or 0) > 0
                            ):
                                has_data = True
                                break

                        if has_data:
                            try:
                                years.add(int(expense_data["yil"]))
                            except (ValueError, TypeError):
                                pass
            except Exception:
                pass

        except Exception:
            pass

        # Eğer hiç yıl bulunamadıysa mevcut yılı ekle
        if not years:
            years.add(datetime.now().year)

        return sorted(years, reverse=True)

    def get_line_chart_data():
        """Backend'den aylık gelir/gider verilerini çeker ve line chart formatında döndürür"""
        try:
            # Seçili para birimini belirle
            current_currency = state.get("current_currency", "TRY")
            amount_field = "toplam_tutar_tl"
            if current_currency == "USD":
                amount_field = "toplam_tutar_usd"
            elif current_currency == "EUR":
                amount_field = "toplam_tutar_eur"

            # Backend'den tüm faturaları al (operation='get')
            income_invoices = (
                backend_instance.handle_invoice_operation("get", "outgoing") or []
            )
            expense_invoices = (
                backend_instance.handle_invoice_operation("get", "incoming") or []
            )

            # Yıllara göre grupla
            yearly_data = {}

            # Gelir faturalarını işle
            for idx, invoice in enumerate(income_invoices):
                tarih = invoice.get("tarih", "")
                if not tarih:
                    continue

                parts = tarih.split(".")
                if len(parts) != 3:
                    continue

                try:
                    month = int(parts[1])
                    year = int(parts[2])
                    amount = (
                        float(invoice.get(amount_field, 0)) / 1000
                    )  # K (bin) cinsine çevir

                    if year not in yearly_data:
                        yearly_data[year] = {"gelir": [0] * 12, "gider": [0] * 12}

                    yearly_data[year]["gelir"][month - 1] += amount
                except (ValueError, IndexError):
                    continue

            # Gider faturalarını işle
            for invoice in expense_invoices:
                tarih = invoice.get("tarih", "")
                if not tarih:
                    continue

                parts = tarih.split(".")
                if len(parts) != 3:
                    continue

                try:
                    month = int(parts[1])
                    year = int(parts[2])
                    amount = (
                        float(invoice.get(amount_field, 0)) / 1000
                    )  # K (bin) cinsine çevir

                    if year not in yearly_data:
                        yearly_data[year] = {"gelir": [0] * 12, "gider": [0] * 12}

                    yearly_data[year]["gider"][month - 1] += amount
                except (ValueError, IndexError):
                    continue

            # Genel giderleri ekle - her yıl için
            month_keys = [
                "ocak",
                "subat",
                "mart",
                "nisan",
                "mayis",
                "haziran",
                "temmuz",
                "agustos",
                "eylul",
                "ekim",
                "kasim",
                "aralik",
            ]
            for year in list(yearly_data.keys()):
                general_expenses = backend_instance.db.get_yearly_expenses(year)
                if general_expenses:
                    for month_idx, month_key in enumerate(month_keys):
                        if month_key in general_expenses:
                            general_amount_tl = float(general_expenses[month_key] or 0)

                            # Para birimine göre çevir
                            general_amount = general_amount_tl
                            if current_currency != "TRY":
                                general_amount = backend_instance.convert_currency(
                                    general_amount_tl, "TRY", current_currency
                                )

                            yearly_data[year]["gider"][month_idx] += (
                                general_amount / 1000
                            )  # K cinsine çevir

            # Eğer veri yoksa boş dict döndür
            if not yearly_data:
                return {}

            return yearly_data
        except Exception:
            return {}

    # ------------------------------------------------------------------------
    # GRAFİK ÇİZİM FONKSİYONLARI (Chart Drawing Functions)
    # ------------------------------------------------------------------------
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
            max_value = max(
                max(year_data.get("gelir", [0])), max(year_data.get("gider", [0]))
            )
        else:
            # Tüm yılların verileri
            for year_data in full_data.values():
                max_value = max(
                    max_value,
                    max(year_data.get("gelir", [0])),
                    max(year_data.get("gider", [0])),
                )

        # Yuvarla (50'lik artışlarla)
        if max_value == 0:
            return 150

        # Daha iyi görünüm için biraz boşluk bırak
        return ((int(max_value) // 50) + 2) * 50

    chart_max_y = calculate_max_y()

    # Y ekseni label'larını dinamik oluştur
    def get_y_axis_labels(max_y):
        """Y ekseni için dinamik label'lar oluşturur"""
        current_currency = state.get("current_currency", "TRY")
        symbol = ""
        if current_currency == "USD":
            symbol = "$"
        elif current_currency == "EUR":
            symbol = "€"

        step = max_y // 3
        return [
            ft.ChartAxisLabel(
                value=0, label=ft.Text("0", size=10, color="onSurfaceVariant")
            ),
            ft.ChartAxisLabel(
                value=step,
                label=ft.Text(f"{symbol}{step}K", size=10, color="onSurfaceVariant"),
            ),
            ft.ChartAxisLabel(
                value=step * 2,
                label=ft.Text(
                    f"{symbol}{step * 2}K", size=10, color="onSurfaceVariant"
                ),
            ),
            ft.ChartAxisLabel(
                value=max_y,
                label=ft.Text(f"{symbol}{max_y}K", size=10, color="onSurfaceVariant"),
            ),
        ]

    line_chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=[],
                stroke_width=5,
                color=col_primary,
                curved=True,
                stroke_cap_round=True,
                below_line_gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=[col_primary_50, transparent_white],
                ),
            ),
            ft.LineChartData(
                data_points=[],
                stroke_width=5,
                color=col_secondary,
                curved=True,
                stroke_cap_round=True,
                below_line_gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=[col_secondary_50, transparent_white],
                ),
            ),
        ],
        border=ft.border.all(0, "transparent"),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=i, label=ft.Text(m, size=12, color="onSurfaceVariant")
                )
                for i, m in enumerate(
                    [
                        "Oca",
                        "Şub",
                        "Mar",
                        "Nis",
                        "May",
                        "Haz",
                        "Tem",
                        "Ağu",
                        "Eyl",
                        "Eki",
                        "Kas",
                        "Ara",
                    ]
                )
            ],
            labels_size=30,
        ),
        left_axis=ft.ChartAxis(labels=get_y_axis_labels(chart_max_y), labels_size=40),
        tooltip_bgcolor=tooltip_bg,
        min_y=0,
        max_y=chart_max_y,
        min_x=0,
        max_x=11,
        expand=True,
        horizontal_grid_lines=ft.ChartGridLines(
            color="outlineVariant", width=1, dash_pattern=[5, 5]
        ),
        animate=None,
    )

    def draw_snake_chart(year):
        """Yılan grafiğini çizen fonksiyon - yıl parametresi int veya str olabilir"""
        # Yıl değerini int'e çevir
        try:
            year = int(year)
        except (ValueError, TypeError):
            return

        if state["current_page"] != "home":
            return

        # SAYFADAN KONTROL: Eğer bileşen sayfada yoksa işlem yapma
        if not line_chart.page:
            return

        # Veri kontrolü - Eğer seçili yıl veya veri yoksa boş grafik göster
        if not full_data or year not in full_data:
            line_chart.data_series[0].data_points = []
            line_chart.data_series[1].data_points = []
            try:
                line_chart.update()
            except Exception:
                pass
            return

        # Seçili yıla göre Y eksenini yeniden hesapla ve güncelle
        year_max_y = calculate_max_y(year)
        line_chart.max_y = year_max_y
        line_chart.left_axis.labels = get_y_axis_labels(year_max_y)

        # Para birimi sembolü
        current_currency = state.get("current_currency", "TRY")
        symbol = ""
        if current_currency == "USD":
            symbol = "$"
        elif current_currency == "EUR":
            symbol = "€"

        # Animasyon bittiyse direkt çiz
        if state["animation_completed"]:
            line_chart.data_series[0].data_points = [
                ft.LineChartDataPoint(
                    i,
                    full_data[year]["gelir"][i],
                    tooltip=f"{symbol}{full_data[year]['gelir'][i]:.1f}K",
                )
                for i in range(12)
            ]
            line_chart.data_series[1].data_points = [
                ft.LineChartDataPoint(
                    i,
                    full_data[year]["gider"][i],
                    tooltip=f"{symbol}{full_data[year]['gider'][i]:.1f}K",
                )
                for i in range(12)
            ]
            try:
                line_chart.update()
            except Exception:
                pass
            return

        # Animasyonlu Çizim Başlangıcı
        line_chart.data_series[0].data_points = []
        line_chart.data_series[1].data_points = []
        try:
            line_chart.update()
        except Exception:
            pass

        time.sleep(0.2)

        gelir_data = full_data[year]["gelir"]
        gider_data = full_data[year]["gider"]

        for i in range(len(gelir_data)):
            if state["current_page"] != "home":
                state["animation_completed"] = True
                return

            line_chart.data_series[0].data_points.append(
                ft.LineChartDataPoint(
                    i, gelir_data[i], tooltip=f"{symbol}{gelir_data[i]:.1f}K"
                )
            )
            line_chart.data_series[1].data_points.append(
                ft.LineChartDataPoint(
                    i, gider_data[i], tooltip=f"{symbol}{gider_data[i]:.1f}K"
                )
            )

            try:
                if line_chart.page:
                    line_chart.update()
            except Exception:
                pass
            time.sleep(0.04)

        state["animation_completed"] = True
        try:
            if line_chart.page:
                line_chart.update()
        except Exception:
            pass

    def on_year_change(e):
        state["animation_completed"] = False
        # Hem yılan grafik hem de donut'ları güncelle
        threading.Thread(
            target=draw_snake_chart, args=(e.control.value,), daemon=True
        ).start()
        # Donut'ları da güncelle
        update_donuts_for_year(int(e.control.value))

    def update_donuts_for_year(year):
        """Seçili yıla göre donut'ları günceller"""
        try:
            # Seçili para birimini al
            current_currency = state.get("current_currency", "TRY")

            # Seçili yıl için istatistikleri al
            year_stats = get_dashboard_stats(year)

            # Her donut için yeni değerleri hesapla
            profit_max = max(abs(year_stats["net_profit"]) * 1.2, 10000)
            income_max = max(year_stats["total_income"] * 1.2, 10000)
            expense_max = max(year_stats["total_expense"] * 1.2, 10000)
            avg_max = max(year_stats["monthly_avg"] * 1.2, 10000)

            # Donut'ları güncelle
            if len(state["donuts"]) >= 4:
                # Net kâr donut
                state["donuts"][0].update_value(
                    abs(year_stats["net_profit"]),
                    profit_max,
                    format_currency(
                        year_stats["net_profit"],
                        currency=current_currency,
                        compact=True,
                    ),
                )

                # Toplam gelir donut
                state["donuts"][1].update_value(
                    year_stats["total_income"],
                    income_max,
                    format_currency(
                        year_stats["total_income"],
                        currency=current_currency,
                        compact=True,
                    ),
                )

                # Toplam gider donut
                state["donuts"][2].update_value(
                    year_stats["total_expense"],
                    expense_max,
                    format_currency(
                        year_stats["total_expense"],
                        currency=current_currency,
                        compact=True,
                    ),
                )

                # Aylık ortalama donut
                state["donuts"][3].update_value(
                    year_stats["monthly_avg"],
                    avg_max,
                    format_currency(
                        year_stats["monthly_avg"],
                        currency=current_currency,
                        compact=True,
                    ),
                )
        except Exception:
            pass

    # Backend callback'ini yeniden tanımla (grafikleri güncellemek için)
    # ------------------------------------------------------------------------
    # VERİ GÜNCELLEME (Data Refresh)
    # ------------------------------------------------------------------------
    def refresh_charts_and_data():
        """Grafikleri ve verileri yeniden yükler"""
        try:
            nonlocal full_data, chart_max_y, year_dropdown_options, available_years

            # 1. Grafik verilerini yeniden yükle
            full_data = get_line_chart_data()

            # 2. Yıl seçeneklerini güncelle - tüm veritabanı yıllarını çek
            available_years = get_all_available_years()
            year_dropdown_options = [
                ft.dropdown.Option(str(year)) for year in available_years
            ]

            # 3. Dropdown'ı güncelle
            if year_dropdown_ref:
                year_dropdown_ref.options = year_dropdown_options
                # Eğer seçili yıl hala mevcut değilse, ilk yılı seç
                current_selected = year_dropdown_ref.value
                if current_selected not in [str(y) for y in available_years]:
                    year_dropdown_ref.value = (
                        str(available_years[0])
                        if available_years
                        else str(datetime.now().year)
                    )

                if hasattr(year_dropdown_ref, "page") and year_dropdown_ref.page:
                    year_dropdown_ref.update()

            # 4. Seçili yılı al
            selected_year = (
                int(year_dropdown_ref.value)
                if year_dropdown_ref and year_dropdown_ref.value
                else (available_years[0] if available_years else datetime.now().year)
            )

            # 5. Seçili yıla göre Max Y değerini hesapla
            chart_max_y = calculate_max_y(selected_year)

            # Para birimi sembolü
            current_currency = state.get("current_currency", "TRY")
            symbol = ""
            if current_currency == "USD":
                symbol = "$"
            elif current_currency == "EUR":
                symbol = "€"

            # 6. Line chart'ı güncelle
            if line_chart:
                try:
                    line_chart.left_axis.labels = get_y_axis_labels(chart_max_y)
                    line_chart.max_y = chart_max_y

                    if selected_year in full_data:
                        # Grafiği direkt çiz (animasyonsuz)
                        line_chart.data_series[0].data_points = [
                            ft.LineChartDataPoint(
                                i,
                                full_data[selected_year]["gelir"][i],
                                tooltip=f"{symbol}{full_data[selected_year]['gelir'][i]:.1f}K",
                            )
                            for i in range(12)
                        ]
                        line_chart.data_series[1].data_points = [
                            ft.LineChartDataPoint(
                                i,
                                full_data[selected_year]["gider"][i],
                                tooltip=f"{symbol}{full_data[selected_year]['gider'][i]:.1f}K",
                            )
                            for i in range(12)
                        ]
                    else:
                        # Veri yoksa grafiği temizle
                        line_chart.data_series[0].data_points = []
                        line_chart.data_series[1].data_points = []

                    # Update sadece page varsa
                    if hasattr(line_chart, "page") and line_chart.page:
                        line_chart.update()
                except Exception:
                    pass

            # 7. Donut grafikleri güncelle - seçili yıla göre
            update_donuts_for_year(selected_year)

            # 8. İşlem geçmişini güncelle (döviz değişikliği için)
            if "transaction_history" in state["update_callbacks"]:
                state["update_callbacks"]["transaction_history"]()

            # 9. Sayfayı güncelle
            try:
                page.update()
            except Exception:
                pass

        except Exception:
            pass

    # Ana sayfa için birleşik callback - hem grafikler hem işlem geçmişi
    state["update_callbacks"]["home_page"] = refresh_charts_and_data

    # ------------------------------------------------------------------------
    # TOPBAR BİLEŞENLERİ (TopBar Components)
    # ------------------------------------------------------------------------
    class TopBarTab(ft.Container):
        def __init__(self, text, page_name, is_selected=False):
            super().__init__()
            self.data = page_name
            self.is_selected = is_selected
            self.padding = ft.padding.symmetric(horizontal=16, vertical=10) # 12 -> 16 (Daha dengeli)
            self.border_radius = ft.border_radius.only(top_left=8, top_right=8)
            self.animate = ft.Animation(200, "easeOut")

            self.text_control = ft.Text(text, size=14, weight="bold")
            self.content = self.text_control
            self.update_visuals(run_update=False)

        def update_visuals(self, run_update=False): # Varsayılanı False yaptık, toplu güncelleme için
            if self.is_selected:
                # Daha açık mor ve daha parlak efekt
                self.bgcolor = ft.colors.with_opacity(0.15, col_primary) if hasattr(ft, "colors") else "#266C5DD3"
                self.text_control.color = col_primary
                self.text_control.size = 15
                self.border = ft.border.only(top=ft.border.BorderSide(4, col_primary))
                self.shadow = ft.BoxShadow(blur_radius=15, color=ft.colors.with_opacity(0.3, col_primary)) if hasattr(ft, "colors") else ft.BoxShadow(blur_radius=15, color="#4D6C5DD3")
            else:
                self.bgcolor = "transparent"
                self.text_control.color = "onSurfaceVariant"
                self.text_control.size = 14
                self.border = ft.border.only(top=ft.border.BorderSide(4, "transparent"))
                self.shadow = None

            if run_update:
                self.update()

    # Sidebar toggle fonksiyonu artık yok
    # def toggle_sidebar(e): ...

    # ------------------------------------------------------------------------
    # DÖNEMSEL GELİR SAYFASI
    # ------------------------------------------------------------------------
    def create_donemsel_page():
        # Yıl dropdown'ı için seçenekler
        current_year = datetime.now().year
        year_options = [
            ft.dropdown.Option(str(y))
            for y in range(current_year - 2, current_year + 2)
        ]

        year_dropdown = ft.Dropdown(
            options=year_options,
            value=str(current_year),
            text_size=12,
            content_padding=10,
            width=95,
            bgcolor="surface",
            border_color="outline",
            border_radius=8,
        )

        # Kurumlar vergisi input field'ları - tabloda kullanılacak
        month_keys = [
            "ocak",
            "subat",
            "mart",
            "nisan",
            "mayis",
            "haziran",
            "temmuz",
            "agustos",
            "eylul",
            "ekim",
            "kasim",
            "aralik",
        ]
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
                        monthly_data[month_key] = (
                            float(value.replace(",", ".")) if value else 0
                        )
                    except ValueError:
                        monthly_data[month_key] = 0

                # Database'e kaydet
                backend_instance.db.add_or_update_corporate_tax(
                    selected_year, monthly_data
                )

                # Veri güncelleme callback'ini çağır
                if backend_instance.on_data_updated:
                    backend_instance.on_data_updated()

                # Tabloyu güncelle (ödenecek vergi hesabı için)
                table_container.content = create_donemsel_table(
                    selected_year, tax_fields_list, on_tax_field_blur
                )
                page.update()
            except Exception:
                pass

        # 12 aylık TextField oluştur
        for i, month_key in enumerate(month_keys):
            text_field = ft.TextField(
                value="0",
                text_size=12,
                color="onSurface",
                text_align=ft.TextAlign.CENTER,
                border_color="outline",
                focused_border_color="primary",
                height=35,
                width=120,
                content_padding=ft.padding.symmetric(horizontal=5, vertical=5),
                bgcolor="surface",
                suffix_text=" %",
                hint_text="0",
                on_blur=on_tax_field_blur,
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
            table_container.content = create_donemsel_table(
                selected_year, tax_fields_list, on_tax_field_blur
            )
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
                month_keys = [
                    "ocak",
                    "subat",
                    "mart",
                    "nisan",
                    "mayis",
                    "haziran",
                    "temmuz",
                    "agustos",
                    "eylul",
                    "ekim",
                    "kasim",
                    "aralik",
                ]
                for month_key in month_keys:
                    amount = tax_data.get(month_key, 0)
                    if month_key in tax_fields_dict:
                        tax_fields_dict[month_key].value = (
                            str(amount) if amount else "0"
                        )

                # Tabloyu güncelle
                table_container.content = create_donemsel_table(selected_year, tax_fields_list, on_tax_field_blur)
                if table_container.page:
                    table_container.update()
                    page.update()
            except Exception:
                pass

        state["update_callbacks"]["donemsel_page"] = refresh_donemsel_data

        # Tablo container - başlangıçta field'ları ile oluştur
        table_container = ft.Container(
            expand=True,
            bgcolor="surface",
            padding=0, # Sayfa ile hizalanması için padding 0 yapıldı
            border_radius=12,
            shadow=ft.BoxShadow(
                blur_radius=10, color="#1A000000", offset=ft.Offset(0, 5)
            ),
            content=create_donemsel_table(current_year, tax_fields_list, on_tax_field_blur),
        )

        # İlk yüklemede verileri doldur
        load_corporate_tax_data()

        def on_year_change(e):
            """Yıl değiştiğinde tabloyu güncelle"""
            selected_year = int(e.control.value)

            # Kurumlar vergisi verilerini yükle
            tax_data = backend_instance.db.get_corporate_tax(selected_year) or {}
            month_keys = [
                "ocak",
                "subat",
                "mart",
                "nisan",
                "mayis",
                "haziran",
                "temmuz",
                "agustos",
                "eylul",
                "ekim",
                "kasim",
                "aralik",
            ]
            for month_key in month_keys:
                amount = tax_data.get(month_key, 0)
                tax_fields_dict[month_key].value = str(amount) if amount else "0"

            # Tabloyu güncelle
            table_container.content = create_donemsel_table(
                selected_year, tax_fields_list, on_tax_field_blur
            )
            page.update()

        year_dropdown.on_change = on_year_change

        # File Picker Handlers
        def on_save_excel_result(e: ft.FilePickerResultEvent):
            if e.path:
                file_path = e.path
                selected_year = int(year_dropdown.value)
                # Verileri topla (tarih filtresi varsa uygula)
                start_date = report_filter_state.get("start")
                end_date = report_filter_state.get("end")
                monthly_results, quarterly_results, summary = calculate_periodic_data(
                    selected_year, start_date=start_date, end_date=end_date
                )

                # Export
                from toexcel import export_monthly_income_to_excel

                current_lang = state.get("current_language", "tr")
                success = export_monthly_income_to_excel(
                    selected_year,
                    monthly_results,
                    quarterly_results,
                    summary,
                    file_path,
                    lang=current_lang,
                )

                if success:

                    def close_success_dlg(e):
                        success_dlg.open = False
                        page.update()

                    success_dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text(tr("success")),
                        content=ft.Text(f"Dosya başarıyla kaydedildi:\n{file_path}"),
                        actions=[
                            ft.ElevatedButton(
                                "Tamam",
                                on_click=close_success_dlg,
                                bgcolor=col_primary,
                                color=col_white,
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.overlay.append(success_dlg)
                    success_dlg.open = True
                    page.update()
                else:
                    page.open(ft.SnackBar(content=ft.Text(tr("msg_excel_report_error"), color=col_white), bgcolor=col_danger,))
                    page.update()

        def on_save_pdf_result(e: ft.FilePickerResultEvent):
            if e.path:
                file_path = e.path
                selected_year = int(year_dropdown.value)
                # Verileri topla (tarih filtresi varsa uygula)
                start_date = report_filter_state.get("start")
                end_date = report_filter_state.get("end")
                monthly_results, quarterly_results, summary = calculate_periodic_data(
                    selected_year, start_date=start_date, end_date=end_date
                )

                # Export
                from topdf import export_monthly_income_to_pdf

                current_lang = state.get("current_language", "tr")
                success = export_monthly_income_to_pdf(
                    selected_year,
                    monthly_results,
                    quarterly_results,
                    summary,
                    file_path,
                    lang=current_lang,
                )

                if success:

                    def close_success_dlg(e):
                        success_dlg.open = False
                        page.update()

                    success_dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text(tr("success")),
                        content=ft.Text(f"Dosya başarıyla kaydedildi:\n{file_path}"),
                        actions=[
                            ft.ElevatedButton(
                                "Tamam",
                                on_click=close_success_dlg,
                                bgcolor=col_primary,
                                color=col_white,
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.overlay.append(success_dlg)
                    success_dlg.open = True
                    page.update()
                else:
                    page.open(ft.SnackBar(content=ft.Text(tr("msg_pdf_report_error"), color=col_white), bgcolor=col_danger,))
                    page.update()

        save_file_picker_excel = ft.FilePicker(on_result=on_save_excel_result)
        save_file_picker_pdf = ft.FilePicker(on_result=on_save_pdf_result)
        page.overlay.extend([save_file_picker_excel, save_file_picker_pdf])

        # --- EXPORT DATE FILTER FOR REPORTS ---
        report_export_start_date = ft.TextField(
            hint_text=tr("date_hint"),
            label=tr("label_start_date"),
            width=140,
            text_size=12,
            height=40,
            bgcolor="surface",
            border_color="outline",
            focused_border_color="primary",
            border_radius=8,
        )

        def pick_report_start_date(e):
            def on_change(e):
                report_export_start_date.value = e.control.value.strftime("%d.%m.%Y")
                report_export_start_date.update()
            page.open(ft.DatePicker(on_change=on_change))

        report_export_end_date = ft.TextField(
            hint_text=tr("date_hint"),
            label=tr("label_end_date"),
            width=140,
            text_size=12,
            height=40,
            bgcolor="surface",
            border_color="outline",
            focused_border_color="primary",
            border_radius=8,
        )

        def pick_report_end_date(e):
            def on_change(e):
                report_export_end_date.value = e.control.value.strftime("%d.%m.%Y")
                report_export_end_date.update()
            page.open(ft.DatePicker(on_change=on_change))

        # Raporlama Butonları
        pdf_report_btn = ft.ElevatedButton(
            tr("export_pdf"),
            icon=ft.Icons.PICTURE_AS_PDF,
            on_click=lambda _: open_report_dialog("pdf"),
            style=ft.ButtonStyle(
                color=col_white,
                bgcolor=col_danger,
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
            ),
        )
        excel_report_btn = ft.ElevatedButton(
            tr("export_excel"),
            icon=ft.Icons.TABLE_VIEW,
            on_click=lambda _: open_report_dialog("excel"),
            style=ft.ButtonStyle(
                color=col_white,
                bgcolor=col_success,
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
            ),
        )

        report_export_format = {"format": "excel"}
        report_filter_state = {"start": None, "end": None}

        def execute_report_export(use_filter=False):
            report_export_dialog.open = False
            page.update()

            if use_filter:
                report_filter_state["start"] = report_export_start_date.value if report_export_start_date.value else None
                report_filter_state["end"] = report_export_end_date.value if report_export_end_date.value else None
            else:
                report_filter_state["start"] = None
                report_filter_state["end"] = None
            
            selected_year = int(year_dropdown.value)
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            
            if report_export_format["format"] == "excel":
                filename = f"{tr('filename_periodic_income')}_{selected_year}_{timestamp}.xlsx"
                save_file_picker_excel.save_file(dialog_title=tr("title_save_excel_report"), file_name=filename)
            else:
                filename = f"{tr('filename_periodic_income')}_{selected_year}_{timestamp}.pdf"
                save_file_picker_pdf.save_file(dialog_title=tr("title_save_pdf_report"), file_name=filename)

        def open_report_dialog(mode):
            report_export_format["format"] = mode
            report_export_dialog.open = True
            page.update()

        report_export_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(tr("dialog_report_export"), size=18, weight="bold"),
            content=ft.Column(
                [
                    ft.Text(tr("dialog_report_export_text"), size=13),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    report_export_start_date,
                                    ft.IconButton(
                                        ft.Icons.CALENDAR_MONTH,
                                        on_click=pick_report_start_date,
                                        icon_size=20,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0,
                            ),
                            ft.Column(
                                [
                                    report_export_end_date,
                                    ft.IconButton(
                                        ft.Icons.CALENDAR_MONTH,
                                        on_click=pick_report_end_date,
                                        icon_size=20,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0,
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                tight=True,
                width=350,
            ),
            actions=[
                ft.ElevatedButton(
                    tr("btn_filtered_download"),
                    on_click=lambda _: execute_report_export(True),
                    bgcolor=col_primary,
                    color=col_white,
                ),
                ft.ElevatedButton(
                    tr("btn_full_year_download"),
                    on_click=lambda _: execute_report_export(False),
                    bgcolor=col_success,
                    color=col_white,
                ),
                ft.TextButton(
                    tr("cancel"),
                    on_click=lambda e: setattr(report_export_dialog, "open", False)
                    or page.update(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        page.overlay.append(report_export_dialog)

        def open_report_export_dialog(fmt):
            report_export_format["format"] = fmt
            report_export_start_date.value = ""
            report_export_end_date.value = ""
            report_export_dialog.open = True
            page.update()

        # Export fonksiyonları
        def export_to_excel_donemsel(e):
            """Dönemsel gelir raporunu Excel'e aktar"""
            open_report_export_dialog("excel")

        def export_to_pdf_donemsel(e):
            """Dönemsel gelir raporunu PDF'e aktar"""
            open_report_export_dialog("pdf")

        def calculate_periodic_data(year, start_date=None, end_date=None):
            """Dönemsel veriler için hesaplama yap"""
            # Backend'den verileri çek
            income_invoices = (
                backend_instance.handle_invoice_operation("get", "outgoing") or []
            )
            expense_invoices = (
                backend_instance.handle_invoice_operation("get", "incoming") or []
            )
            general_expenses = backend_instance.db.get_yearly_expenses(year) or {}
            corporate_tax_data = backend_instance.db.get_corporate_tax(year) or {}

            # Tarih aralığı filtresi uygula (varsa)
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, "%d.%m.%Y")
                    end_dt = datetime.strptime(end_date, "%d.%m.%Y")

                    def _in_range(tarih):
                        try:
                            return start_dt <= datetime.strptime(tarih, "%d.%m.%Y") <= end_dt
                        except ValueError:
                            return False

                    income_invoices = [inv for inv in income_invoices if _in_range(inv.get("tarih", ""))]
                    expense_invoices = [inv for inv in expense_invoices if _in_range(inv.get("tarih", ""))]
                except ValueError:
                    pass

            # Aylık hesaplamalar
            monthly_income = [0.0] * 12
            monthly_expense = [0.0] * 12
            monthly_general = [0.0] * 12
            monthly_income_kdv = [0.0] * 12
            monthly_expense_kdv = [0.0] * 12
            monthly_corporate_tax = [0.0] * 12

            # Gelir faturalarını işle
            for invoice in income_invoices:
                tarih = invoice.get("tarih", "")
                if not tarih:
                    continue
                parts = tarih.split(".")
                if len(parts) != 3:
                    continue
                try:
                    month = int(parts[1])
                    invoice_year = int(parts[2])
                    if invoice_year == year:
                        monthly_income[month - 1] += float(
                            invoice.get("toplam_tutar_tl", 0)
                        )
                        monthly_income_kdv[month - 1] += float(
                            invoice.get("kdv_tutari", 0)
                        )
                except (ValueError, IndexError):
                    continue

            # Gider faturalarını işle
            for invoice in expense_invoices:
                tarih = invoice.get("tarih", "")
                if not tarih:
                    continue
                parts = tarih.split(".")
                if len(parts) != 3:
                    continue
                try:
                    month = int(parts[1])
                    invoice_year = int(parts[2])
                    if invoice_year == year:
                        monthly_expense[month - 1] += float(
                            invoice.get("toplam_tutar_tl", 0)
                        )
                        monthly_expense_kdv[month - 1] += float(
                            invoice.get("kdv_tutari", 0)
                        )
                except (ValueError, IndexError):
                    continue

            # Genel gider ve kurumlar vergisi
            month_keys = [
                "ocak",
                "subat",
                "mart",
                "nisan",
                "mayis",
                "haziran",
                "temmuz",
                "agustos",
                "eylul",
                "ekim",
                "kasim",
                "aralik",
            ]
            for i in range(12):
                month_key = month_keys[i]
                if month_key in general_expenses:
                    monthly_general[i] = float(general_expenses[month_key] or 0)
                if month_key in corporate_tax_data:
                    monthly_corporate_tax[i] = float(corporate_tax_data[month_key] or 0)

            # Aylık sonuçları hazırla
            monthly_results = []
            total_income = 0.0
            total_expense = 0.0

            for i in range(12):
                income = monthly_income[i]
                expense = monthly_expense[i]
                general = monthly_general[i]
                income_kdv = monthly_income_kdv[i]
                expense_kdv = monthly_expense_kdv[i]
                tax_percentage = monthly_corporate_tax[i]

                total_month_expense = expense + general
                taxable_base = income - total_month_expense
                kurumlar_vergisi = (
                    (taxable_base * tax_percentage / 100) if tax_percentage > 0 else 0
                )

                total_income += income
                total_expense += total_month_expense

                monthly_results.append(
                    {
                        "kesilen": income,
                        "gelen": total_month_expense,
                        "kdv": income_kdv - expense_kdv,
                        "kurumlar": kurumlar_vergisi,
                        "kurumlar_yuzde": tax_percentage,
                        "gelir_kdv": income_kdv,
                        "gider_kdv": expense_kdv,
                    }
                )

            # Çeyreklik sonuçları hesapla
            quarterly_results = []
            for q in range(4):
                start_month = q * 3
                quarter_kurumlar = sum(
                    monthly_results[start_month + j]["kurumlar"] for j in range(3)
                )
                quarterly_results.append({"odenecek_kv": quarter_kurumlar})

            total_kurumlar = sum(q["odenecek_kv"] for q in quarterly_results)
            sum(m["kdv"] for m in monthly_results)
            net_profit = total_income - total_expense - total_kurumlar

            summary = {
                "toplam_gelir": total_income,
                "toplam_gider": total_expense,
                "yillik_kar": net_profit,
            }

            return monthly_results, quarterly_results, summary

        btn_excel = create_styled_icon_button(
            ft.Icons.TABLE_VIEW, "#217346", tr("export_excel"), export_to_excel_donemsel
        )
        btn_pdf = create_styled_icon_button(
            ft.Icons.PICTURE_AS_PDF, "#D32F2F", tr("export_pdf"), export_to_pdf_donemsel
        )

        report_controls = ft.Container(
            padding=ft.padding.only(top=8, right=18, bottom=6),
            content=ft.Row([btn_excel, btn_pdf], spacing=6),
        )
        state["report_controls"] = report_controls

        top_bar = ft.Row(
            [ft.Container(height=38, content=year_dropdown), report_controls],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        return ft.Container(
            alignment=ft.alignment.top_center,
            padding=ft.padding.only(left=30, right=30, top=20, bottom=20),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                tr("reports_title"),
                                size=26,
                                weight="bold",
                                color="onBackground",
                            ),
                            ft.Row([
                                ft.Container(height=38, content=year_dropdown),
                                report_controls
                            ], spacing=8)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=15),
                    table_container,
                    ft.Container(height=50),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    # ------------------------------------------------------------------------
    # FATURALAR SAYFASI
    # ------------------------------------------------------------------------
    def create_invoices_page():
        def create_styled_icon_button(icon, color, tooltip, on_click):
            return ScaleButton(
                icon=icon,
                color=color,
                tooltip_text=tooltip,
                width=42,
                height=42,
                on_click=on_click,
            )

        # File Picker Handlers for Invoices
        def filter_invoices(invoices):
            start_str = export_filter_state.get("start")
            end_str = export_filter_state.get("end")
            if not start_str or not end_str:
                return invoices
            try:
                start_dt = datetime.strptime(start_str, "%d.%m.%Y")
                end_dt = datetime.strptime(end_str, "%d.%m.%Y")
                
                filtered = []
                for inv in invoices:
                    try:
                        inv_dt = datetime.strptime(inv.get("tarih", ""), "%d.%m.%Y")
                        if start_dt <= inv_dt <= end_dt:
                            filtered.append(inv)
                    except ValueError:
                        pass
                return filtered
            except ValueError:
                return invoices

        def on_save_invoices_excel_result(e: ft.FilePickerResultEvent):
            if e.path:
                file_path = e.path
                current_invoice_type = state.get("invoice_type", "income")
                db_type = "outgoing" if current_invoice_type == "income" else "incoming"
                type_name = (
                    tr("filename_outgoing_invoices")
                    if current_invoice_type == "income"
                    else tr("filename_incoming_invoices")
                )

                invoices = backend_instance.handle_invoice_operation(
                    operation="get", invoice_type=db_type
                )
                
                invoices = filter_invoices(invoices)

                if invoices:
                    from toexcel import InvoiceExcelExporter
                    excel_exporter = InvoiceExcelExporter()
                    current_lang = state.get("current_language", "tr")
                    success = excel_exporter.export_invoices_to_excel(
                        invoices, type_name, file_path, lang=current_lang
                    )

                    if success:
                        page.open(ft.SnackBar(content=ft.Text(tr("msg_file_saved").format(file_path), color=col_white), bgcolor=col_success,))
                        page.update()

        def on_save_invoices_pdf_result(e: ft.FilePickerResultEvent):
            if e.path:
                file_path = e.path
                current_invoice_type = state.get("invoice_type", "income")
                db_type = "outgoing" if current_invoice_type == "income" else "incoming"

                invoices = backend_instance.handle_invoice_operation(
                    operation="get", invoice_type=db_type
                )
                
                invoices = filter_invoices(invoices)

                if invoices:
                    from topdf import InvoicePDFExporter
                    pdf_exporter = InvoicePDFExporter()
                    current_lang = state.get("current_language", "tr")
                    success = pdf_exporter.export_invoices_to_pdf(
                        invoices, db_type, file_path, lang=current_lang
                    )

                    if success:
                        page.open(ft.SnackBar(content=ft.Text(tr("msg_file_saved").format(file_path), color=col_white), bgcolor=col_success,))
                        page.update()

        save_file_picker_invoices_excel = ft.FilePicker(on_result=on_save_invoices_excel_result)
        save_file_picker_invoices_pdf = ft.FilePicker(on_result=on_save_invoices_pdf_result)
        page.overlay.extend([save_file_picker_invoices_excel, save_file_picker_invoices_pdf])

        general_expenses_section = create_grid_expenses(page)
        general_expenses_section.visible = (state.get("invoice_type", "income") == "expense")

        selected_count_text = ft.Text("", size=12, color=col_danger, weight="bold", visible=False)

        invoice_snackbar_duration = 2500
        invoice_error_reset_delay = invoice_snackbar_duration
        invoice_error_reset_state = {"token": 0}
        invoice_alert_state = {"dialog": None}

        def normalize_invoice_amount(raw_value):
            normalized = (raw_value or "").strip().replace(" ", "")
            if not normalized:
                return None, tr("msg_total_required")
            if normalized.startswith("-"):
                return None, tr("msg_enter_valid_amount")

            normalized = normalized.replace(",", ".")
            parts = normalized.split(".")
            if len(parts) > 2 or not parts[0].isdigit():
                return None, tr("msg_enter_valid_amount")
            if len(parts) == 2:
                decimal_part = parts[1]
                if not decimal_part.isdigit() or len(decimal_part) > 4:
                    return None, tr("msg_enter_valid_amount")

            try:
                amount_value = float(normalized)
            except ValueError:
                return None, tr("msg_enter_valid_amount")

            if amount_value < 1 or amount_value >= 2147483648:
                return None, tr("msg_enter_valid_amount")

            return round(amount_value, 4), None

        def format_invoice_amount(amount_value):
            return f"{amount_value:.4f}".replace(".", ",")

        def schedule_invoice_error_reset(duration_ms):
            invoice_error_reset_state["token"] += 1
            current_token = invoice_error_reset_state["token"]

            async def clear_after_delay():
                import asyncio

                await asyncio.sleep(max(duration_ms, 0) / 1000)
                if invoice_error_reset_state["token"] == current_token:
                    reset_input_errors(cancel_pending=False)

            page.run_task(clear_after_delay)

        def show_invoice_snackbar(message, color=col_danger, reset_errors=False):
            page.open(
                ft.SnackBar(
                    content=ft.Text(message, color=col_white),
                    bgcolor=color,
                    duration=invoice_snackbar_duration,
                )
            )
            page.update()
            if reset_errors:
                schedule_invoice_error_reset(invoice_error_reset_delay)

        def close_invoice_alert(e=None):
            dialog = invoice_alert_state.get("dialog")
            if dialog is not None:
                page.close(dialog)
                invoice_alert_state["dialog"] = None

        def show_invoice_alert(message):
            close_invoice_alert()
            alert = ft.AlertDialog(
                modal=True,
                title=ft.Text(tr("warning")),
                content=ft.Text(message),
                actions=[ft.TextButton(tr("ok"), on_click=close_invoice_alert)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            invoice_alert_state["dialog"] = alert
            page.open(alert)

        def validate_required_text(control, message):
            value = (control.value or "").strip()
            if value:
                control.border_color = "outline"
                control.update()
                return True
            control.border_color = col_danger
            control.update()
            show_invoice_alert(message)
            return False

        def mark_invalid_with_alert(control, message):
            control.border_color = col_danger
            control.update()
            show_invoice_alert(message)
            return False

        def normalize_free_text(raw_value):
            return " ".join((raw_value or "").strip().split())

        def validate_company_value(raw_value):
            value = normalize_free_text(raw_value)
            if not value:
                return "", None
            if any(char in value for char in "*[]{}<>|~`"):
                return None, tr("msg_invalid_char_company")
            has_alnum = any(char.isalnum() for char in value)
            if not has_alnum or len(value) < 2:
                return None, tr("msg_invalid_value_company")
            return value, None

        def validate_item_value(raw_value):
            value = normalize_free_text(raw_value)
            if not value:
                return "", None
            if any(char in value for char in "*[]{}<>|~`"):
                return None, tr("msg_invalid_char_item")
            normalized_lower = value.casefold()
            if normalized_lower in {"firma", "company", "malzeme", "hizmet", "item", "service"}:
                return None, tr("msg_generic_item_value")
            if not any(char.isalpha() or char.isdigit() for char in value):
                return None, tr("msg_invalid_value_item")
            return value, None

        def validate_quantity_value(raw_value):
            value = normalize_free_text(raw_value)
            if not value:
                return "", None
            if any(char in value for char in "*[]{}<>|~`"):
                return None, tr("msg_enter_valid_quantity")
            if value.startswith("-"):
                return None, tr("msg_enter_valid_quantity")
            allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789çğıöşüÇĞİÖŞÜ .,/%+-")
            if any(char not in allowed_chars for char in value):
                return None, tr("msg_enter_valid_quantity")
            if not any(char.isdigit() for char in value):
                return None, tr("msg_enter_valid_quantity")
            return value, None

        def normalize_positive_decimal(raw_value, *, min_value=None, max_value=None, max_decimals=4):
            normalized = (raw_value or "").strip().replace(" ", "")
            if not normalized:
                return None, tr("msg_fill_required_fields")
            if normalized.startswith("-"):
                return None, tr("msg_enter_valid_amount")

            normalized = normalized.replace(",", ".")
            parts = normalized.split(".")
            if len(parts) > 2 or not parts[0].isdigit():
                return None, tr("msg_enter_valid_amount")
            if len(parts) == 2:
                decimal_part = parts[1]
                if not decimal_part.isdigit() or len(decimal_part) > max_decimals:
                    return None, tr("msg_enter_valid_amount")

            try:
                value = float(normalized)
            except ValueError:
                return None, tr("msg_enter_valid_amount")

            if min_value is not None and value < min_value:
                return None, tr("msg_enter_valid_amount")
            if max_value is not None and value > max_value:
                return None, tr("msg_enter_valid_amount")

            return round(value, max_decimals), None

        def get_invoice_table_rows():
            content = table_container.content
            if content and hasattr(content, "rows"):
                return content.rows
            if isinstance(content, ft.Column):
                for control in content.controls:
                    if hasattr(control, "rows"):
                        return control.rows
            return []

        def get_selected_invoice_rows():
            selected_rows = []
            for row in get_invoice_table_rows():
                if len(row.cells) > 0:
                    try:
                        cb = row.cells[0].content.content.content
                        if isinstance(cb, ft.Checkbox) and cb.value:
                            selected_rows.append(row)
                    except (AttributeError, TypeError):
                        pass
            return selected_rows

        def has_unsaved_invoice_inputs():
            field_values = [
                input_fatura_no.value,
                input_tarih.value,
                input_firma.value,
                input_malzeme.value,
                input_miktar.value,
                input_tutar.value,
                input_kdv.value,
                input_usd_kur.value,
                input_eur_kur.value,
            ]
            if any((value or "").strip() for value in field_values):
                return True
            return (input_para_birimi.value or "TL") != "TL"

        def on_tarih_blur(e):
            if e.control.value and e.control.value.strip():
                formatted = format_date_input(e.control.value.strip())
                if formatted != e.control.value:
                    e.control.value = formatted
                    e.control.update()
                try:
                    datetime.strptime(e.control.value, "%d.%m.%Y")
                    e.control.border_color = "outline"
                    e.control.update()
                except ValueError:
                    e.control.border_color = "outline"
                    e.control.update()
                    show_invoice_alert(tr("msg_enter_valid_date"))

        error_label_fatura_no = ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="red", size=18, visible=False, tooltip="")
        error_label_tutar = ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="red", size=18, visible=False, tooltip="")

        def reset_input_errors(cancel_pending=True):
            if cancel_pending:
                invoice_error_reset_state["token"] += 1
            input_fatura_no.border_color = "outline"
            input_firma.border_color = "outline"
            input_malzeme.border_color = "outline"
            input_miktar.border_color = "outline"
            input_tutar.border_color = "outline"
            input_tarih.border_color = "outline"
            input_kdv.border_color = "outline"
            input_usd_kur.border_color = "outline"
            input_eur_kur.border_color = "outline"
            page.update()

        def validate_invoice_form(summary_message=None):
            reset_input_errors()
            tutar_val = 0.0

            # --- Zorunlu alanlar boşsa: kırmızı border + alt SnackBar ---
            has_required_empty = False

            if not (input_fatura_no.value or "").strip():
                input_fatura_no.border_color = col_danger
                has_required_empty = True

            date_value = (input_tarih.value or "").strip()
            if not date_value:
                input_tarih.border_color = col_danger
                has_required_empty = True

            total_value = (input_tutar.value or "").strip()
            if not total_value:
                input_tutar.border_color = col_danger
                has_required_empty = True

            if has_required_empty:
                page.update()
                show_invoice_snackbar(tr("msg_fill_required_fields"), reset_errors=True)
                return None

            # --- Değer/format hatası varsa: merkez popup ---
            first_invalid_msg = ""

            if date_value:
                formatted = format_date_input(date_value)
                try:
                    datetime.strptime(formatted, "%d.%m.%Y")
                    input_tarih.value = formatted
                except ValueError:
                    first_invalid_msg = tr("msg_enter_valid_date")

            if not first_invalid_msg and total_value:
                tutar_val, amount_error = normalize_invoice_amount(total_value)
                if amount_error:
                    first_invalid_msg = amount_error
                else:
                    input_tutar.value = format_invoice_amount(tutar_val)

            normalized_company, company_error = validate_company_value(input_firma.value)
            if company_error:
                if not first_invalid_msg:
                    first_invalid_msg = company_error
            else:
                input_firma.value = normalized_company

            normalized_item, item_error = validate_item_value(input_malzeme.value)
            if item_error:
                if not first_invalid_msg:
                    first_invalid_msg = item_error
            else:
                input_malzeme.value = normalized_item

            normalized_quantity, quantity_error = validate_quantity_value(input_miktar.value)
            if quantity_error:
                if not first_invalid_msg:
                    first_invalid_msg = quantity_error
            else:
                input_miktar.value = normalized_quantity

            if input_kdv.value and input_kdv.value.strip():
                normalized_kdv, kdv_error = normalize_positive_decimal(
                    input_kdv.value,
                    min_value=0,
                    max_value=100,
                )
                if kdv_error:
                    if not first_invalid_msg:
                        first_invalid_msg = tr("msg_enter_valid_value").format(tr("vat_amount"))
                else:
                    input_kdv.value = format_invoice_amount(normalized_kdv)

            if input_usd_kur.value and input_usd_kur.value.strip():
                normalized_usd, usd_error = normalize_positive_decimal(
                    input_usd_kur.value,
                    min_value=0.01,
                    max_value=1000,
                )
                if usd_error:
                    if not first_invalid_msg:
                        first_invalid_msg = tr("msg_enter_valid_value").format(tr("usd_rate_label"))
                else:
                    input_usd_kur.value = format_invoice_amount(normalized_usd)

            if input_eur_kur.value and input_eur_kur.value.strip():
                normalized_eur, eur_error = normalize_positive_decimal(
                    input_eur_kur.value,
                    min_value=0.01,
                    max_value=1000,
                )
                if eur_error:
                    if not first_invalid_msg:
                        first_invalid_msg = tr("msg_enter_valid_value").format(tr("eur_rate_label"))
                else:
                    input_eur_kur.value = format_invoice_amount(normalized_eur)

            if first_invalid_msg:
                show_invoice_alert(first_invalid_msg)
                return None

            return tutar_val

        def create_professional_input(hint, expand=1, on_blur=None, is_dropdown=False, options=None, value=None):
            if is_dropdown:
                c = ft.Dropdown(
                    options=options if options else [],
                    value=value,
                    hint_text=hint,
                    text_size=12,
                    border=ft.InputBorder.OUTLINE,
                    border_color="outline",
                    focused_border_color=col_primary,
                    border_radius=8,
                    bgcolor="surface",
                    content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
                    expand=expand
                )
            else:
                c = ft.TextField(
                    hint_text=hint,
                    text_size=12,
                    border=ft.InputBorder.OUTLINE,
                    border_color="outline",
                    focused_border_color=col_primary,
                    border_radius=8,
                    bgcolor="surface",
                    content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
                    on_blur=on_blur,
                    expand=expand
                )
            c.height = 40
            return c

        def form_label(text, trailing=None):
            controls = [ft.Text(text, size=12, weight="w600")]
            if trailing is not None:
                controls.append(trailing)
            return ft.Container(
                height=22,
                alignment=ft.alignment.center_left,
                content=ft.Row(
                    controls,
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        input_fatura_no = create_professional_input(tr("hint_invoice_no"))
        input_tarih = create_professional_input(tr("hint_date"), on_blur=on_tarih_blur)
        input_tarih.expand = True

        def on_tutar_blur(e):
            amount_value = (e.control.value or "").strip()
            if not amount_value:
                return
            parsed_amount, amount_error = normalize_invoice_amount(amount_value)
            if amount_error:
                e.control.border_color = col_danger
                e.control.update()
                show_invoice_alert(amount_error)
                return

            e.control.value = format_invoice_amount(parsed_amount)
            e.control.border_color = "outline"
            e.control.update()

        def on_firma_blur(e):
            normalized_value, error_message = validate_company_value(e.control.value)
            if error_message:
                mark_invalid_with_alert(e.control, error_message)
                return
            e.control.value = normalized_value
            e.control.border_color = "outline"
            e.control.update()

        def on_malzeme_blur(e):
            normalized_value, error_message = validate_item_value(e.control.value)
            if error_message:
                mark_invalid_with_alert(e.control, error_message)
                return
            e.control.value = normalized_value
            e.control.border_color = "outline"
            e.control.update()

        def on_miktar_blur(e):
            normalized_value, error_message = validate_quantity_value(e.control.value)
            if error_message:
                mark_invalid_with_alert(e.control, error_message)
                return
            e.control.value = normalized_value
            e.control.border_color = "outline"
            e.control.update()

        def pick_invoice_date(e):
            def on_date_change(ev):
                input_tarih.value = ev.control.value.strftime("%d.%m.%Y")
                input_tarih.border_color = "outline"
                input_tarih.update()
            page.open(ft.DatePicker(on_change=on_date_change))

        date_label = form_label(
            tr("date"),
            ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_size=16,
                icon_color=col_text_light,
                tooltip=tr("go_to_date"),
                on_click=pick_invoice_date,
                style=ft.ButtonStyle(padding=ft.padding.all(0)),
                width=22,
                height=22,
            ),
        )

        input_firma = create_professional_input(tr("hint_company"), on_blur=on_firma_blur)
        input_malzeme = create_professional_input(tr("hint_item"), on_blur=on_malzeme_blur)
        input_miktar = create_professional_input(tr("hint_amount"), on_blur=on_miktar_blur)
        input_tutar = create_professional_input(tr("hint_total"), on_blur=on_tutar_blur)
        input_para_birimi = create_professional_input(
            tr("hint_currency"), 
            is_dropdown=True, 
            options=[ft.dropdown.Option("TL"), ft.dropdown.Option("USD"), ft.dropdown.Option("EUR")],
            value="TL"
        )
        input_kdv = create_professional_input(tr("hint_vat"))
        input_usd_kur = create_professional_input(tr("optional_tcmb"))
        input_eur_kur = create_professional_input(tr("optional_tcmb"))

        def on_optional_decimal_blur(control, label, min_value, max_value):
            control_value = (control.value or "").strip()
            if not control_value:
                control.border_color = "outline"
                control.update()
                return
            normalized_value, value_error = normalize_positive_decimal(
                control_value,
                min_value=min_value,
                max_value=max_value,
            )
            if value_error:
                control.border_color = col_danger
                control.update()
                show_invoice_alert(tr("msg_enter_valid_value").format(label))
                return
            control.value = format_invoice_amount(normalized_value)
            control.border_color = "outline"
            control.update()

        input_kdv.on_blur = lambda e: on_optional_decimal_blur(e.control, tr("vat_amount"), 0, 100)
        input_usd_kur.on_blur = lambda e: on_optional_decimal_blur(e.control, tr("usd_rate_label"), 0.01, 1000)
        input_eur_kur.on_blur = lambda e: on_optional_decimal_blur(e.control, tr("eur_rate_label"), 0.01, 1000)

        # Dil değişiminde form değerlerini koru: kaydedilmiş değerleri yükle
        _saved_inputs = state.pop("_invoice_form_values", {})
        if _saved_inputs:
            input_fatura_no.value = _saved_inputs.get("fatura_no", "")
            input_tarih.value = _saved_inputs.get("tarih", "")
            input_firma.value = _saved_inputs.get("firma", "")
            input_malzeme.value = _saved_inputs.get("malzeme", "")
            input_miktar.value = _saved_inputs.get("miktar", "")
            input_tutar.value = _saved_inputs.get("tutar", "")
            input_para_birimi.value = _saved_inputs.get("birim", "TL")
            input_kdv.value = _saved_inputs.get("kdv", "")
            input_usd_kur.value = _saved_inputs.get("usd_kur", "")
            input_eur_kur.value = _saved_inputs.get("eur_kur", "")

        def _get_invoice_form_values():
            return {
                "fatura_no": input_fatura_no.value or "",
                "tarih": input_tarih.value or "",
                "firma": input_firma.value or "",
                "malzeme": input_malzeme.value or "",
                "miktar": input_miktar.value or "",
                "tutar": input_tutar.value or "",
                "birim": input_para_birimi.value or "TL",
                "kdv": input_kdv.value or "",
                "usd_kur": input_usd_kur.value or "",
                "eur_kur": input_eur_kur.value or "",
            }
        state["_get_invoice_form_values"] = _get_invoice_form_values

        def fill_form_from_invoice(invoice):
            """Fatura verisini form alanlarına yükler"""
            input_fatura_no.value = str(invoice.get("fatura_no", ""))
            input_tarih.value = str(invoice.get("tarih", ""))
            input_firma.value = str(invoice.get("firma", ""))
            input_malzeme.value = str(invoice.get("malzeme", ""))
            input_miktar.value = str(invoice.get("miktar", ""))
            birim = str(invoice.get("birim", "TL"))
            input_para_birimi.value = birim
            matrah = invoice.get("matrah", 0)
            kdv_yuzdesi = float(invoice.get("kdv_yuzdesi", 20.0))
            usd_rate = float(invoice.get("usd_rate", 0))
            eur_rate = float(invoice.get("eur_rate", 0))
            if matrah and matrah > 0:
                input_tutar.value = format_invoice_amount(round(float(matrah), 4))
            else:
                kdv_tutari_tl = float(invoice.get("kdv_tutari", 0))
                if birim == "TL":
                    toplam_tutar = round(float(invoice.get("toplam_tutar_tl", 0)), 5)
                    tutar = toplam_tutar - kdv_tutari_tl
                elif birim == "USD":
                    toplam_tutar = round(float(invoice.get("toplam_tutar_usd", 0)), 5)
                    if usd_rate > 0:
                        tutar = toplam_tutar - (kdv_tutari_tl / usd_rate)
                    else:
                        tutar = toplam_tutar / (1 + kdv_yuzdesi / 100)
                elif birim == "EUR":
                    toplam_tutar = round(float(invoice.get("toplam_tutar_eur", 0)), 5)
                    if eur_rate > 0:
                        tutar = toplam_tutar - (kdv_tutari_tl / eur_rate)
                    else:
                        tutar = toplam_tutar / (1 + kdv_yuzdesi / 100)
                else:
                    toplam_tutar = round(float(invoice.get("toplam_tutar_tl", 0)), 5)
                    tutar = toplam_tutar - kdv_tutari_tl
                input_tutar.value = format_invoice_amount(round(tutar, 4)) if tutar else "0"
            input_kdv.value = format_invoice_amount(round(kdv_yuzdesi, 4))
            input_usd_kur.value = format_invoice_amount(round(usd_rate, 4)) if usd_rate and usd_rate > 0 else ""
            input_eur_kur.value = format_invoice_amount(round(eur_rate, 4)) if eur_rate and eur_rate > 0 else ""
            for ctrl in [input_fatura_no, input_tarih, input_firma, input_malzeme,
                         input_miktar, input_tutar, input_para_birimi, input_kdv,
                         input_usd_kur, input_eur_kur]:
                ctrl.update()

        def update_selected_count(e=None):
            try:
                selected_rows = get_selected_invoice_rows()
                selected_count = len(selected_rows)
                if selected_count > 0:
                    selected_count_text.value = f"({selected_count})"
                    selected_count_text.visible = True
                else:
                    selected_count_text.value = ""
                    selected_count_text.visible = False
                    state["editing_invoice_id"] = None
                selected_count_text.update()
                table_container.update()
                page.update()
            except Exception:
                pass

        INVOICE_PAGE_SIZE = 25
        invoice_pagination = {"page": 0, "total": 0}

        initial_table_content = create_invoice_table_content("newest", state.get("invoice_type", "income"), on_select_changed=update_selected_count, theme_mode=page.theme_mode, container_width=page.width - 40, limit=INVOICE_PAGE_SIZE, offset=0)

        _initial_empty = getattr(initial_table_content, "data", {}).get("row_count", 0) == 0
        table_container = ft.Container(
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000", offset=ft.Offset(0, 5)),
            bgcolor="surface",
            height=310 if _initial_empty else None,
            content=initial_table_content,
        )

        _page_label = ft.Text("", size=12, color=col_text_light)
        _prev_page_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
            icon_size=20,
            disabled=True,
            tooltip="Önceki sayfa",
        )
        _next_page_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
            icon_size=20,
            disabled=True,
            tooltip="Sonraki sayfa",
        )
        _pagination_bar = ft.Row(
            [_prev_page_btn, _page_label, _next_page_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
        )

        def update_invoice_table(sort_option=None, reset_page=False):
            if state["current_page"] != "invoices" and state["current_page"] != "faturalar":
                return
            if sort_option is None:
                sort_option = state.get("invoice_sort_option", "newest")
            current_invoice_type = state.get("invoice_type", "income")
            is_expense = current_invoice_type == "expense"

            income_btn.bgcolor = col_secondary if not is_expense else "surfaceVariant"
            income_btn.content.controls[0].color = col_white if not is_expense else col_secondary
            income_btn.content.controls[1].color = col_white if not is_expense else col_text_light

            expense_btn.bgcolor = col_primary if is_expense else "surfaceVariant"
            expense_btn.content.controls[0].color = col_white if is_expense else col_primary
            expense_btn.content.controls[1].color = col_white if is_expense else col_text_light

            general_expenses_section.visible = is_expense

            # Sayfalama hesapla
            if reset_page:
                invoice_pagination["page"] = 0
            db_type = "outgoing" if current_invoice_type == "income" else "incoming"
            try:
                total = backend_instance.get_invoice_count(db_type)
            except Exception:
                total = 0
            invoice_pagination["total"] = total
            total_pages = max(1, (total + INVOICE_PAGE_SIZE - 1) // INVOICE_PAGE_SIZE)
            cur_page = min(invoice_pagination["page"], total_pages - 1)
            invoice_pagination["page"] = cur_page
            offset = cur_page * INVOICE_PAGE_SIZE

            # Tabloyu yenile
            table_container.content = create_invoice_table_content(sort_option, current_invoice_type, on_select_changed=update_selected_count, theme_mode=page.theme_mode, container_width=page.width - 40, limit=INVOICE_PAGE_SIZE, offset=offset)
            _is_empty = getattr(table_container.content, "data", {}).get("row_count", 0) == 0
            table_container.height = 310 if _is_empty else None

            # Sayfalama barını güncelle
            _page_label.value = f"{tr('pagination_page_of').format(cur_page + 1, total_pages)}  •  {tr('pagination_records').format(total)}"
            _prev_page_btn.disabled = cur_page == 0
            _next_page_btn.disabled = cur_page >= total_pages - 1

            if income_btn.page: income_btn.update()
            if expense_btn.page: expense_btn.update()
            if general_expenses_section.page: general_expenses_section.update()
            if table_container.page: table_container.update()
            if _pagination_bar.page: _pagination_bar.update()
            page.update()

        state["update_callbacks"]["invoice_page"] = update_invoice_table

        def _go_prev_invoice_page(e):
            if invoice_pagination["page"] > 0:
                invoice_pagination["page"] -= 1
                update_invoice_table()

        def _go_next_invoice_page(e):
            total_pages = max(1, (invoice_pagination["total"] + INVOICE_PAGE_SIZE - 1) // INVOICE_PAGE_SIZE)
            if invoice_pagination["page"] < total_pages - 1:
                invoice_pagination["page"] += 1
                update_invoice_table()

        _prev_page_btn.on_click = _go_prev_invoice_page
        _next_page_btn.on_click = _go_next_invoice_page

        def on_sort_change(e):
            update_invoice_table(e.control.value, reset_page=True)

        def set_invoice_type(inv_type):
            state["invoice_type"] = inv_type
            update_invoice_table(state.get("invoice_sort_option", "newest"), reset_page=True)

        initial_is_expense = state.get("invoice_type", "income") == "expense"
        
        income_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.TRENDING_UP_ROUNDED, color=col_white if not initial_is_expense else col_secondary, size=18),
                ft.Text(tr("outgoing_invoices"), color=col_white if not initial_is_expense else col_text_light, weight="bold", size=13),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=col_secondary if not initial_is_expense else "surfaceVariant",
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=8,
            on_click=lambda _: set_invoice_type("income"),
            animate=ft.Animation(200, "easeOut"),
        )
        
        expense_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.TRENDING_DOWN_ROUNDED, color=col_white if initial_is_expense else col_primary, size=18),
                ft.Text(tr("incoming_invoices"), color=col_white if initial_is_expense else col_text_light, weight="bold", size=13),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=col_primary if initial_is_expense else "surfaceVariant",
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=8,
            on_click=lambda _: set_invoice_type("expense"),
            animate=ft.Animation(200, "easeOut"),
        )

        type_selector = ft.Row([income_btn, expense_btn], spacing=10)

        def clear_inputs(e=None, force=False, show_message=True):
            try:
                if not force and not get_selected_invoice_rows() and not has_unsaved_invoice_inputs():
                    show_invoice_snackbar(tr("msg_nothing_to_clear"))
                    return

                input_fatura_no.value = ""
                input_tarih.value = ""
                input_firma.value = ""
                input_malzeme.value = ""
                input_miktar.value = ""
                input_tutar.value = ""
                input_para_birimi.value = "TL"
                input_kdv.value = ""
                input_usd_kur.value = ""
                input_eur_kur.value = ""
                reset_input_errors()
                state["selected_invoice_id"] = None
                for row in get_invoice_table_rows():
                    if len(row.cells) > 0:
                        try:
                            cb = row.cells[0].content.content.content
                            if isinstance(cb, ft.Checkbox):
                                cb.value = False
                        except (AttributeError, TypeError):
                            pass
                selected_count_text.value = ""
                selected_count_text.visible = False
                if show_message:
                    show_invoice_snackbar(tr("msg_form_cleared"))
                page.update()
            except Exception:
                pass

        def add_invoice(e):
            try:
                tutar_val = validate_invoice_form(
                    summary_message=tr("msg_complete_invoice_fields"),
                )
                if tutar_val is None:
                    return

                invoice_data = {
                    "fatura_no": input_fatura_no.value or "",
                    "tarih": input_tarih.value or "",
                    "firma": input_firma.value or "",
                    "malzeme": input_malzeme.value or "",
                    "miktar": input_miktar.value or "",
                    "toplam_tutar": tutar_val,
                    "birim": input_para_birimi.value or "TL",
                    "kdv_yuzdesi": float(input_kdv.value.replace(",", ".")) if input_kdv.value else 20.0,
                }
                if input_usd_kur.value and input_usd_kur.value.strip():
                    try:
                        invoice_data["manual_usd_rate"] = float(
                            input_usd_kur.value.replace(",", ".")
                        )
                    except ValueError:
                        pass
                if input_eur_kur.value and input_eur_kur.value.strip():
                    try:
                        invoice_data["manual_eur_rate"] = float(
                            input_eur_kur.value.replace(",", ".")
                        )
                    except ValueError:
                        pass

                processed_data = process_invoice(invoice_data)
                if processed_data:
                    invoice_type = "incoming" if state["invoice_type"] == "expense" else "outgoing"
                    result = backend_instance.handle_invoice_operation("add", invoice_type, processed_data)
                    if result:
                        update_invoice_table(state.get("invoice_sort_option", "newest"), reset_page=True)
                        clear_inputs(force=True, show_message=False)
                        if state["update_callbacks"]["home_page"]: state["update_callbacks"]["home_page"]()
                        if state["update_callbacks"]["transaction_history"]: state["update_callbacks"]["transaction_history"]()
                        # Döviz faturalarında eski/önbellekte kur kullanıldıysa ekstra uyarı
                        birim = invoice_data.get("birim", "TL")
                        rates_src = getattr(backend_instance, "rates_source", "live")
                        manual_key = "manual_usd_rate" if birim == "USD" else "manual_eur_rate"
                        used_manual_rate = manual_key in invoice_data
                        if birim in ("USD", "EUR") and rates_src in ("cache", "default") and not used_manual_rate:
                            show_invoice_snackbar(
                                get_text("msg_stale_rates_invoice", state.get("current_language", "tr")).format(birim),
                                "#FF9F43",
                            )
                        else:
                            show_invoice_snackbar(tr("msg_invoice_added"), col_success)
                    else:
                        show_invoice_snackbar(tr("msg_invoice_add_error"))
            except Exception as ex:
                show_invoice_snackbar(tr("msg_error_prefix").format(str(ex)))

        def update_invoice(e):
            try:
                selected_rows = get_selected_invoice_rows()
                if not selected_rows:
                    show_invoice_snackbar(tr("msg_select_to_update"))
                    return
                if len(selected_rows) > 1:
                    show_invoice_snackbar(tr("msg_select_one"))
                    return

                row_data = selected_rows[0].data
                invoice_id = (
                    row_data.get("id") if isinstance(row_data, dict) else row_data
                )
                editing_id = state.get("editing_invoice_id")

                if editing_id != invoice_id:
                    # 1. tıklama: formu doldur, düzenleme moduna gir
                    if isinstance(selected_rows[0].data, dict):
                        fill_form_from_invoice(selected_rows[0].data)
                        state["editing_invoice_id"] = invoice_id
                    return

                # 2. tıklama: kaydet
                tutar_val = validate_invoice_form()
                if tutar_val is None:
                    return
                invoice_data = {
                    "fatura_no": input_fatura_no.value or "",
                    "tarih": input_tarih.value or "",
                    "firma": input_firma.value or "",
                    "malzeme": input_malzeme.value or "",
                    "miktar": input_miktar.value or "",
                    "toplam_tutar": tutar_val,
                    "birim": input_para_birimi.value or "TL",
                    "kdv_yuzdesi": float(input_kdv.value.replace(",", ".")) if input_kdv.value else 20.0,
                }
                if input_usd_kur.value and input_usd_kur.value.strip():
                    try:
                        invoice_data["manual_usd_rate"] = float(
                            input_usd_kur.value.replace(",", ".")
                        )
                    except ValueError:
                        pass
                if input_eur_kur.value and input_eur_kur.value.strip():
                    try:
                        invoice_data["manual_eur_rate"] = float(
                            input_eur_kur.value.replace(",", ".")
                        )
                    except ValueError:
                        pass
                if processed_data := process_invoice(invoice_data):
                    invoice_type = (
                        "incoming" if state["invoice_type"] == "expense" else "outgoing"
                    )
                    updated = backend_instance.handle_invoice_operation(
                        "update", invoice_type, processed_data, record_id=invoice_id
                    )
                    if updated:
                        state["editing_invoice_id"] = None
                        update_invoice_table()
                        # Kaydedilen satırı tekrar seç ve formu güncel veriyle doldur
                        for row in get_invoice_table_rows():
                            if isinstance(row.data, dict) and row.data.get("id") == invoice_id:
                                try:
                                    cb = row.cells[0].content.content.content
                                    if isinstance(cb, ft.Checkbox):
                                        cb.value = True
                                except (AttributeError, TypeError):
                                    pass
                                if isinstance(row.data, dict):
                                    fill_form_from_invoice(row.data)
                                break
                        update_selected_count()
                        if state["update_callbacks"]["home_page"]: state["update_callbacks"]["home_page"]()
                        show_invoice_snackbar(tr("msg_invoice_updated"), col_success)
                    else:
                        show_invoice_snackbar(tr("msg_update_error"))
            except Exception as ex:
                show_invoice_snackbar(tr("msg_update_error_prefix").format(str(ex)))

        def show_delete_all_dialog():
            """Sağ tık ile tetiklenir — mevcut türdeki TÜM faturaları siler."""
            try:
                current_invoice_type = state.get("invoice_type", "income")
                db_type = "outgoing" if current_invoice_type == "income" else "incoming"
                total_count = backend_instance.get_invoice_count(db_type)
                if total_count == 0:
                    show_invoice_snackbar(tr("msg_select_to_delete"))
                    return

                dlg_all = None

                def close_dlg_all(e):
                    dlg_all.open = False
                    page.update()

                def confirm_delete_all(e):
                    dlg_all.open = False
                    page.update()
                    original_callback = backend_instance.on_data_updated
                    backend_instance.on_data_updated = None
                    deleted = backend_instance.delete_all_invoices(db_type)
                    backend_instance.on_data_updated = original_callback
                    update_invoice_table(reset_page=True)
                    clear_inputs(force=True, show_message=False)
                    if original_callback:
                        original_callback()
                    if state["update_callbacks"]["home_page"]:
                        state["update_callbacks"]["home_page"]()
                    if state["update_callbacks"]["transaction_history"]:
                        state["update_callbacks"]["transaction_history"]()
                    show_invoice_snackbar(
                        tr("delete_all_success").format(deleted), col_success
                    )

                dlg_all = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=col_danger, size=22),
                        ft.Container(width=8),
                        ft.Text(tr("delete_all_confirm_title"), color=col_danger, weight="bold"),
                    ]),
                    content=ft.Text(
                        tr("delete_all_confirm_msg").format(total_count),
                        size=14,
                    ),
                    actions=[
                        ft.ElevatedButton(
                            tr("yes"),
                            on_click=confirm_delete_all,
                            bgcolor=col_danger,
                            color=col_white,
                        ),
                        ft.ElevatedButton(
                            tr("no"),
                            on_click=close_dlg_all,
                            bgcolor="surfaceVariant",
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.overlay.append(dlg_all)
                dlg_all.open = True
                page.update()
            except Exception as ex:
                show_invoice_snackbar(tr("msg_delete_error_prefix").format(str(ex)))

        def delete_invoice(e):
            try:
                # ── Sadece seçili satırlar ──
                selected_rows = get_selected_invoice_rows()
                if not selected_rows:
                    show_invoice_snackbar(tr("msg_select_to_delete"))
                    return
                
                dlg_modal = None
                def close_dlg(e):
                    dlg_modal.open = False
                    page.update()
                
                def confirm_delete(e):
                    dlg_modal.open = False
                    page.update()
                    current_invoice_type = state.get("invoice_type", "income")
                    db_type = "outgoing" if current_invoice_type == "income" else "incoming"
                    original_callback = backend_instance.on_data_updated
                    backend_instance.on_data_updated = None
                    deleted_count = 0
                    for row in selected_rows:
                        if isinstance(row.data, dict) and "id" in row.data:
                            if backend_instance.handle_invoice_operation("delete", db_type, record_id=row.data["id"]):
                                deleted_count += 1
                    backend_instance.on_data_updated = original_callback
                    update_invoice_table()
                    clear_inputs(force=True, show_message=False)
                    if original_callback: original_callback()
                    if deleted_count > 0:
                        show_invoice_snackbar(tr("msg_deleted_count").format(deleted_count), col_success)
                    else:
                        show_invoice_snackbar(tr("msg_delete_error"))

                dlg_modal = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(tr("delete_confirm_title")),
                    content=ft.Text(tr("delete_confirm_msg_multi").format(len(selected_rows))),
                    actions=[
                        ft.ElevatedButton(tr("yes"), on_click=confirm_delete, bgcolor=col_success, color=col_white),
                        ft.ElevatedButton(tr("no"), on_click=close_dlg, bgcolor=col_danger, color=col_white),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.overlay.append(dlg_modal)
                dlg_modal.open = True
                page.update()
            except Exception as ex:
                show_invoice_snackbar(tr("msg_delete_error_prefix").format(str(ex)))

        def process_qr_folder(e):
            try:
                def on_files_selected(e: ft.FilePickerResultEvent):
                    if not e.files:
                        return
                    file_paths = [f.path for f in e.files if f.path]
                    if not file_paths:
                        return

                    progress_text = ft.Text(tr("reading_qr_codes"), size=13, color="onBackground")
                    progress_bar = ft.ProgressBar(value=None, color="#3498DB", bgcolor="surfaceVariant", width=340)
                    progress_dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Row([
                            ft.Icon(ft.Icons.QR_CODE_SCANNER, color="#3498DB", size=22),
                            ft.Container(width=8),
                            ft.Text(tr("qr_processing_title"), color="onBackground", size=16, weight="bold"),
                        ]),
                        content=ft.Container(
                            width=340,
                            content=ft.Column([
                                progress_bar,
                                ft.Container(height=8),
                                progress_text,
                            ], tight=True),
                        ),
                        bgcolor="surface",
                    )

                    def show_progress():
                        page.open(progress_dlg)

                    def hide_progress():
                        progress_dlg.open = False
                        page.update()

                    def status_callback(msg, progress_val):
                        progress_text.value = msg
                        progress_bar.value = (progress_val / 100.0) if progress_val else None
                        page.update()
                        return True

                    def process_in_thread(selected_type):
                        try:
                            time.sleep(0.1)
                            results = backend_instance.process_qr_file_list(
                                file_paths, max_workers=8,
                                status_callback=status_callback,
                                lang=state.get("current_language", "tr"),
                            )
                            if not results:
                                hide_progress()
                                page.open(ft.SnackBar(content=ft.Text(tr("msg_qr_no_files"), color=col_white), bgcolor=col_danger))
                                page.update()
                                return
                            backend_instance.add_invoices_from_qr_data(results, selected_type)
                            hide_progress()
                            update_invoice_table(reset_page=True)
                            page.open(ft.SnackBar(content=ft.Text(tr("process_completed"), color=col_white), bgcolor=col_success))
                            page.update()
                        except Exception as ex:
                            hide_progress()
                            page.open(ft.SnackBar(content=ft.Text(tr("qr_error_prefix").format(str(ex)), color=col_white), bgcolor=col_danger))
                            page.update()

                    def on_type_selected(invoice_type, bs_ref):
                        bs_ref.open = False
                        page.update()
                        show_progress()
                        threading.Thread(target=process_in_thread, args=(invoice_type,), daemon=True).start()

                    bs = ft.BottomSheet(
                        content=ft.Container(
                            padding=20,
                            bgcolor="surface",
                            content=ft.Column([
                                ft.Text(tr("select_invoice_type"), size=20, weight="bold", color="onBackground"),
                                ft.Container(height=10),
                                ft.ElevatedButton(tr("income_sales_invoice"), on_click=lambda _: on_type_selected("outgoing", bs), bgcolor=col_success, width=300, height=50),
                                ft.Container(height=10),
                                ft.ElevatedButton(tr("expense_purchase_invoice"), on_click=lambda _: on_type_selected("incoming", bs), bgcolor=col_danger, width=300, height=50),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True)
                        ),
                        open=True,
                    )
                    page.overlay.append(bs)
                    page.update()

                file_picker = ft.FilePicker(on_result=on_files_selected)
                page.overlay.append(file_picker)
                page.update()
                file_picker.pick_files(
                    dialog_title=tr("qr_folder_dialog_title"),
                    allow_multiple=True,
                    allowed_extensions=["pdf", "jpg", "jpeg", "png", "bmp"],
                )
            except Exception as ex:
                page.open(ft.SnackBar(content=ft.Text(tr("qr_error_prefix").format(str(ex)), color=col_white), bgcolor=col_danger))
                page.update()

        def backup_database(e):
            try:
                from backup import LocalBackupManager
                manager = LocalBackupManager(database_folder=os.path.join(PROJECT_ROOT, "Database"))
                def on_save_result(e: ft.FilePickerResultEvent):
                    if e.path:
                        success, msg = manager.create_backup(e.path)
                        if success:
                            page.open(ft.SnackBar(content=ft.Text(tr("backup_success_title"), color=col_white), bgcolor=col_success))
                            page.update()
                save_file_picker = ft.FilePicker(on_result=on_save_result)
                page.overlay.append(save_file_picker)
                page.update()
                save_file_picker.save_file(file_name=manager.get_default_filename())
            except Exception as ex:
                page.open(ft.SnackBar(content=ft.Text(tr("backup_error_prefix").format(str(ex)), color=col_white), bgcolor=col_danger))
                page.update()

        def restore_database(e):
            try:
                from backup import LocalBackupManager
                manager = LocalBackupManager(database_folder=os.path.join(PROJECT_ROOT, "Database"))

                def do_restore(zip_path):
                    success, msg = manager.restore_backup(zip_path)
                    if success:
                        reinit_ok = backend_instance.reinitialize_db()
                        if reinit_ok:
                            for cb in state["update_callbacks"].values():
                                if cb:
                                    try:
                                        cb()
                                    except Exception:
                                        pass
                        page.open(ft.SnackBar(content=ft.Text(tr("restore_success"), color=col_white), bgcolor=col_success))
                    else:
                        page.open(ft.SnackBar(content=ft.Text(tr("restore_error_prefix").format(msg), color=col_white), bgcolor=col_danger))
                    page.update()

                def on_confirm(zip_path, dlg_ref):
                    dlg_ref.open = False
                    page.update()
                    threading.Thread(target=do_restore, args=(zip_path,), daemon=True).start()

                def on_file_selected(e: ft.FilePickerResultEvent):
                    if not e.files:
                        return
                    zip_path = e.files[0].path if e.files and e.files[0].path else None
                    if not zip_path:
                        return
                    confirm_dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text(tr("restore_confirm_title"), color="onBackground", weight="bold"),
                        content=ft.Text(tr("restore_confirm_msg"), color="onSurfaceVariant", size=13),
                        bgcolor="surface",
                        actions=[
                            ft.TextButton(tr("yes"), on_click=lambda _: on_confirm(zip_path, confirm_dlg),
                                          style=ft.ButtonStyle(color=col_danger)),
                            ft.TextButton(tr("no"), on_click=lambda _: setattr(confirm_dlg, "open", False) or page.update(),
                                          style=ft.ButtonStyle(color="onSurface")),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.open(confirm_dlg)

                open_picker = ft.FilePicker(on_result=on_file_selected)
                page.overlay.append(open_picker)
                page.update()
                open_picker.pick_files(
                    dialog_title=tr("restore_select_zip"),
                    allow_multiple=False,
                    allowed_extensions=["zip"],
                )
            except Exception as ex:
                page.open(ft.SnackBar(content=ft.Text(tr("restore_error_prefix").format(str(ex)), color=col_white), bgcolor=col_danger))
                page.update()

        # --- EXPORT DIALOG AND FILTERING ---
        export_start_date = ft.TextField(
            hint_text=tr("date_hint"),
            label=tr("label_start_date"),
            width=140,
            text_size=12,
            height=40,
            bgcolor="surface",
            border_color="outline",
            focused_border_color="primary",
            border_radius=8,
        )

        def pick_export_start_date(e):
            def on_change(e):
                export_start_date.value = e.control.value.strftime("%d.%m.%Y")
                export_start_date.update()
            page.open(ft.DatePicker(on_change=on_change))

        export_end_date = ft.TextField(
            hint_text=tr("date_hint"),
            label=tr("label_end_date"),
            width=140,
            text_size=12,
            height=40,
            bgcolor="surface",
            border_color="outline",
            focused_border_color="primary",
            border_radius=8,
        )

        def pick_export_end_date(e):
            def on_change(e):
                export_end_date.value = e.control.value.strftime("%d.%m.%Y")
                export_end_date.update()
            page.open(ft.DatePicker(on_change=on_change))

        export_current_format = {"format": "excel"}
        export_filter_state = {"start": None, "end": None}

        def execute_export():
            export_dialog.open = False
            page.update()
            current_invoice_type = state.get("invoice_type", "income")
            type_name = tr("filename_outgoing_invoices") if current_invoice_type == "income" else tr("filename_incoming_invoices")
            if export_current_format["format"] == "excel":
                save_file_picker_invoices_excel.save_file(file_name=f"{type_name}_{datetime.now().strftime('%d-%m-%Y')}.xlsx")
            else:
                save_file_picker_invoices_pdf.save_file(file_name=f"{type_name}_{datetime.now().strftime('%d-%m-%Y')}.pdf")

        def export_download_all(e):
            export_filter_state["start"] = None
            export_filter_state["end"] = None
            execute_export()

        def export_download_filtered(e):
            start_val = export_start_date.value
            end_val = export_end_date.value
            if start_val and end_val:
                export_filter_state["start"] = start_val
                export_filter_state["end"] = end_val
            else:
                export_filter_state["start"] = None
                export_filter_state["end"] = None
            execute_export()

        export_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(tr("dialog_export"), size=18, weight="bold"),
            content=ft.Column(
                [
                    ft.Text(tr("dialog_export_text"), size=13),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    export_start_date,
                                    ft.IconButton(
                                        ft.Icons.CALENDAR_MONTH,
                                        on_click=pick_export_start_date,
                                        icon_size=20,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0,
                            ),
                            ft.Column(
                                [
                                    export_end_date,
                                    ft.IconButton(
                                        ft.Icons.CALENDAR_MONTH,
                                        on_click=pick_export_end_date,
                                        icon_size=20,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0,
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                tight=True,
                width=350,
            ),
            actions=[
                ft.ElevatedButton(
                    tr("btn_filtered_download"),
                    on_click=export_download_filtered,
                    bgcolor=col_primary,
                    color=col_white,
                ),
                ft.ElevatedButton(
                    tr("btn_full_download"),
                    on_click=export_download_all,
                    bgcolor=col_success,
                    color=col_white,
                ),
                ft.TextButton(
                    tr("cancel"),
                    on_click=lambda e: setattr(export_dialog, "open", False) or page.update(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        def open_export_dialog(fmt):
            export_current_format["format"] = fmt
            # Önceki filtre değerlerini koru; yoksa boş bırak
            export_start_date.value = export_filter_state.get("start") or ""
            export_end_date.value = export_filter_state.get("end") or ""
            if export_dialog not in page.overlay:
                page.overlay.append(export_dialog)
            export_dialog.open = True
            page.update()

        def export_to_excel(e):
            open_export_dialog("excel")

        def export_to_pdf(e):
            open_export_dialog("pdf")

        btn_clear = AestheticButton(tr("clear"), "refresh", "#7F8C8D", width=145, on_click=clear_inputs)
        btn_add = AestheticButton(tr("add"), "add", col_success, width=110, on_click=add_invoice)
        btn_update = AestheticButton(tr("update"), "update", col_blue_donut, width=125, on_click=update_invoice)
        _delete_btn = AestheticButton(tr("delete"), "delete", col_danger, width=110)
        _delete_gesture = ft.GestureDetector(
            content=_delete_btn,
            on_tap=delete_invoice,
            on_secondary_tap=lambda e: show_delete_all_dialog(),
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        btn_delete_row = ft.Row([_delete_gesture, selected_count_text], spacing=5)
        operation_buttons = ft.Row([btn_clear, btn_add, btn_update, btn_delete_row], spacing=20)

        btn_qr = create_styled_icon_button(ft.Icons.QR_CODE_SCANNER, "#3498DB", tr("qr_scan"), process_qr_folder)
        btn_excel = create_styled_icon_button(ft.Icons.TABLE_VIEW, "#217346", tr("export_excel"), export_to_excel)
        btn_pdf = create_styled_icon_button(ft.Icons.PICTURE_AS_PDF, "#D32F2F", tr("export_pdf"), export_to_pdf)
        btn_backup = create_styled_icon_button(ft.Icons.BACKUP, "#8E44AD", tr("backup_db"), backup_database)
        btn_restore = create_styled_icon_button(ft.Icons.CLOUD_DOWNLOAD, "#8E44AD", tr("restore_db"), restore_database)

        btn_backup_menu = ft.PopupMenuButton(
            tooltip=tr("backup_db"),
            content=ft.Container(
                bgcolor="#8E44AD",
                border_radius=8,
                width=42,
                height=42,
                alignment=ft.alignment.center,
                border=ft.border.all(1, "#22FFFFFF"),
                shadow=ft.BoxShadow(blur_radius=10, color="#808E44AD", offset=ft.Offset(0, 4)),
                content=ft.Icon(ft.Icons.STORAGE_ROUNDED, color=col_white, size=18),
            ),
            items=[
                ft.PopupMenuItem(
                    content=ft.Row([
                        ft.Icon(ft.Icons.BACKUP_ROUNDED, color="#8E44AD", size=18),
                        ft.Text(tr("backup_db"), size=13),
                    ], spacing=10),
                    on_click=backup_database,
                ),
                ft.PopupMenuItem(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, color="#8E44AD", size=18),
                        ft.Text(tr("restore_db"), size=13),
                    ], spacing=10),
                    on_click=restore_database,
                ),
            ],
        )

        sort_dropdown = ft.Container(
            padding=ft.padding.only(left=20),
            content=ft.Dropdown(
                options=[ft.dropdown.Option("newest", tr("sort_newest")), ft.dropdown.Option("date_desc", tr("sort_date_desc")), ft.dropdown.Option("date_asc", tr("sort_date_asc"))],
                value="newest", on_change=on_sort_change, width=160, text_size=13, label=tr("sort"), border_radius=10, bgcolor="surface", border_color="outline",
            ),
        )

        controls_row = ft.Row(
            [
                sort_dropdown,
                ft.Row([btn_backup_menu], spacing=4),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.padding.only(right=18),
                    content=ft.Row([btn_qr, btn_excel, btn_pdf], spacing=8),
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        input_line_1 = ft.ResponsiveRow([
            ft.Column([form_label(tr("invoice_no")), input_fatura_no], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([date_label, input_tarih], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("company")), input_firma], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("item_service")), input_malzeme], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("amount")), input_miktar], spacing=6, col={"sm": 10, "md": 2}),
        ], columns=10, spacing=16, run_spacing=14)

        input_line_2 = ft.ResponsiveRow([
            ft.Column([form_label(tr("total")), input_tutar], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("currency")), input_para_birimi], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("vat_amount")), input_kdv], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("usd_rate_label")), input_usd_kur], spacing=6, col={"sm": 10, "md": 2}),
            ft.Column([form_label(tr("eur_rate_label")), input_eur_kur], spacing=6, col={"sm": 10, "md": 2}),
        ], columns=10, spacing=16, run_spacing=14)

        return ft.Container(
            alignment=ft.alignment.top_left,
            padding=ft.padding.only(left=20, right=20, top=15, bottom=15),
            content=ft.Column([
                # Üst Başlık ve Tip Seçici - Responsive hale getirildi
                ft.ResponsiveRow([
                    ft.Column([ft.Text(tr("invoices_title"), size=24, weight="bold")], col={"sm": 12, "md": 4}),
                    ft.Column([type_selector], col={"sm": 12, "md": 8}, horizontal_alignment=ft.CrossAxisAlignment.END),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Container(height=10),
                
                # Kontroller Sırası (Sıralama, Yedek, Dışa Aktar...)
                controls_row,
                
                ft.Container(height=6),
                
                # Giriş Alanları - Kompakt (2 satır)
                ft.Column([
                    input_line_1,
                    input_line_2,
                ], spacing=14),
                
                ft.Container(height=14),
                
                # İşlem Butonları (Kaydet, Güncelle...)
                ft.Container(content=operation_buttons, alignment=ft.alignment.center_left, padding=ft.padding.only(left=10), margin=ft.margin.only(top=4)),
                
                ft.Container(height=8),
                
                # Tablo Alanı ve Diğerleri
                table_container,
                _pagination_bar,
                ft.Container(height=12),
                general_expenses_section,
                ft.Container(height=20),
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, 
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            ),
            expand=True,
        )

    # ------------------------------------------------------------------------
    # SAYFA YÖNETİMİ VE NAVİGASYON (Page Management & Navigation)
    # ------------------------------------------------------------------------
    # Sayfa Yöneticisi
    dashboard_content = ft.Container()
    faturalar_page = create_invoices_page()
    donemsel_page = create_donemsel_page()

    def change_view(e):
        clicked_btn_data = e.control.data

        if state["current_page"] == "home" and clicked_btn_data != "home":
            state["animation_completed"] = True

        state["current_page"] = clicked_btn_data

        # Tabları güncelle
        for tab in top_bar_tabs.controls:
            if isinstance(tab, TopBarTab):
                tab.is_selected = tab.data == clicked_btn_data
                tab.update_visuals(run_update=False)
        top_bar_tabs.update()

        # Dynamic Controls
        dynamic_controls_container.controls = []

        # Language Button Visibility
        try:
            lang_btn.visible = True
        except: pass

        def switch_page_and_update_data():
            if clicked_btn_data == "home":
                content_area.content = dashboard_content
                page.update()
                if state["update_callbacks"]["home_page"]:
                    state["update_callbacks"]["home_page"]()
                threading.Thread(
                    target=lambda: backend_instance.update_exchange_rates(force_refresh=True),
                    daemon=True,
                ).start()
            elif clicked_btn_data == "faturalar":
                state["current_page"] = "invoices"
                content_area.content = faturalar_page
                page.update()
                if state["update_callbacks"]["invoice_page"]:
                    state["update_callbacks"]["invoice_page"]()
            elif clicked_btn_data == "raporlar":
                state["current_page"] = "donemsel"
                content_area.content = donemsel_page
                page.update()
                if state["update_callbacks"]["donemsel_page"]:
                    state["update_callbacks"]["donemsel_page"]()

        # Sayfa geçişini ve veri yüklemesini ayırarak takılmayı önlüyoruz
        switch_page_and_update_data()

    # Logo
    logo_text = ft.Text("Excellent", size=24, weight="bold", color="onBackground")
    logo_area = ft.Row(
        [
            ft.Image(src="logo.png", width=40, height=40, fit=ft.ImageFit.CONTAIN),
            logo_text,
        ],
        spacing=10,
    )

    # Tabs
    btn_home = TopBarTab(tr("nav_home"), "home", True)
    btn_faturalar = TopBarTab(tr("nav_invoices"), "faturalar")
    btn_raporlar = TopBarTab(tr("nav_reports"), "raporlar")
    btn_home.on_click = change_view
    btn_faturalar.on_click = change_view
    btn_raporlar.on_click = change_view

    top_bar_tabs = ft.Row([btn_home, btn_faturalar, btn_raporlar], spacing=10)

    # Language Toggle
    def toggle_language(e):
        nonlocal faturalar_page, donemsel_page
        new_lang = "en" if state["current_language"] == "tr" else "tr"
        state["current_language"] = new_lang

        # Update button text
        lang_btn.text = "TR" if new_lang == "en" else "EN"
        lang_btn.tooltip = (
            tr("tooltip_lang_tr") if new_lang == "en" else tr("tooltip_lang_en")
        )

        # Update tabs
        btn_home.text_control.value = tr("nav_home")
        btn_faturalar.text_control.value = tr("nav_invoices")
        btn_raporlar.text_control.value = tr("nav_reports")
        btn_home.update()
        btn_faturalar.update()
        btn_raporlar.update()
        internet_warning_text.value = tr("no_internet_warning")
        if internet_warning_widget.visible:
            internet_warning_widget.update()

        # Recreate pages
        # Fatura formu değerlerini koru (dil değişimi sırasında)
        _form_getter = state.get("_get_invoice_form_values")
        if callable(_form_getter):
            state["_invoice_form_values"] = _form_getter()
        faturalar_page = create_invoices_page()
        donemsel_page = create_donemsel_page()
        dashboard_content.content = create_dashboard_page()

        # Update current view
        if state["current_page"] == "invoices" or state["current_page"] == "faturalar":
            content_area.content = faturalar_page
        elif state["current_page"] == "donemsel" or state["current_page"] == "raporlar":
            content_area.content = donemsel_page
        else:
            content_area.content = dashboard_content
            # Dil değişince animasyonun her zaman çalışmasını sağlıyoruz (Giriş ekranındayken)
            # Sadece animasyon tamamlanmamışsa başlat
            if not state.get("animation_completed", False):
                threading.Thread(target=start_animations, daemon=True).start()
            else:
                # Animasyon tamamlanmışsa donutları direkt başlat (son hallerine getir)
                for donut in state["donuts"]:
                    donut.start_animation()

        content_area.update()

        # Show restart hint
        page.open(ft.SnackBar(content=ft.Text(tr("language_changed_msg")), bgcolor=col_primary))
        page.update()

    lang_btn = ft.TextButton(
        text="EN",
        tooltip=tr("tooltip_lang_en"),
        on_click=toggle_language,
        style=ft.ButtonStyle(color="onSurfaceVariant"),
    )

    # Theme Toggle
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.WB_SUNNY
            theme_btn.tooltip = tr("light_mode")
        elif page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.NIGHTLIGHT_ROUND
            theme_btn.tooltip = tr("dark_mode")
        else:
            if page.platform_brightness == ft.Brightness.DARK:
                page.theme_mode = ft.ThemeMode.LIGHT
                theme_btn.icon = ft.Icons.NIGHTLIGHT_ROUND
                theme_btn.tooltip = tr("dark_mode")
            else:
                page.theme_mode = ft.ThemeMode.DARK
                theme_btn.icon = ft.Icons.WB_SUNNY
                theme_btn.tooltip = tr("light_mode")
        page.open(ft.SnackBar(content=ft.Text(tr("theme_changed_msg")), bgcolor=col_secondary))
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.NIGHTLIGHT_ROUND,
        tooltip=tr("dark_mode"),
        on_click=toggle_theme,
        icon_color="onSurfaceVariant",
    )

    try:
        if page.platform_brightness == ft.Brightness.DARK:
            theme_btn.icon = ft.Icons.WB_SUNNY
            theme_btn.tooltip = "Açık Mod"
    except Exception:
        pass

    # Dynamic Controls Container - Scrollable Row for responsiveness
    dynamic_controls_container = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)

    # Internet Warning Widget (top-right)
    internet_warning_text = ft.Text(tr("no_internet_warning"), color=col_danger, size=11, weight="bold")
    internet_warning_widget = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, color=col_danger, size=14),
                internet_warning_text,
            ],
            spacing=4,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=6,
        bgcolor="#22FF3B30",
        border=ft.border.all(1, col_danger),
    )
    state["internet_warning"] = internet_warning_widget

    # Internet Reconnected Widget (top-right, yeşil)
    internet_reconnected_widget = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WIFI_ROUNDED, color=col_success, size=14),
                ft.Text(tr("internet_reconnected"), color=col_success, size=11, weight="bold"),
            ],
            spacing=4,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=6,
        bgcolor="#224CD964",
        border=ft.border.all(1, col_success),
    )
    state["internet_reconnected_widget"] = internet_reconnected_widget

    # Top Bar Container
    _tb_logo_con = ft.Container(content=logo_area, width=220)
    _tb_right_con = ft.Container(
        content=ft.Row([
            internet_warning_widget,
            internet_reconnected_widget,
            dynamic_controls_container,
            lang_btn,
            theme_btn,
        ], alignment=ft.MainAxisAlignment.END, spacing=8),
        width=320,
    )
    top_bar = ft.Container(
        content=ft.Row(
            [
                _tb_logo_con,
                ft.Container(expand=2),
                ft.Container(content=top_bar_tabs, alignment=ft.alignment.center),
                ft.Container(expand=True),
                _tb_right_con,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="surface",
        padding=ft.padding.symmetric(horizontal=20, vertical=0),
        shadow=ft.BoxShadow(blur_radius=5, color="shadow"),
        height=65,
    )

    # ------------------------------------------------------------------------
    # DASHBOARD İÇERİK VE YARDIMCILARI (Dashboard Content & Helpers)
    # ------------------------------------------------------------------------
    # --- DASHBOARD İÇERİK ---
    year_dropdown_ref = None
    available_years = []
    year_dropdown_options = []

    # Backend'den gerçek verileri çek
    def get_dashboard_stats(year=None):
        """Dashboard için istatistikleri hesapla - isteğe bağlı yıl filtresi"""
        try:
            # Seçili para birimini belirle
            current_currency = state.get("current_currency", "TRY")
            amount_field = "toplam_tutar_tl"
            if current_currency == "USD":
                amount_field = "toplam_tutar_usd"
            elif current_currency == "EUR":
                amount_field = "toplam_tutar_eur"

            # Giden faturalar (Gelir)
            income_invoices = (
                backend_instance.handle_invoice_operation(
                    operation="get", invoice_type="outgoing"
                )
                or []
            )

            # Gelen faturalar (Gider)
            expense_invoices = (
                backend_instance.handle_invoice_operation(
                    operation="get", invoice_type="incoming"
                )
                or []
            )

            # Eğer yıl filtresi varsa, sadece o yıla ait faturaları al
            if year:
                income_invoices = [
                    inv
                    for inv in income_invoices
                    if inv.get("tarih", "").endswith(str(year))
                ]
                expense_invoices = [
                    inv
                    for inv in expense_invoices
                    if inv.get("tarih", "").endswith(str(year))
                ]

            # Toplam gelir
            total_income = sum(
                float(inv.get(amount_field, 0)) for inv in income_invoices
            )

            # Toplam gider
            total_expense = sum(
                float(inv.get(amount_field, 0)) for inv in expense_invoices
            )

            # Genel giderleri ekle
            if year:
                general_expenses = backend_instance.db.get_yearly_expenses(year)
                if general_expenses:
                    month_keys = [
                        "ocak",
                        "subat",
                        "mart",
                        "nisan",
                        "mayis",
                        "haziran",
                        "temmuz",
                        "agustos",
                        "eylul",
                        "ekim",
                        "kasim",
                        "aralik",
                    ]
                    for month_key in month_keys:
                        if month_key in general_expenses:
                            general_amount_tl = float(general_expenses[month_key] or 0)

                            # Para birimine göre çevir
                            general_amount = general_amount_tl
                            if current_currency != "TRY":
                                general_amount = backend_instance.convert_currency(
                                    general_amount_tl, "TRY", current_currency
                                )

                            total_expense += general_amount

            # Net kâr
            net_profit = total_income - total_expense

            # Aylık ortalama (son 12 ay gelir ortalaması)
            current_year = datetime.now().year
            current_month = datetime.now().month

            # Eğer seçili yıl geçmiş yılsa, 12 aya böl
            if year and year < current_year:
                monthly_avg = total_income / 12
            else:
                monthly_avg = total_income / max(current_month, 1)

            return {
                "net_profit": net_profit,
                "total_income": total_income,
                "total_expense": total_expense,
                "monthly_avg": monthly_avg,
                "income_count": len(income_invoices),
                "expense_count": len(expense_invoices),
            }
        except Exception:
            return {
                "net_profit": 0,
                "total_income": 0,
                "total_expense": 0,
                "monthly_avg": 0,
                "income_count": 0,
                "expense_count": 0,
            }

    def create_dashboard_page():
        nonlocal year_dropdown_ref, available_years, year_dropdown_options

        # Donut listesini temizle (yeni oluşturulacaklar eklenecek)
        state["donuts"] = []

        def change_currency(currency_code):
            state["current_currency"] = currency_code
            currency_selector_container.content = create_currency_selector()
            currency_selector_container.update()

            # Grafikleri ve verileri güncelle
            refresh_charts_and_data()

        def create_currency_selector():
            curr = state["current_currency"]
            return ft.Container(
                bgcolor="background",
                border_radius=12,
                padding=4,
                content=ft.Row(
                    [
                        currency_button("₺ TRY", "TRY", curr, change_currency),
                        currency_button("$ USD", "USD", curr, change_currency),
                        currency_button("€ EUR", "EUR", curr, change_currency),
                    ],
                    spacing=0,
                    tight=True,
                ),
            )

        currency_selector_container = ft.Container(content=create_currency_selector())

        # Kur bilgisi text'i dinamik olarak oluştur
        exchange_rate_text = ft.Text(
            get_exchange_rate_display(),
            size=13,
            color="onSurfaceVariant",
            weight="w600",
        )

        # Warning icon logic
        show_warning = backend_instance.using_default_rates
        rate_warning_icon = ft.Icon(
            ft.Icons.WARNING,
            color=col_danger,
            size=16,
            visible=show_warning,
            tooltip=tr("rate_warning_tooltip"),
        )

        header = ft.Row(
            [
                ft.Text(
                    tr("dashboard_title"), size=26, weight="bold", color="onBackground"
                ),
                ft.Row(
                    [
                        ft.Container(
                            bgcolor="secondaryContainer",
                            padding=ft.padding.symmetric(horizontal=15, vertical=10),
                            border_radius=8,
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        "currency_exchange", size=16, color="primary"
                                    ),
                                    exchange_rate_text,
                                    rate_warning_icon,
                                ],
                                spacing=10,
                            ),
                        ),
                        currency_selector_container,
                    ],
                    spacing=20,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # İstatistikleri al
        stats = get_dashboard_stats()

        # Trend hesapla (basit - önceki aya göre %15 artış varsayımı)
        net_profit_trend = "+15%" if stats["net_profit"] > 0 else "0%"
        income_trend = "+4%" if stats["total_income"] > 0 else "0%"
        expense_trend = "-2%" if stats["total_expense"] > 0 else "0%"
        avg_trend = "+1%" if stats["monthly_avg"] > 0 else "0%"

        # Her donut için kendi max değerini hesapla (değerin %120'si, min 10K)
        profit_max = max(abs(stats["net_profit"]) * 1.2, 10000)
        income_max = max(stats["total_income"] * 1.2, 10000)
        expense_max = max(stats["total_expense"] * 1.2, 10000)
        avg_max = max(stats["monthly_avg"] * 1.2, 10000)

        current_currency = state.get("current_currency", "TRY")

        stats_row = ft.Row(
            [
                DonutStatCard(
                    tr("net_profit"),
                    "attach_money",
                    col_blue_donut,
                    net_profit_trend,
                    abs(stats["net_profit"]),
                    profit_max,
                    format_currency(
                        stats["net_profit"], currency=current_currency, compact=True
                    ),
                ),
                DonutStatCard(
                    tr("total_income"),
                    "arrow_upward",
                    col_success,
                    income_trend,
                    stats["total_income"],
                    income_max,
                    format_currency(
                        stats["total_income"], currency=current_currency, compact=True
                    ),
                ),
                DonutStatCard(
                    tr("total_expense"),
                    "arrow_downward",
                    col_secondary,
                    expense_trend,
                    stats["total_expense"],
                    expense_max,
                    format_currency(
                        stats["total_expense"], currency=current_currency, compact=True
                    ),
                ),
                DonutStatCard(
                    tr("monthly_avg"),
                    "pie_chart",
                    "#FF5B5B",
                    avg_trend,
                    stats["monthly_avg"],
                    avg_max,
                    format_currency(
                        stats["monthly_avg"], currency=current_currency, compact=True
                    ),
                ),
            ],
            spacing=20,
        )

        # Son işlemleri backend'den çek
        def get_recent_transactions():
            """Son işlem geçmişini getir"""
            try:
                # İşlem geçmişinden son kayıtları al
                history_records = backend_instance.get_recent_history(limit=10)
                return _process_history_records(history_records)
            except Exception:
                return []

        def _process_history_records(records):
            """Geçmiş kayıtlarını transaction formatına çevirir"""
            import re

            transactions = []

            for record in records:
                # Record yapısı: {'id': 1, 'action': 'EKLEME_GELIR', 'details': '...', 'timestamp': '...'}

                action = record.get("action", "")
                details = record.get("details", "")
                timestamp = record.get("timestamp", "")

                # Action'dan işlem tipi ve fatura tipi çıkar
                parts = action.split("_")
                operation_type = parts[0] if len(parts) > 0 else "İŞLEM"
                invoice_type_raw = parts[1] if len(parts) > 1 else ""

                is_income = invoice_type_raw == "GELIR"

                is_updated = operation_type == "GÜNCELLEME"
                is_deleted = operation_type == "SİLME"

                # Timestamp'ten tarih ve saat çıkar (ISO format: YYYY-MM-DDTHH:MM:SS...)
                try:
                    # fromisoformat bazen Z veya +00:00 ile sorun yaşayabilir, basitçe ilk 19 karakteri alalım
                    ts_clean = timestamp[:19]
                    dt = datetime.fromisoformat(ts_clean)
                    op_date = dt.strftime("%d.%m.%Y")
                    op_time = dt.strftime("%H:%M")
                    display_date = f"{op_date} {op_time}"
                except Exception:
                    display_date = timestamp
                    op_date = timestamp
                    op_time = ""

                # Details stringinden bilgileri çıkar
                # Örnek: "Gelir fatura eklendi - Firma: ABC - Tutar: 100 TL - Tarih: 01.01.2025"

                title = "İşlem"
                amount_str = "0.00"
                invoice_date = ""

                # Firma
                firma_match = re.search(r"Firma:\s*(.*?)(?:\s-\s|$)", details)
                if firma_match:
                    title = firma_match.group(1)

                # Tutar ve Birim
                amount_str = "0.00"
                currency = "TL"
                amount_match = re.search(r"Tutar:\s*([\d\.,]+)\|(\w+)", details)
                if amount_match:
                    amount_str = amount_match.group(1)
                    currency = amount_match.group(2)
                else:
                    # Eski format için fallback (Tutar: 100 TL)
                    old_format = re.search(
                        r"Tutar:\s*([\d\.,]+)(?:\s*(TL|USD|EUR))?", details
                    )
                    if old_format:
                        amount_str = old_format.group(1)
                        currency = old_format.group(2) if old_format.group(2) else "TL"

                # Fatura Tarihi
                date_match = re.search(r"Tarih:\s*([\d\.]+)", details)
                if date_match:
                    invoice_date = date_match.group(1)

                transactions.append(
                    {
                        "title": title,
                        "display_date": display_date,
                        "invoice_date": invoice_date,
                        "amount": amount_str,
                        "currency": currency,  # Birim bilgisi eklendi
                        "income": is_income,
                        "is_updated": is_updated,
                        "is_deleted": is_deleted,
                        "operation_type": operation_type,
                        "sort_key": timestamp,  # Sıralama için timestamp kullan
                    }
                )

            # Tarihe göre ters sıralama (en yeni üstte)
            transactions.sort(key=lambda x: x.get("sort_key", ""), reverse=True)

            return transactions

        transactions_column = ft.Column(
            spacing=5, scroll=ft.ScrollMode.ALWAYS, expand=True
        )
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
                # Tarih filtresi varsa veritabanından o tarihteki işlemleri çek
                display_date = filter_date.strftime("%d.%m.%Y")

                # Veritabanı sorgusu için ISO formatı (YYYY-MM-DD)
                # Günün başlangıcı ve bitişi
                query_date_str = filter_date.strftime("%Y-%m-%d")
                start_str = f"{query_date_str}T00:00:00"
                end_str = f"{query_date_str}T23:59:59"

                # Başlık ekle
                transactions_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CALENDAR_TODAY, color=col_primary, size=16
                                ),
                                ft.Text(
                                    tr("transactions_for_date").format(display_date),
                                    size=13,
                                    weight="bold",
                                    color=col_primary,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=ft.padding.only(bottom=10),
                    )
                )

                # O tarihteki işlemleri getir
                history_records = backend_instance.get_history_by_date_range(
                    start_str, end_str
                )
                filtered_data = _process_history_records(history_records)
            else:
                # Filtre yoksa son işlemleri yeniden çek
                filtered_data = get_recent_transactions()

            if not filtered_data:
                transactions_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            tr("no_transactions"), color="onSurfaceVariant"
                        ),
                        alignment=ft.alignment.center,
                        padding=20,
                    )
                )
            else:
                for t in filtered_data:
                    transactions_column.controls.append(
                        TransactionRow(
                            t["title"],
                            t["display_date"],
                            t["amount"],
                            t["income"],
                            is_updated=t.get("is_updated", False),
                            is_deleted=t.get("is_deleted", False),
                            invoice_date=t.get("invoice_date"),
                            operation_type=t.get("operation_type", "EKLEME"),
                            currency=t.get("currency", "TL"),
                            current_currency=current_currency,  # Aktif döviz birimi
                        )
                    )

            try:
                if transactions_column.page:
                    transactions_column.update()
            except Exception:
                pass

        # İşlem geçmişi callback'ini kaydet
        state["update_callbacks"]["transaction_history"] = update_transactions

        update_transactions()

        def handle_date_change(e):
            if e.control.value:
                update_transactions(e.control.value)

        # Özel Türkçe tarih seçici dialog
        date_input_field = ft.TextField(
            hint_text=tr("date_hint"),
            hint_style=ft.TextStyle(color="onSurfaceVariant", size=12),
            text_size=14,
            color="onBackground",
            bgcolor="surface",
            border_color="outline",
            focused_border_color=col_primary,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=15, vertical=12),
            width=280,
        )

        date_dialog_error = ft.Text("", color=col_danger, size=12, visible=False)

        def close_date_dialog(e):
            date_dialog.open = False
            date_input_field.value = ""
            date_dialog_error.visible = False
            page.update()

        def apply_date_filter(e):
            """Girilen tarihi parse edip filtrele"""
            input_val = date_input_field.value
            if not input_val or not input_val.strip():
                date_dialog_error.value = "Lütfen bir tarih girin"
                date_dialog_error.visible = True
                page.update()
                return

            # Tarihi formatla
            formatted = format_date_input(input_val.strip())

            # Geçerli tarih mi kontrol et
            try:
                parts = formatted.split(".")
                if len(parts) == 3:
                    gun, ay, yil = int(parts[0]), int(parts[1]), int(parts[2])
                    selected_date = datetime(yil, ay, gun)

                    # Dialog'u kapat ve filtrele
                    date_dialog.open = False
                    date_input_field.value = ""
                    date_dialog_error.visible = False
                    page.update()

                    update_transactions(selected_date)
                else:
                    raise ValueError("Geçersiz format")
            except (ValueError, IndexError):
                date_dialog_error.value = "Geçersiz tarih! Örn: 121225 veya 12.12.2025"
                date_dialog_error.visible = True
                page.update()

        # Türkçe ay isimleri ile takvim görünümü için basit bir seçici
        TURKISH_MONTHS = [
            "Ocak",
            "Şubat",
            "Mart",
            "Nisan",
            "Mayıs",
            "Haziran",
            "Temmuz",
            "Ağustos",
            "Eylül",
            "Ekim",
            "Kasım",
            "Aralık",
        ]

        current_cal_year = datetime.now().year
        current_cal_month = datetime.now().month

        def get_month_days(year, month):
            """Ayın gün sayısını döndür"""
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            return (next_month - datetime(year, month, 1)).days

        def select_day(day, year, month):
            """Gün seçildiğinde"""

            def handler(e):
                selected_date = datetime(year, month, day)
                date_dialog.open = False
                date_input_field.value = ""
                date_dialog_error.visible = False
                page.update()
                update_transactions(selected_date)

            return handler

        calendar_grid = ft.Column(spacing=5)
        month_year_text = ft.Text("", size=16, weight="bold", color="onBackground")

        def build_calendar(year, month):
            """Takvim grid'ini oluştur"""
            nonlocal current_cal_year, current_cal_month
            current_cal_year = year
            current_cal_month = month

            month_year_text.value = f"{TURKISH_MONTHS[month - 1]} {year}"

            calendar_grid.controls.clear()

            # Gün başlıkları
            day_headers = ft.Row(
                [
                    ft.Container(
                        width=35,
                        height=25,
                        content=ft.Text(
                            d,
                            size=11,
                            weight="bold",
                            color="onSurfaceVariant",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        alignment=ft.alignment.center,
                    )
                    for d in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=2,
            )
            calendar_grid.controls.append(day_headers)

            # Ayın ilk gününün haftanın hangi günü olduğunu bul (0=Pazartesi)
            first_day = datetime(year, month, 1)
            start_weekday = first_day.weekday()

            # Ayın toplam gün sayısı
            total_days = get_month_days(year, month)

            # Takvim satırlarını oluştur
            day_num = 1
            for week in range(6):  # Max 6 hafta
                if day_num > total_days:
                    break

                week_row = []
                for weekday in range(7):
                    if week == 0 and weekday < start_weekday:
                        # Boş hücre
                        week_row.append(ft.Container(width=35, height=30))
                    elif day_num <= total_days:
                        # Bugün mü kontrol et
                        is_today = (
                            year == datetime.now().year
                            and month == datetime.now().month
                            and day_num == datetime.now().day
                        )

                        day_btn = ft.Container(
                            width=35,
                            height=30,
                            bgcolor=col_primary if is_today else None,
                            border_radius=5,
                            content=ft.Text(
                                str(day_num),
                                size=12,
                                color=col_white if is_today else col_text,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            alignment=ft.alignment.center,
                            on_click=select_day(day_num, year, month),
                            ink=True,
                        )
                        week_row.append(day_btn)
                        day_num += 1
                    else:
                        week_row.append(ft.Container(width=35, height=30))

                calendar_grid.controls.append(
                    ft.Row(week_row, alignment=ft.MainAxisAlignment.CENTER, spacing=2)
                )

            if calendar_grid.page:
                calendar_grid.update()
                month_year_text.update()

        def prev_month(e):
            nonlocal current_cal_year, current_cal_month
            if current_cal_month == 1:
                current_cal_month = 12
                current_cal_year -= 1
            else:
                current_cal_month -= 1
            build_calendar(current_cal_year, current_cal_month)

        def next_month(e):
            nonlocal current_cal_year, current_cal_month
            if current_cal_month == 12:
                current_cal_month = 1
                current_cal_year += 1
            else:
                current_cal_month += 1
            build_calendar(current_cal_year, current_cal_month)

        # İlk takvimi oluştur
        build_calendar(current_cal_year, current_cal_month)

        date_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(tr("select_date_title"), weight="bold", size=18),
            content=ft.Container(
                width=320,
                content=ft.Column(
                    [
                        # Manuel tarih girişi
                        ft.Text(
                            tr("enter_date_label"), size=13, color="onSurfaceVariant"
                        ),
                        date_input_field,
                        date_dialog_error,
                        ft.Container(height=5),
                        ft.ElevatedButton(
                            tr("go_to_date"),
                            icon="search",
                            bgcolor=col_primary,
                            color=col_white,
                            on_click=apply_date_filter,
                            width=280,
                        ),
                        ft.Divider(height=20),
                        # Takvim görünümü
                        ft.Text(
                            tr("or_select_calendar"), size=13, color="onSurfaceVariant"
                        ),
                        ft.Container(height=5),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon="chevron_left",
                                    on_click=prev_month,
                                    icon_color=col_primary,
                                ),
                                month_year_text,
                                ft.IconButton(
                                    icon="chevron_right",
                                    on_click=next_month,
                                    icon_color=col_primary,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        calendar_grid,
                    ],
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            actions=[
                ft.TextButton(
                    tr("cancel"),
                    on_click=close_date_dialog,
                    style=ft.ButtonStyle(color="onSurfaceVariant"),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(date_dialog)

        def open_date_dialog(e):
            # Takvimi bugünün tarihine sıfırla
            build_calendar(datetime.now().year, datetime.now().month)
            date_dialog.open = True
            page.update()

        def reset_transactions(e):
            update_transactions(None)

        transactions_list_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            tr("recent_transactions"),
                            size=18,
                            weight="bold",
                            color="onBackground",
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon="calendar_month",
                                    icon_color="onSurfaceVariant",
                                    tooltip=tr("go_by_date"),
                                    on_click=open_date_dialog,
                                ),
                                ft.TextButton(
                                    tr("latest_entries"),
                                    style=ft.ButtonStyle(color=col_primary),
                                    on_click=reset_transactions,
                                ),
                            ]
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=15),
                transactions_column,
            ],
            spacing=5,
        )

        transactions_list = ft.Container(
            bgcolor="surface",
            border_radius=20,
            padding=25,
            shadow=ft.BoxShadow(blur_radius=20, color="#08000000"),
            expand=True,
            content=transactions_list_content,
        )

        # Yıl dropdown'ı için dinamik seçenekler oluştur - tüm veritabanı yıllarını çek
        available_years = get_all_available_years()
        year_dropdown_options = [
            ft.dropdown.Option(str(year)) for year in available_years
        ]
        default_year = (
            str(available_years[0]) if available_years else str(datetime.now().year)
        )

        # Dropdown'ı değişkene ata (refresh fonksiyonunda kullanmak için)
        year_dropdown_ref = ft.Dropdown(
            width=100,
            options=year_dropdown_options,
            value=default_year,
            on_change=on_year_change,
            border_radius=10,
            text_size=13,
            content_padding=10,
            bgcolor="surface",
            border_color="outline",
            focused_border_color="primary",
        )

        chart_container = ft.Container(
            bgcolor="surface",
            border_radius=20,
            padding=ft.padding.only(left=30, right=30, top=30, bottom=10),
            expand=2,
            shadow=ft.BoxShadow(blur_radius=20, color="#08000000"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        tr("performance_analysis"),
                                        size=20,
                                        weight="bold",
                                        color="onBackground",
                                    ),
                                    ft.Text(
                                        tr("yearly_comparison"),
                                        size=13,
                                        color="onSurfaceVariant",
                                    ),
                                ]
                            ),
                            year_dropdown_ref,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=20),
                    ft.Container(content=line_chart, expand=True),
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        width=10,
                                        height=10,
                                        bgcolor=col_primary,
                                        border_radius=2,
                                    ),
                                    ft.Text(tr("income"), size=12, color="grey"),
                                ],
                                spacing=5,
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        width=10,
                                        height=10,
                                        bgcolor=col_secondary,
                                        border_radius=2,
                                    ),
                                    ft.Text(tr("expense"), size=12, color="grey"),
                                ],
                                spacing=5,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ]
            ),
        )

        dashboard_layout = ft.Column(
            [
                header,
                ft.Container(height=10),
                stats_row,
                ft.Container(height=10),
                ft.Row(
                    [
                        chart_container,
                        ft.Container(content=transactions_list, expand=1),
                    ],
                    expand=True,
                    spacing=20,
                ),
            ],
            spacing=10,
            expand=True,
        )

        return dashboard_layout

    dashboard_content.content = create_dashboard_page()
    content_area = ft.Container(expand=True, padding=30, content=dashboard_content)

    layout = ft.Column([top_bar, content_area], expand=True, spacing=0)
    page.add(layout)

    # İnternet bağlantı monitörünü başlat
    start_internet_monitor()

    def start_animations():
        time.sleep(0.5)
        for donut in state["donuts"]:
            donut.start_animation()
        
        # Animasyonların tamamlandığını işaretle
        state["animation_completed"] = True
        
        # İlk yüklemede varsayılan yılı çiz
        if available_years:
            first_year = available_years[0]
            draw_snake_chart(first_year)

        # Animasyonlar başladıktan sonra callback'leri kaydet
        time.sleep(0.3)  # Animasyonların tamamlanmasını bekle

        # Ana sayfa için birleşik callback - hem grafikler hem işlem geçmişi
        def home_page_full_update():
            refresh_charts_and_data()
            if state["update_callbacks"]["transaction_history"]:
                state["update_callbacks"][
                    "transaction_history"
                ]()  # İşlem geçmişini de güncelle

        state["update_callbacks"]["home_page"] = home_page_full_update

    threading.Thread(target=start_animations, daemon=True).start()

    # ------------------------------------------------------------------------
    # GÜNCELLEME FONKSİYONLARI (Update Functions)
    # ------------------------------------------------------------------------

    # Güncelleme kontrolü - sadece ana sayfa için
    def check_for_updates():
        """Uygulama güncellemelerini kontrol et"""
        try:
            # Ana sayfa açıkken güncelleme kontrolü yap
            if state["current_page"] != "home":
                return

            # Güncelleme kontrolü yap
            update_info = backend_instance.check_for_updates()

            if update_info and update_info.get("update_available", False):
                # Güncelleme mevcutsa, bilgilendirme mesajı göster
                msg = f"Yeni bir güncelleme mevcut: {update_info.get('version', 'Bilinmiyor')}\n\nAçıklama: {update_info.get('description', 'No description')}\n\nGüncellemek için 'Evet' butonuna tıklayın."

                def on_update_confirm(e):
                    # Güncelleme işlemini başlat
                    backend_instance.download_and_install_update()

                    # Bilgilendirme mesajı
                    page.open(ft.SnackBar(content=ft.Text(tr("update_downloading"), color=col_white), bgcolor=col_success,))
                    page.update()

                    # Uygulamayı yeniden başlat
                    time.sleep(2)
                    os.execl(sys.executable, sys.executable, *sys.argv)

                # Güncelleme onayı için dialog göster
                update_dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(tr("update_available")),
                    content=ft.Text(msg),
                    actions=[
                        ft.ElevatedButton(
                            tr("yes"),
                            on_click=on_update_confirm,
                            bgcolor=col_success,
                            color=col_white,
                        ),
                        ft.ElevatedButton(
                            tr("no"),
                            on_click=lambda e: update_dlg.close(),
                            bgcolor=col_danger,
                            color=col_white,
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )

                page.overlay.append(update_dlg)
                update_dlg.open = True
                page.update()
        except Exception:
            pass

    # Açılışı bloklamamak için güncelleme kontrolünü başlangıçta senkron çalıştırmıyoruz.


# Assets dizinini belirle (PyInstaller için)
def get_assets_dir():
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return sys._MEIPASS
    except Exception:
        return os.path.abspath(".")


ft.app(target=main, assets_dir=get_assets_dir())
