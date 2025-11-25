import flet as ft
import time
import threading

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
col_selected_row = "#E8F5E9" # Seçili satır için açık yeşil

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
    "chart_animated": False,
    "selected_row": None # Seçili satırı takip etmek için
}

# --- YARDIMCI BİLEŞENLER ---
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
        self.chart_container.rotate.angle = 0
        self.chart_container.opacity = 1
        self.chart_container.update()

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
                ft.Container(height=2),
                ft.Text(trend_text, size=12, color=col_success if "+" in trend_text else col_danger, weight="bold")
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
            ft.Container(content=self.donut, alignment=ft.alignment.center_right)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

class TransactionRow(ft.Container):
    def __init__(self, title, date, amount, is_income=True):
        super().__init__()
        self.padding = ft.padding.symmetric(vertical=10)
        self.border = ft.border.only(bottom=ft.border.BorderSide(1, "#F0F0F0"))
        color = col_success if is_income else col_danger
        icon = "arrow_upward" if is_income else "arrow_downward"
        sign = "+" if is_income else "-"
        self.content = ft.Row([
            ft.Container(width=40, height=40, bgcolor=f"{color}20", border_radius=10, content=ft.Icon(icon, color=color, size=20), alignment=ft.alignment.center),
            ft.Column([ft.Text(title, weight="bold", size=14, color=col_text), ft.Text(date, size=12, color=col_text_light)], spacing=2, expand=True),
            ft.Text(f"{sign} {amount}", weight="bold", size=14, color=color)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

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

# --- YENİ KOMPAKT GİRİŞ KUTUSU (TEK SATIR İÇİN - BİRAZ DAHA GENİŞ) ---
def create_mini_input(hint, width=None, expand=False):
    return ft.Container(
        content=ft.TextField(
            hint_text=hint,
            hint_style=ft.TextStyle(color="#B0B0B0", size=13), # Biraz daha büyük font
            text_size=13,
            color=col_text,
            border_color="transparent",
            bgcolor="transparent",
            content_padding=ft.padding.only(left=10, bottom=14), # Padding ayarı
            height=35 # Yükseklik arttı
        ),
        bgcolor="#F5F5F5",
        border=ft.border.all(1, "#E0E0E0"),
        border_radius=8, # Köşeler daha yuvarlak
        height=35, # Yükseklik arttı
        width=width,
        expand=expand
    )

# --- YENİ EXCEL TARZI SEÇİLEBİLİR TABLO (TAM GENİŞLİK & YEŞİL SEÇİM) ---
def create_invoice_table():
    # Başlık stili
    def header(t): return ft.DataColumn(ft.Text(t, weight="bold", color="black", size=12))
    # Hücre stili
    def cell(t): return ft.DataCell(ft.Text(t, color="#333333", size=12))

    # Satır seçme fonksiyonu (Yeşil Renk)
    def on_row_select(e):
        # Önceki seçili satırı eski haline getir (varsa)
        if state["selected_row"] and state["selected_row"] != e.control:
            state["selected_row"].selected = False
            state["selected_row"].update()
        
        # Yeni satırı seç veya seçimi kaldır
        e.control.selected = not e.control.selected
        state["selected_row"] = e.control if e.control.selected else None
        e.control.update()

    return ft.DataTable(
        columns=[
            header("FATURA NO"),
            header("İRSALİYE NO"),
            header("TARİH"),
            header("FİRMA"),
            header("MALZEME"),
            header("MİKTAR"),
            ft.DataColumn(ft.Text("TUTAR (TL)", weight="bold", color="black", size=12), numeric=True),
            ft.DataColumn(ft.Text("TUTAR (USD)", weight="bold", color="black", size=12), numeric=True),
            ft.DataColumn(ft.Text("TUTAR (EUR)", weight="bold", color="black", size=12), numeric=True),
            header("KDV %"),
            ft.DataColumn(ft.Text("KDV TUTARI", weight="bold", color="black", size=12), numeric=True),
        ],
        rows=[
            ft.DataRow(
                cells=[cell("FAT-KDV-TEST"), cell("IRS-KDV-TEST"), cell("24.11.2025"), cell("KDV Test Firma"), cell("-"), cell("-"), cell("423.73"), cell("10.00"), cell("8.68"), cell("18%"), cell("76.27")],
                on_select_changed=on_row_select, selected=False
            ),
            ft.DataRow(
                cells=[cell("FAT-10"), cell("IRS-10"), cell("24.11.2025"), cell("Test Firma 10"), cell("Test Ürün 10"), cell("1"), cell("1,666.67"), cell("39.27"), cell("34.06"), cell("20%"), cell("333.33")],
                on_select_changed=on_row_select, selected=False
            ),
            ft.DataRow(
                cells=[cell("FAT-11"), cell("IRS-11"), cell("24.11.2025"), cell("Test Firma 11"), cell("Test Ürün 11"), cell("1"), cell("1,750.00"), cell("41.23"), cell("35.76"), cell("20%"), cell("350.00")],
                on_select_changed=on_row_select, selected=False
            ),
            ft.DataRow(
                cells=[cell("FAT-12"), cell("IRS-12"), cell("24.11.2025"), cell("Test Firma 12"), cell("Test Ürün 12"), cell("1"), cell("1,833.33"), cell("43.19"), cell("37.46"), cell("20%"), cell("366.67")],
                on_select_changed=on_row_select, selected=False
            ),
             ft.DataRow(
                cells=[cell("FAT-13"), cell("IRS-13"), cell("24.11.2025"), cell("Test Firma 13"), cell("Test Ürün 13"), cell("1"), cell("1,916.67"), cell("45.16"), cell("39.17"), cell("20%"), cell("383.33")],
                on_select_changed=on_row_select, selected=False
            ),
        ],
        heading_row_color="#DDDDDD",
        heading_row_height=40, # Biraz daha yüksek başlık
        data_row_max_height=40, # Biraz daha yüksek satır
        vertical_lines=ft.border.BorderSide(1, "#CCCCCC"),
        horizontal_lines=ft.border.BorderSide(1, "#CCCCCC"),
        column_spacing=15, # Sütunlar arası boşluk arttı
        show_checkbox_column=True,
        width=float("inf") # Tabloyu tam genişliğe yay
    )

# --- GENEL GİDER TABLOSU ---
def create_grid_expenses():
    months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    expense_cards = []
    for m in months:
        card = ft.Container(
            bgcolor=col_white, border_radius=8, padding=8, width=140, height=80,
            shadow=ft.BoxShadow(blur_radius=3, color="#05000000", offset=ft.Offset(0,2)), border=ft.border.all(1, "#F0F0F0"),
            content=ft.Column([
                ft.Row([ft.Text(m, size=12, weight="bold", color=col_primary), ft.Icon("edit", size=12, color=col_text_light)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=2, color="transparent"),
                ft.TextField(value="0", text_size=13, text_style=ft.TextStyle(weight=ft.FontWeight.BOLD), color=col_text, text_align=ft.TextAlign.RIGHT, border_color="#E0E0E0", focused_border_color=col_primary, height=30, content_padding=5, bgcolor="#FAFAFA", prefix_text="₺ ")
            ], spacing=1)
        )
        expense_cards.append(card)
    return ft.Container(padding=ft.padding.only(top=15), content=ft.Column([ft.Row([ft.Icon("calendar_month", color=col_secondary, size=20), ft.Text("Yıllık Genel Giderler (Manuel Giriş)", size=16, weight="bold", color=col_text)], spacing=8), ft.Container(height=5), ft.Row(controls=expense_cards, wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER))

# --- CHART ---
full_data = {"2024": {"gelir": [20, 50, 35, 75, 60, 85, 70, 90, 75, 100, 85, 115], "gider": [10, 30, 25, 40, 35, 50, 45, 60, 55, 70, 65, 80]}, "2025": {"gelir": [30, 60, 45, 85, 70, 95, 80, 100, 95, 120, 110, 130], "gider": [15, 35, 30, 50, 45, 60, 55, 70, 65, 85, 75, 90]}}
line_chart = ft.LineChart(data_series=[ft.LineChartData(data_points=[], stroke_width=5, color=col_primary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_primary_50, transparent_white])), ft.LineChartData(data_points=[], stroke_width=5, color=col_secondary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_secondary_50, transparent_white]))], border=ft.border.all(0, "transparent"), bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(m, size=12, color=col_text_light)) for i, m in enumerate(["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"])], labels_size=30), left_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=0, label=ft.Text("0", size=10, color=col_text_light)), ft.ChartAxisLabel(value=50, label=ft.Text("50K", size=10, color=col_text_light)), ft.ChartAxisLabel(value=100, label=ft.Text("100K", size=10, color=col_text_light)), ft.ChartAxisLabel(value=150, label=ft.Text("150K", size=10, color=col_text_light))], labels_size=40), tooltip_bgcolor=tooltip_bg, min_y=0, max_y=150, min_x=0, max_x=11, expand=True, horizontal_grid_lines=ft.ChartGridLines(color="#F0F0F0", width=1, dash_pattern=[5, 5]), animate=None)

def draw_snake_chart(year):
    line_chart.data_series[0].data_points = []
    line_chart.data_series[1].data_points = []
    line_chart.update()
    time.sleep(0.01)
    gelir_data = full_data[year]["gelir"]
    gider_data = full_data[year]["gider"]
    for i in range(len(gelir_data)):
        target_y_gelir = gelir_data[i]
        target_y_gider = gider_data[i]
        if i == 0:
            line_chart.data_series[0].data_points.append(ft.LineChartDataPoint(0, target_y_gelir, tooltip=str(target_y_gelir)))
            line_chart.data_series[1].data_points.append(ft.LineChartDataPoint(0, target_y_gider, tooltip=str(target_y_gider)))
        else:
            prev_y_gelir = gelir_data[i-1]
            prev_y_gider = gider_data[i-1]
            steps = 10
            for step in range(1, steps + 1):
                factor = step / steps
                inter_x = (i - 1) + factor
                inter_y_gelir = prev_y_gelir + (target_y_gelir - prev_y_gelir) * factor
                inter_y_gider = prev_y_gider + (target_y_gider - prev_y_gider) * factor
                line_chart.data_series[0].data_points.append(ft.LineChartDataPoint(inter_x, inter_y_gelir, tooltip=""))
                line_chart.data_series[1].data_points.append(ft.LineChartDataPoint(inter_x, inter_y_gider, tooltip=""))
                if not state["chart_animated"]:
                    line_chart.update()
                    time.sleep(0.01)
    state["chart_animated"] = True
    line_chart.update()

def on_year_change(e): threading.Thread(target=draw_snake_chart, args=(e.control.value,), daemon=True).start()

# --- ANA UYGULAMA ---
def main(page: ft.Page):
    page.title = "Excellent MVP Dashboard"
    page.padding = 0
    page.bgcolor = col_bg
    page.window_width = 1400 
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- SIDEBAR ---
    class SidebarButton(ft.Container):
        def __init__(self, icon_name, text, page_name, is_selected=False):
            super().__init__()
            self.data = page_name
            self.is_selected = is_selected
            self.width = 50
            self.height = 50
            self.border_radius = 12
            self.padding = 0
            self.alignment = ft.alignment.center
            self.animate = ft.Animation(200, "easeOut") 
            self.icon_control = ft.Icon(icon_name, size=24)
            self.text_control = ft.Text(text, size=15, weight="w600", visible=state["sidebar_expanded"])
            self.content_row = ft.Row([self.icon_control, self.text_control], spacing=15, alignment=ft.MainAxisAlignment.START, visible=state["sidebar_expanded"])
            self.content_icon_only = ft.Container(content=self.icon_control, alignment=ft.alignment.center, visible=not state["sidebar_expanded"])
            self.content = ft.Stack([self.content_row, self.content_icon_only])
            self.update_visuals(run_update=False)

        def update_visuals(self, run_update=True):
            self.text_control.visible = state["sidebar_expanded"]
            self.content_row.visible = state["sidebar_expanded"]
            self.content_icon_only.visible = not state["sidebar_expanded"]
            self.width = 220 if state["sidebar_expanded"] else 50
            self.padding = ft.padding.only(left=15) if state["sidebar_expanded"] else 0
            self.alignment = ft.alignment.center_left if state["sidebar_expanded"] else ft.alignment.center
            if self.is_selected:
                self.bgcolor = col_primary
                self.icon_control.color = col_white
                self.text_control.color = col_white
                self.shadow = ft.BoxShadow(blur_radius=10, color=col_primary_50, offset=ft.Offset(0, 4))
            else:
                self.bgcolor = "transparent"
                self.icon_control.color = col_text_light
                self.text_control.color = col_text_light
                self.shadow = None
            if run_update: self.update()

    def toggle_sidebar(e):
        state["sidebar_expanded"] = not state["sidebar_expanded"]
        sidebar_container.width = 260 if state["sidebar_expanded"] else 90
        logo_text.visible = state["sidebar_expanded"]
        menu_row.alignment = ft.MainAxisAlignment.START if state["sidebar_expanded"] else ft.MainAxisAlignment.CENTER
        for btn in sidebar_column.controls:
            if isinstance(btn, SidebarButton): btn.update_visuals()
        page.update()

    # --- FATURA SAYFASI İÇERİĞİ (YENİ DÜZEN) ---
    def create_invoices_page():
        
        general_expenses_section = create_grid_expenses()
        general_expenses_section.visible = True

        def toggle_invoice_type(e):
            btn_container = e.control
            state["invoice_type"] = "income" if state["invoice_type"] == "expense" else "expense"
            is_expense = state["invoice_type"] == "expense"
            active_color = col_secondary if is_expense else col_primary
            btn_container.content.controls[0].value = "Giden Faturalar (Gelir)" if not is_expense else "Gelen Faturalar (Gider)"
            btn_container.bgcolor = active_color
            btn_container.shadow.color = col_secondary_50 if is_expense else col_primary_50
            btn_container.update()
            general_expenses_section.visible = is_expense
            general_expenses_section.update()

        type_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Text("Gelen Faturalar (Gider)", color=col_white, weight="bold", size=14),
                ft.Icon("swap_horiz", color=col_white, size=20)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            bgcolor=col_secondary, padding=ft.padding.symmetric(horizontal=20, vertical=10), border_radius=8, 
            on_click=toggle_invoice_type,
            shadow=ft.BoxShadow(blur_radius=5, color=col_secondary_50, offset=ft.Offset(0,2)), animate=ft.Animation(300, "easeOut")
        )

        def action_btn(text, icon, color, text_color=col_white, icon_color=col_white):
            return ft.ElevatedButton(
                text=text, icon=icon, bgcolor=color, color=text_color, icon_color=icon_color,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5), padding=15, elevation=1)
            )

        # Sağ Üst Köşe Butonları (YAN YANA)
        def right_corner_btn(text, icon, color):
            return ft.ElevatedButton(
                text=text, icon=icon, bgcolor=color, color=col_white,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5), padding=10)
            )

        right_buttons_row = ft.Row([
            right_corner_btn("Otomatik (QR)", "qr_code_scanner", "#3498DB"),
            right_corner_btn("Excel", "table_view", "#217346"),
            right_corner_btn("PDF", "picture_as_pdf", "#D32F2F"),
            right_corner_btn("Yazdır", "print", "#607D8B"),
        ], spacing=10)

        # Tek Satır Inputlar (4x2 DÜZENİ ve BİRAZ BÜYÜTÜLMÜŞ)
        input_line_1 = ft.Row([
            create_mini_input("Fatura No", width=140),
            create_mini_input("İrsaliye", width=140),
            create_mini_input("Tarih", width=120),
            create_mini_input("Firma", width=180),
        ], spacing=10)

        input_line_2 = ft.Row([
            create_mini_input("Malzeme", width=180),
            create_mini_input("Miktar", width=80),
            create_mini_input("KDV %", width=80),
            create_mini_input("Birim F.", width=100),
            ft.Container(
                height=35, width=90, border=ft.border.all(1, "#E0E0E0"), border_radius=8, bgcolor="#F5F5F5",
                content=ft.Dropdown(options=[ft.dropdown.Option("TL"), ft.dropdown.Option("USD")], value="TL", text_size=13, content_padding=ft.padding.only(left=10), border_color="transparent")
            ),
            create_mini_input("Toplam", width=120),
        ], spacing=10)

        operation_buttons = ft.Row([
            action_btn("Yeni / Temizle", "refresh", "#7F8C8D"),
            action_btn("Ekle", "add", "#27AE60"),
            action_btn("Güncelle", "update", "#2980B9"),
            action_btn("Sil", "delete", "#C0392B"),
        ], spacing=10)

        return ft.Container(
            alignment=ft.alignment.top_center, 
            padding=20,
            content=ft.Column([
                # Başlık ve Sağ Üst Butonlar için Row (Başlık solda, Butonlar sağda - YAN YANA)
                ft.Row([
                    ft.Column([ # Sol Taraf (Başlık ve Toggle)
                        ft.Row([ft.Text("Fatura Yönetimi", size=24, weight="bold", color=col_text)]),
                        ft.Container(height=10),
                        type_toggle_btn
                    ]),
                    right_buttons_row # Sağ Taraf (QR, Excel, PDF... - YAN YANA)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START, width=1200),
                
                ft.Container(height=20),

                # Inputlar (2 SATIR)
                ft.Container(content=ft.Column([input_line_1, input_line_2], spacing=10), width=1200),
                
                ft.Container(height=15),
                
                # İşlem Butonları
                ft.Container(content=operation_buttons, width=1200, alignment=ft.alignment.center_left),

                ft.Container(height=25),

                # Tablo (TAM GENİŞLİK)
                ft.Container(
                    bgcolor=col_white, padding=5, border_radius=0,
                    border=ft.border.all(1, "#CCCCCC"),
                    width=1200, 
                    content=ft.Column([create_invoice_table()], scroll=ft.ScrollMode.AUTO, height=400)
                ),
                
                ft.Container(content=general_expenses_section, width=1200)
                
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        )

    dashboard_content = ft.Container() 
    faturalar_page = create_invoices_page()
    raporlar_page = ft.Container(alignment=ft.alignment.center, content=ft.Text("Raporlar", size=30, color=col_text))

    def change_view(e):
        clicked_btn_data = e.control.data
        for btn in sidebar_column.controls:
             if isinstance(btn, SidebarButton):
                btn.is_selected = (btn.data == clicked_btn_data)
                btn.update_visuals()
        
        if clicked_btn_data == "home":
            content_area.content = dashboard_content
            threading.Thread(target=start_animations, daemon=True).start()
        elif clicked_btn_data == "faturalar":
            content_area.content = faturalar_page
        elif clicked_btn_data == "raporlar":
            content_area.content = raporlar_page
        
        content_area.update()

    logo_text = ft.Text("Excellent", size=24, weight="bold", color=col_text, visible=False)
    menu_icon = ft.IconButton(icon="menu", icon_color=col_text, on_click=toggle_sidebar)
    menu_row = ft.Row([menu_icon, logo_text], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    btn_home = SidebarButton("home_rounded", "Giriş", "home", True)
    btn_faturalar = SidebarButton("receipt_long_rounded", "Faturalar", "faturalar")
    btn_raporlar = SidebarButton("bar_chart_rounded", "Raporlar", "raporlar")
    btn_home.on_click = change_view
    btn_faturalar.on_click = change_view
    btn_raporlar.on_click = change_view

    sidebar_column = ft.Column([
        ft.Container(height=20), menu_row, ft.Container(height=30),
        btn_home, btn_faturalar, btn_raporlar,
    ], spacing=15, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    sidebar_container = ft.Container(
        width=90, height=900, bgcolor=col_white, 
        padding=ft.padding.symmetric(horizontal=15, vertical=20),
        content=sidebar_column, animate=ft.Animation(300, "easeOut"),
        shadow=ft.BoxShadow(blur_radius=10, color="#05000000")
    )

    # --- DASHBOARD İÇERİK ---
    def change_currency(currency_code):
        state["current_currency"] = currency_code
        currency_selector_container.content = create_currency_selector()
        currency_selector_container.update()

    def create_currency_selector():
        curr = state["current_currency"]
        return ft.Container(
            bgcolor=col_bg, border_radius=12, padding=4,
            content=ft.Row([
                currency_button("₺ TRY", "TRY", curr, change_currency),
                currency_button("$ USD", "USD", curr, change_currency),
                currency_button("€ EUR", "EUR", curr, change_currency),
            ], spacing=0, tight=True)
        )
    currency_selector_container = ft.Container(content=create_currency_selector())

    header = ft.Row([
        ft.Text("Genel Durum Paneli", size=26, weight="bold", color=col_text),
        ft.Row([
            ft.Container(bgcolor="#EAF2F8", padding=ft.padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                content=ft.Row([ft.Icon("currency_exchange", size=16, color=col_blue_donut), ft.Text("1 USD = 42.44 TL | 1 EUR = 48.94 TL", size=13, color=col_text_light, weight="w600")], spacing=10)
            ),
            currency_selector_container,
        ], spacing=20)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    stats_row = ft.Row([
        DonutStatCard("Anlık Net Kâr", "attach_money", col_blue_donut, "+15%", 11.7, 24.3, "₺ 11.7K"),
        DonutStatCard("Toplam Gelir", "arrow_upward", col_success, "+4%", 24.3, 30, "₺ 24.3K"),
        DonutStatCard("Toplam Gider", "arrow_downward", col_secondary, "-2%", 12.5, 30, "₺ 12.5K"),
        DonutStatCard("Aylık Ortalama", "pie_chart", "#FF5B5B", "+1%", 8.2, 15, "₺ 8.2K"),
    ], spacing=20)

    transactions_list_content = ft.Column([
            ft.Row([ft.Text("Son İşlemler", size=18, weight="bold", color=col_text), ft.Text("Tümünü Gör", size=13, color=col_primary, weight="bold")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=15),
            TransactionRow("Frontend Test Gideri", "25 Kas 2025", "1,500 TL", False),
            TransactionRow("Frontend Test Şirketi", "25 Kas 2025", "4,250 TL", True),
            TransactionRow("Genel Gider Fatura", "25 Kas 2025", "1,500 TL", False),
            TransactionRow("Entegrasyon Testi", "25 Kas 2025", "750 TL", False),
            TransactionRow("Danışmanlık Geliri", "24 Kas 2025", "12,000 TL", True),
            TransactionRow("Sunucu Kirası", "23 Kas 2025", "2,000 TL", False),
            TransactionRow("Mobil Uygulama", "22 Kas 2025", "15,000 TL", True),
            TransactionRow("Ofis Giderleri", "21 Kas 2025", "500 TL", False),
        ], spacing=5, scroll=ft.ScrollMode.AUTO)

    transactions_list = ft.Container(
        bgcolor=col_white, border_radius=20, padding=25, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450, content=transactions_list_content
    )

    chart_container = ft.Container(
        bgcolor=col_white, border_radius=20, padding=ft.padding.only(left=30, right=30, top=30, bottom=10), expand=2, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450,
        content=ft.Column([
            ft.Row([
                ft.Column([ft.Text("Performans Analizi", size=20, weight="bold", color=col_text), ft.Text("Yıllık gelir ve gider karşılaştırması", size=13, color=col_text_light)]),
                ft.Dropdown(width=100, options=[ft.dropdown.Option("2024"), ft.dropdown.Option("2025")], value="2024", on_change=on_year_change, border_radius=10, text_size=13, content_padding=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=20),
            ft.Container(content=line_chart, expand=True),
            ft.Row([
                ft.Row([ft.Container(width=10, height=10, bgcolor=col_primary, border_radius=2), ft.Text("Gelir", size=12, color="grey")], spacing=5),
                ft.Row([ft.Container(width=10, height=10, bgcolor=col_secondary, border_radius=2), ft.Text("Gider", size=12, color="grey")], spacing=5),
            ], alignment=ft.MainAxisAlignment.CENTER)
        ])
    )

    dashboard_layout = ft.Column([
        header, ft.Container(height=10), stats_row, ft.Container(height=10),
        ft.Row([chart_container, ft.Container(content=transactions_list, expand=1)], expand=True, spacing=20)
    ], spacing=10)

    dashboard_content.content = dashboard_layout
    content_area = ft.Container(expand=True, padding=30, content=dashboard_content)

    layout = ft.Row([sidebar_container, content_area], expand=True, spacing=0)
    page.add(layout)
    
    def start_animations():
        time.sleep(0.75) # HIZLANDIRILDI (1.0 -> 0.75)
        for donut in state["donuts"]: donut.start_animation()
        draw_snake_chart("2024")

    threading.Thread(target=start_animations, daemon=True).start()

ft.app(target=main)
