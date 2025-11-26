import flet as ft
import time
import threading
import datetime

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
    "animation_completed": False 
}

# --- YARDIMCI BİLEŞENLER ---

class ScaleButton(ft.Container):
    def __init__(self, icon, color, tooltip_text, width=50, height=45):
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
    def __init__(self, text, icon, color, width=130):
        super().__init__()
        self.bgcolor = color
        self.border_radius = 8
        self.padding = ft.padding.symmetric(horizontal=15, vertical=10)
        self.width = width
        self.animate_scale = ft.Animation(150, ft.AnimationCurve.EASE_OUT)
        self.animate = ft.Animation(200, "easeOut") 
        self.ink = False 
        
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
invoice_data = [
    {"no": "FAT-102", "irs": "IRS-102", "date": "2025-11-26", "firma": "Teknoloji A.Ş.", "malzeme": "Sunucu", "miktar": "1", "tutar": "15,000.00", "usd": "450.00", "eur": "410.00", "kdv": "3000 (%20)"},
    {"no": "FAT-101", "irs": "IRS-101", "date": "2025-11-25", "firma": "Yazılım Ltd.", "malzeme": "Lisans", "miktar": "5", "tutar": "5,000.00", "usd": "150.00", "eur": "135.00", "kdv": "1000 (%20)"},
    {"no": "FAT-100", "irs": "IRS-100", "date": "2025-11-20", "firma": "Ofis Malz.", "malzeme": "Kağıt", "miktar": "100", "tutar": "2,500.00", "usd": "75.00", "eur": "68.00", "kdv": "500 (%20)"},
]

def get_sorted_invoices(sort_option):
    data = invoice_data.copy()
    if sort_option == "newest": return data 
    elif sort_option == "date_desc": return sorted(data, key=lambda x: x["date"], reverse=True)
    elif sort_option == "date_asc": return sorted(data, key=lambda x: x["date"])
    return data

def create_invoice_table_content(sort_option="newest"):
    def header(t): return ft.DataColumn(ft.Text(t, weight="bold", color=col_white, size=12))
    def cell(t): return ft.DataCell(ft.Text(t, color="#333333", size=12))
    def on_row_select(e):
        e.control.selected = not e.control.selected
        e.control.update()

    current_data = get_sorted_invoices(sort_option)
    rows = []
    
    for inv in current_data:
        d_obj = datetime.datetime.strptime(inv["date"], "%Y-%m-%d")
        display_date = d_obj.strftime("%d.%m.%Y")
        rows.append(ft.DataRow(
            cells=[cell(inv["no"]), cell(inv["irs"]), cell(display_date), cell(inv["firma"]), cell(inv["malzeme"]), cell(inv["miktar"]), cell(inv["tutar"]), cell(inv["usd"]), cell(inv["eur"]), cell(inv["kdv"])],
            on_select_changed=on_row_select, selected=False
        ))

    return ft.DataTable(
        columns=[header("FATURA NO"), header("İRSALİYE NO"), header("TARİH"), header("FİRMA"), header("MALZEME"), header("MİKTAR"), ft.DataColumn(ft.Text("TUTAR (TL)", weight="bold", color=col_white, size=12), numeric=True), ft.DataColumn(ft.Text("TUTAR (USD)", weight="bold", color=col_white, size=12), numeric=True), ft.DataColumn(ft.Text("TUTAR (EUR)", weight="bold", color=col_white, size=12), numeric=True), header("KDV")],
        rows=rows, heading_row_color=col_table_header_bg, heading_row_height=45, data_row_max_height=40,
        vertical_lines=ft.border.BorderSide(0, "transparent"), horizontal_lines=ft.border.BorderSide(1, "#F0F0F0"),
        show_checkbox_column=True, column_spacing=15, width=float("inf")
    )

def create_donemsel_table():
    months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
    quarter_colors = [col_danger, col_success, col_secondary, col_blue_donut]
    def header(t): return ft.DataColumn(ft.Text(t, weight="bold", color=col_white, size=12))
    def cell(t): return ft.DataCell(ft.Text(t, color="#333333", size=12))
    
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

def create_grid_expenses():
    months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    expense_cards = []
    for m in months:
        card = ft.Container(bgcolor=col_white, border_radius=12, padding=10, width=140, height=85, shadow=ft.BoxShadow(blur_radius=5, color="#08000000", offset=ft.Offset(0,3)), border=ft.border.all(1, "#F0F0F0"), content=ft.Column([ft.Container(content=ft.Text(m, size=13, weight="bold", color=col_primary), alignment=ft.alignment.center), ft.Divider(height=5, color="transparent"), ft.TextField(value="0", text_size=14, text_style=ft.TextStyle(weight=ft.FontWeight.BOLD), color=col_text, text_align=ft.TextAlign.CENTER, border_color="#E0E0E0", focused_border_color=col_primary, height=35, content_padding=5, bgcolor="#FAFAFA", prefix_text="₺ ")], spacing=2, alignment=ft.MainAxisAlignment.CENTER))
        expense_cards.append(card)
    
    expense_buttons = ft.Container(padding=ft.padding.only(right=40), content=ft.Row([ScaleButton("table_view", "#217346", "Giderleri İndir (Excel)", width=40, height=40), ScaleButton("picture_as_pdf", "#D32F2F", "Giderleri İndir (PDF)", width=40, height=40), ScaleButton("print", "#607D8B", "Yazdır", width=40, height=40)], spacing=5))
    
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

# --- ANA UYGULAMA ---
def main(page: ft.Page):
    page.title = "Excellent MVP Dashboard"
    page.padding = 0
    page.bgcolor = col_bg
    page.window_width = 1400 
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Grafik Verileri ve Tanımı ---
    full_data = {"2024": {"gelir": [20, 50, 35, 75, 60, 85, 70, 90, 75, 100, 85, 115], "gider": [10, 30, 25, 40, 35, 50, 45, 60, 55, 70, 65, 80]}, "2025": {"gelir": [30, 60, 45, 85, 70, 95, 80, 100, 95, 120, 110, 130], "gider": [15, 35, 30, 50, 45, 60, 55, 70, 65, 85, 75, 90]}}
    
    line_chart = ft.LineChart(data_series=[ft.LineChartData(data_points=[], stroke_width=5, color=col_primary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_primary_50, transparent_white])), ft.LineChartData(data_points=[], stroke_width=5, color=col_secondary, curved=True, stroke_cap_round=True, below_line_gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[col_secondary_50, transparent_white]))], border=ft.border.all(0, "transparent"), bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(m, size=12, color=col_text_light)) for i, m in enumerate(["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"])], labels_size=30), left_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=0, label=ft.Text("0", size=10, color=col_text_light)), ft.ChartAxisLabel(value=50, label=ft.Text("50K", size=10, color=col_text_light)), ft.ChartAxisLabel(value=100, label=ft.Text("100K", size=10, color=col_text_light)), ft.ChartAxisLabel(value=150, label=ft.Text("150K", size=10, color=col_text_light))], labels_size=40), tooltip_bgcolor=tooltip_bg, min_y=0, max_y=150, min_x=0, max_x=11, expand=True, horizontal_grid_lines=ft.ChartGridLines(color="#F0F0F0", width=1, dash_pattern=[5, 5]), animate=None)

    def draw_snake_chart(year):
        if state["current_page"] != "home": return
        
        # SAYFADAN KONTROL: Eğer bileşen sayfada yoksa işlem yapma
        if not line_chart.page: return

        # Animasyon bittiyse direkt çiz
        if state["animation_completed"]:
            line_chart.data_series[0].data_points = [ft.LineChartDataPoint(i, full_data[year]["gelir"][i], tooltip=str(full_data[year]["gelir"][i])) for i in range(12)]
            line_chart.data_series[1].data_points = [ft.LineChartDataPoint(i, full_data[year]["gider"][i], tooltip=str(full_data[year]["gider"][i])) for i in range(12)]
            try: line_chart.update()
            except: pass
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
            
            line_chart.data_series[0].data_points.append(ft.LineChartDataPoint(i, gelir_data[i], tooltip=str(gelir_data[i])))
            line_chart.data_series[1].data_points.append(ft.LineChartDataPoint(i, gider_data[i], tooltip=str(gider_data[i])))
            
            try:
                if line_chart.page: line_chart.update()
            except: pass
            time.sleep(0.04) 
        
        state["animation_completed"] = True 
        try:
            if line_chart.page: line_chart.update()
        except: pass

    def on_year_change(e): 
        state["animation_completed"] = False 
        threading.Thread(target=draw_snake_chart, args=(e.control.value,), daemon=True).start()

    # --- SIDEBAR (GÜNCELLENDİ: GİRİŞ BUTONU DA STANDARDİZE EDİLDİ) ---
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
            initial_color = col_text_light
            self.icon_control = ft.Icon(icon_name, size=24, color=initial_color)
            self.text_control = ft.Text(text, size=15, weight="w600", visible=state["sidebar_expanded"], color=initial_color)
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
            
            # --- STANDART KURAL ---
            if self.is_selected:
                self.bgcolor = col_primary
                self.icon_control.color = col_white # Seçiliyse Beyaz
                self.text_control.color = col_white
                self.shadow = ft.BoxShadow(blur_radius=10, color=col_primary_50, offset=ft.Offset(0, 4))
            else:
                self.bgcolor = "transparent"
                self.icon_control.color = col_text_light # Değilse Gri
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

    # --- DÖNEMSEL GELİR SAYFASI ---
    def create_donemsel_page():
        right_buttons = ft.Container(
            padding=ft.padding.only(right=40),
            content=ft.Row([
                ScaleButton("table_view", "#217346", "Excel", width=45, height=40),
                ScaleButton("picture_as_pdf", "#D32F2F", "PDF", width=45, height=40),
                ScaleButton("print", "#607D8B", "Yazdır", width=45, height=40),
            ], spacing=8)
        )

        top_bar = ft.Row([
            ft.Row([
                create_vertical_input("Kurumlar Vergisi (%)", "22.0", width=140),
                ft.Container(
                    content=ft.Text("Kaydet", color=col_white, weight="bold", size=12),
                    bgcolor=col_success, padding=ft.padding.symmetric(horizontal=15, vertical=8), 
                    border_radius=8, alignment=ft.alignment.center, height=38,
                    on_hover=lambda e: e.control.update() 
                ),
                ft.Container(height=38, content=ft.Dropdown(options=[ft.dropdown.Option("2025"), ft.dropdown.Option("2024")], value="2025", text_size=12, content_padding=10, width=95, bgcolor=col_white, border_color=col_border, border_radius=8))
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=10),
            right_buttons
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        return ft.Container(alignment=ft.alignment.top_center, padding=30, content=ft.Column([ft.Row([ft.Text("Dönemsel ve Yıllık Gelir", size=26, weight="bold", color=col_text)]), ft.Container(height=15), ft.Container(content=top_bar, width=1100), ft.Container(height=15), ft.Container(width=1100, bgcolor=col_white, padding=20, border_radius=12, shadow=ft.BoxShadow(blur_radius=10, color="#1A000000", offset=ft.Offset(0, 5)), content=create_donemsel_table())], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO, expand=True))

    # --- FATURA SAYFASI ---
    def create_invoices_page():
        general_expenses_section = create_grid_expenses()
        general_expenses_section.visible = True

        table_container = ft.Container(width=1200, border_radius=12, shadow=ft.BoxShadow(blur_radius=15, color="#1A000000", offset=ft.Offset(0, 5)), bgcolor=col_white, content=create_invoice_table_content("newest"))

        def update_invoice_table(sort_option):
            table_container.content = create_invoice_table_content(sort_option)
            table_container.update()

        def on_sort_change(e): update_invoice_table(e.control.value)

        def toggle_invoice_type(e):
            state["invoice_type"] = "income" if state["invoice_type"] == "expense" else "expense"
            is_expense = state["invoice_type"] == "expense"
            active_color = col_secondary if is_expense else col_primary
            btn_container = e.control
            btn_container.content.controls[0].value = "Giden Faturalar (Gelir)" if not is_expense else "Gelen Faturalar (Gider)"
            btn_container.bgcolor = active_color
            btn_container.shadow.color = col_secondary_50 if is_expense else col_primary_50
            btn_container.update()
            general_expenses_section.visible = is_expense
            general_expenses_section.update()

        type_toggle_btn = ft.Container(content=ft.Row([ft.Text("Gelen Faturalar (Gider)", color=col_white, weight="bold", size=14), ft.Icon("swap_horiz", color=col_white, size=20)], alignment=ft.MainAxisAlignment.CENTER, spacing=5), bgcolor=col_secondary, padding=ft.padding.symmetric(horizontal=20, vertical=10), border_radius=8, on_click=toggle_invoice_type, ink=False, shadow=ft.BoxShadow(blur_radius=5, color=col_secondary_50, offset=ft.Offset(0,2)), animate=ft.Animation(100, "easeOut"))

        operation_buttons = ft.Row([AestheticButton("Yeni / Temizle", "refresh", "#7F8C8D", width=145), AestheticButton("Ekle", "add", col_success, width=110), AestheticButton("Güncelle", "update", col_blue_donut, width=125), AestheticButton("Sil", "delete", col_danger, width=110)], spacing=15)

        right_buttons_row = ft.Row([ScaleButton("qr_code_scanner", "#3498DB", "Kamerayı Aç / QR Ekle", width=50, height=45), ScaleButton("table_view", "#217346", "Excel Olarak İndir", width=50, height=45), ScaleButton("picture_as_pdf", "#D32F2F", "PDF Olarak İndir", width=50, height=45), ScaleButton("print", "#607D8B", "Yazdır", width=50, height=45)], spacing=10)
        
        right_buttons_container = ft.Container(content=right_buttons_row, padding=ft.padding.only(right=25))

        sort_dropdown = ft.Container(padding=ft.padding.only(left=20), content=ft.Dropdown(options=[ft.dropdown.Option("newest", "Son Eklenen"), ft.dropdown.Option("date_desc", "Yeniden Eskiye"), ft.dropdown.Option("date_asc", "Eskiden Yeniye")], value="newest", on_change=on_sort_change, width=160, text_size=13, label="Sıralama", border_radius=10, content_padding=10, bgcolor=col_white, border_color=col_border))

        controls_row = ft.Row([type_toggle_btn, sort_dropdown, ft.Container(expand=True), right_buttons_container], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        input_line_1 = ft.Row([create_vertical_input("Fatura No", "FAT-2025...", expand=True), create_vertical_input("İrsaliye", "IRS...", expand=True), create_vertical_input("Tarih", "25.11.2025", expand=True), create_vertical_input("Firma", "Firma seçiniz...", expand=True)], spacing=5)
        input_line_2 = ft.Row([create_vertical_input("Malzeme / Hizmet", "Ürün giriniz...", expand=2), create_vertical_input("Miktar", "0", expand=1), create_vertical_input("Girilecek Tutar", "0.00", expand=1), create_vertical_input("Para Birimi", "TL", is_dropdown=True, dropdown_options=["TL", "USD", "EUR"], expand=1), create_vertical_input("KDV Tutarı", "0.00", expand=1)], spacing=5)

        return ft.Container(alignment=ft.alignment.top_center, padding=30, content=ft.Column([
            ft.Row([ft.Text("Fatura Yönetimi", size=28, weight="bold", color=col_text)], width=1200),
            ft.Container(height=15), ft.Container(content=controls_row, width=1200), ft.Container(height=20),
            ft.Container(content=ft.Column([input_line_1, ft.Container(height=5), input_line_2], spacing=10), width=1200),
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

    def change_view(e):
        clicked_btn_data = e.control.data
        
        if state["current_page"] == "home" and clicked_btn_data != "home":
             state["animation_completed"] = True 
        
        state["current_page"] = clicked_btn_data
        
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
            content_area.content = donemsel_page 
        
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

    sidebar_column = ft.Column([ft.Container(height=20), menu_row, ft.Container(height=30), btn_home, btn_faturalar, btn_raporlar], spacing=15, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

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

    header = ft.Row([ft.Text("Genel Durum Paneli", size=26, weight="bold", color=col_text), ft.Row([ft.Container(bgcolor="#EAF2F8", padding=ft.padding.symmetric(horizontal=15, vertical=10), border_radius=8, content=ft.Row([ft.Icon("currency_exchange", size=16, color=col_blue_donut), ft.Text("1 USD = 42.44 TL | 1 EUR = 48.94 TL", size=13, color=col_text_light, weight="w600")], spacing=10)), currency_selector_container], spacing=20)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    stats_row = ft.Row([DonutStatCard("Anlık Net Kâr", "attach_money", col_blue_donut, "+15%", 11.7, 24.3, "₺ 11.7K"), DonutStatCard("Toplam Gelir", "arrow_upward", col_success, "+4%", 24.3, 30, "₺ 24.3K"), DonutStatCard("Toplam Gider", "arrow_downward", col_secondary, "-2%", 12.5, 30, "₺ 12.5K"), DonutStatCard("Aylık Ortalama", "pie_chart", "#FF5B5B", "+1%", 8.2, 15, "₺ 8.2K")], spacing=20)

    # --- SON İŞLEMLER ---
    mock_transactions = [
        {"title": "Frontend Test Gideri", "date": "2025-11-25", "display_date": "25 Kas 2025", "amount": "1,500 TL", "income": False},
        {"title": "Frontend Test Şirketi", "date": "2025-11-25", "display_date": "25 Kas 2025", "amount": "4,250 TL", "income": True},
        {"title": "Genel Gider Fatura", "date": "2025-11-25", "display_date": "25 Kas 2025", "amount": "1,500 TL", "income": False},
        {"title": "Entegrasyon Testi", "date": "2025-11-25", "display_date": "25 Kas 2025", "amount": "750 TL", "income": False},
        {"title": "Danışmanlık Geliri", "date": "2025-11-24", "display_date": "24 Kas 2025", "amount": "12,000 TL", "income": True},
        {"title": "Sunucu Kirası", "date": "2025-11-23", "display_date": "23 Kas 2025", "amount": "2,000 TL", "income": False},
        {"title": "Mobil Uygulama", "date": "2025-11-22", "display_date": "22 Kas 2025", "amount": "15,000 TL", "income": True},
        {"title": "Ofis Giderleri", "date": "2025-11-21", "display_date": "21 Kas 2025", "amount": "500 TL", "income": False},
        {"title": "Eski İşlem Örneği", "date": "2025-11-20", "display_date": "20 Kas 2025", "amount": "100 TL", "income": False},
    ]

    transactions_column = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    def update_transactions(filter_date=None):
        transactions_column.controls.clear()
        filtered_data = []
        if filter_date:
            str_date = filter_date.strftime("%Y-%m-%d")
            filtered_data = [t for t in mock_transactions if t["date"] == str_date]
        else:
            filtered_data = mock_transactions[:8]

        if not filtered_data:
            transactions_column.controls.append(ft.Container(content=ft.Text("Bu tarihte işlem bulunamadı.", color=col_text_light), alignment=ft.alignment.center, padding=20))
        else:
            for t in filtered_data:
                transactions_column.controls.append(TransactionRow(t["title"], t["display_date"], t["amount"], t["income"]))
        if transactions_column.page: transactions_column.update()

    update_transactions()

    def handle_date_change(e):
        if e.control.value: update_transactions(e.control.value)

    date_picker = ft.DatePicker(on_change=handle_date_change, cancel_text="İptal", confirm_text="Seç", help_text="İşlem Tarihini Seçin")
    page.overlay.append(date_picker)

    def reset_transactions(e): update_transactions(None)

    transactions_list_content = ft.Column([ft.Row([ft.Text("Son İşlemler", size=18, weight="bold", color=col_text), ft.Row([ft.IconButton(icon="calendar_month", icon_color=col_text_light, tooltip="Tarihe Göre Git", on_click=lambda _: date_picker.pick_date()), ft.TextButton("En Son Girilenler", style=ft.ButtonStyle(color=col_primary), on_click=reset_transactions)])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=15), transactions_column], spacing=5)

    transactions_list = ft.Container(bgcolor=col_white, border_radius=20, padding=25, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450, content=transactions_list_content)

    chart_container = ft.Container(bgcolor=col_white, border_radius=20, padding=ft.padding.only(left=30, right=30, top=30, bottom=10), expand=2, shadow=ft.BoxShadow(blur_radius=20, color="#08000000"), height=450, content=ft.Column([ft.Row([ft.Column([ft.Text("Performans Analizi", size=20, weight="bold", color=col_text), ft.Text("Yıllık gelir ve gider karşılaştırması", size=13, color=col_text_light)]), ft.Dropdown(width=100, options=[ft.dropdown.Option("2024"), ft.dropdown.Option("2025")], value="2024", on_change=on_year_change, border_radius=10, text_size=13, content_padding=10)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=20), ft.Container(content=line_chart, expand=True), ft.Row([ft.Row([ft.Container(width=10, height=10, bgcolor=col_primary, border_radius=2), ft.Text("Gelir", size=12, color="grey")], spacing=5), ft.Row([ft.Container(width=10, height=10, bgcolor=col_secondary, border_radius=2), ft.Text("Gider", size=12, color="grey")], spacing=5)], alignment=ft.MainAxisAlignment.CENTER)]))

    dashboard_layout = ft.Column([header, ft.Container(height=10), stats_row, ft.Container(height=10), ft.Row([chart_container, ft.Container(content=transactions_list, expand=1)], expand=True, spacing=20)], spacing=10)

    dashboard_content.content = dashboard_layout
    content_area = ft.Container(expand=True, padding=30, content=dashboard_content)

    layout = ft.Row([sidebar_container, content_area], expand=True, spacing=0)
    page.add(layout)
    
    def start_animations():
        time.sleep(0.5) 
        for donut in state["donuts"]: donut.start_animation()
        draw_snake_chart("2024")

    threading.Thread(target=start_animations, daemon=True).start()

ft.app(target=main)


