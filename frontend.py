# -*- coding: utf-8 -*- # Türkçe karakterler için eklendi
import sys
import os
import sqlite3
import json
from datetime import datetime
import math

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QMessageBox, QCalendarWidget,
    QTextEdit, QFileDialog, QStatusBar, QComboBox, QTabWidget,
    QGroupBox, QListWidget, QListWidgetItem, QCheckBox
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QPainterPath, QColor, QFont,
    QFontDatabase, QDoubleValidator, QTextCharFormat, QPixmap
)
from PyQt6.QtCore import Qt, QDate, QLocale, QTimer, QRectF, QPointF, QSize

import pyqtgraph as pg

# QR Processing import
try:
    from qr_fast import fatura_bilgilerini_isle_hizli
    QR_PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"UYARI: qr_fast.py modülü yüklenemedi ({e}). QR işleme özelliği devre dışı.")
    QR_PROCESSING_AVAILABLE = False

# Backend import
# <<< DÜZELTME 1: Backend İçe Aktarma ve Kapsam Hatası Düzeltildi >>> (Bu kısım zaten vardı, dokunulmadı)

# --- ÖNCE SAHTE (FALLBACK) BACKEND SINIFINI TANIMLAYIN ---
class Backend:  # Sahte (Fallback) Backend
    settings = {}
    exchange_rates = {}
    def get_summary_data(self, year=None): return {'net_kar': 0, 'aylik_ortalama': 0, 'son_gelirler': 0, 'toplam_giderler': 0}, {'income': [0]*12, 'expenses': [0]*12}
    def handle_invoice_operation(self, *args, **kwargs): 
        if len(args) > 0 and args[0] == 'get': return []  # Boş liste döndür, True değil
        return True
    def get_calculations_for_year(self, year): return ([{'kesilen': 0, 'gelen': 0, 'kdv': 0}]*12), ([{'kar': 0, 'vergi': 0, 'odenecek_kv': 0}]*4) # odenecek_kv eklendi
    def get_yearly_summary(self, year): return {'toplam_gelir': 0, 'toplam_gider': 0, 'yillik_kar': 0}
    def get_year_range(self): return [str(datetime.now().year)]
    def save_setting(self, key, value): print(f"AYAR KAYDETME (Backend yok): {key}={value}")
    def export_to_excel(self, path, data): print(f"Excel'e Aktarma İsteği (Backend yok): {path}")
    def get_monthly_data_for_year(self, year): return {'income': [0]*12, 'expenses': [0]*12}
    def convert_currency(self, value, from_curr, to_curr): return value

    class Signal:
        def connect(self, slot): pass
        def emit(self, *args, **kwargs): pass
    data_updated = Signal(); status_updated = Signal()

# --- ŞİMDİ GERÇEK BACKEND'İ İÇE AKTARMAYI DENEYİN ---
try:
    # Aynı dizinde (ExcellentMVP içinde) backend.py olduğunu varsayıyoruz
    from backend import Backend as RealBackend
    Backend = RealBackend # Başarılı olursa, sahte sınıfın üzerine yaz
    print("INFO: Gerçek backend.py başarıyla yüklendi.")
except ImportError as e:
    print(f"UYARI: backend.py dosyası bulunamadı ({e}). Sahte Backend özellikleri kullanılacak.")
except Exception as e:
    print(f"UYARI: backend.py yüklenirken beklenmedik bir hata oluştu ({e}). Sahte Backend özellikleri kullanılacak.")


# --- Stil ve Tema Tanımlamaları ---
LIGHT_THEME_PALETTE = {
    "page_background": "#f8f9fa", "main_card_frame": "#ffffff", "card_frame": "#ffffff",
    "card_border": "#e5eaf0", "text_primary": "#0b2d4d", "text_secondary": "#505050",
    "text_tertiary": "#606060", "title_color": "#0b2d4d", "page_title_color": "#000000",
    "table_background": "#FFFFFF", "table_border": "#D0D0D0", "table_header": "#F0F0F0",
    "table_selection": "#DFF0D8", "input_border": "#D0D0D0", "menu_background": "#ffffff",
    "menu_hover": "#f0f5fa", "menu_checked": "#e9f0f8", "graph_background": "w", "graph_foreground": "#404040",
    "notes_list_bg": "#FFFFFF", "notes_list_border": "#E0E0E0", "notes_list_item_selected_bg": "#007bff",
    "notes_list_item_selected_text": "#FFFFFF", "calendar_note_bg": "#28a745", "calendar_note_text": "#FFFFFF",
    "donut_base_color": "#E9ECEF", "donut_text_color": "#495057",
    # <<< YENİ: Not Defteri Renkleri >>>
    "notes_drawing_bg": "#FFCCCC",
    "notes_drawing_border": "#FF9999",
    "notes_drawing_label_bg": "#FF9999",
    "notes_drawing_text_color": "#333333"
}
STYLES = {}

def update_styles(palette):
    """Stil sözlüğünü günceller."""
    STYLES["palette"] = palette
    STYLES["page_background"] = f"background-color: {palette['page_background']};"
    STYLES["main_card_frame"] = f"QFrame {{ background-color: {palette['main_card_frame']}; border-radius: 12px; }}"
    STYLES["title"] = f"font-size: 26px; font-weight: 600; color: {palette['title_color']};"
    STYLES["page_title"] = f"font-size: 24px; font-weight: bold; margin-bottom: 5px; color: {palette['page_title_color']};"
    STYLES["card_frame"] = f"QFrame {{ background-color: {palette['card_frame']}; border: 1px solid {palette['card_border']}; border-radius: 12px; }}"
    STYLES["info_panel_title"] = f"font-size: 16px; font-weight: 600; color: {palette['text_primary']}; margin-bottom: 10px;"
    STYLES["table_style"] = (f"QTableWidget {{ background-color: {palette['table_background']}; border: 1px solid {palette['table_border']}; gridline-color: {palette['table_border']}; color: {palette['text_primary']}; selection-background-color: {palette['table_selection']}; selection-color: {palette['text_primary']}; }} QHeaderView::section {{ background-color: {palette['table_header']}; color: {palette['text_primary']}; font-weight: bold; padding: 5px; border: 1px solid {palette['table_border']}; }}")
    STYLES["input_style"] = f"padding: 8px; border: 1px solid {palette.get('input_border', '#D0D0D0')}; border-radius: 6px; font-size: 13px; color: {palette.get('text_primary', '#0b2d4d')}; background-color: {palette.get('card_frame', '#FFFFFF')};"
    STYLES["menu_frame_style"] = f"background-color: {palette['menu_background']};"
    STYLES["menu_button_style"] = (f"QPushButton {{ text-align: left; padding: 15px 20px; border: none; color: {palette['text_secondary']}; font-size: 15px; font-weight: 500; border-radius: 8px; background-color: transparent; }} QPushButton:hover {{ background-color: {palette['menu_hover']}; color: #0088ff; }} QPushButton:checked {{ background-color: {palette['menu_checked']}; color: {palette['text_primary']}; font-weight: 600; }}")
    STYLES["export_button"] = "padding: 8px 12px; background-color: #17a2b8; color: white; border-radius: 6px; font-weight: 600; font-size: 12px;"
    # <<< DÜZENLEME 2: Yıllık kâr etiketi stilleri kaldırıldı (artık tabloda) >>>
    # STYLES["yearly_profit_label_style"] = ...
    # STYLES["yearly_profit_value_style"] = ...
    STYLES["logo_text_style"] = f"font-size: 20px; font-weight: 600; color: {palette['text_primary']}; padding-left: 10px;"
    STYLES["notes_list_style"] = f"QListWidget {{ border: 1px solid {palette['notes_list_border']}; border-radius: 6px; padding: 5px; background-color: {palette['notes_list_bg']}; color: {palette['text_primary']}; }} QListWidget::item {{ padding: 8px; margin: 2px 0; border-radius: 4px; color: {palette['text_primary']}; }} QListWidget::item:selected {{ background-color: {palette['notes_list_item_selected_bg']}; color: {palette['notes_list_item_selected_text']}; }} QListWidget::item:hover {{ background-color: {palette['menu_hover']}; }}"
    STYLES["notes_date_label_style"] = f"font-size: 16px; font-weight: 600; color: {palette['text_primary']}; margin-bottom: 5px;"
    STYLES["notes_section_title_style"] = f"font-size: 14px; font-weight: 600; color: {palette['text_secondary']}; margin-top: 10px; margin-bottom: 5px;"
    STYLES["donut_label_style"] = f"font-size: 12px; color: {palette.get('text_secondary', '#505050')}; font-weight: 500;"

    # <<< YENİ/GÜNCEL STİLLER: Not Defteri ve Takvim için >>>
    STYLES["notes_drawing_frame"] = f"QFrame {{ background-color: {palette['notes_drawing_bg']}; border: 2px solid {palette['notes_drawing_border']}; border-radius: 8px; }}"
    STYLES["notes_drawing_label_bg"] = f"background-color: {palette['notes_drawing_label_bg']}; color: {palette['notes_drawing_text_color']}; font-weight: bold; padding: 5px; border-radius: 5px;"
    STYLES["notes_list_item_drawing_style"] = f"QListWidget {{ border: none; background-color: transparent; }} QListWidget::item {{ padding: 8px 5px; color: {palette['notes_drawing_text_color']}; background-color: transparent; border-bottom: 1px dashed {palette['notes_drawing_border']}; }} QListWidget::item:selected {{ background-color: {palette['notes_drawing_border']}; color: {palette['notes_list_item_selected_text']}; }}"
    STYLES["notes_buttons_drawing_style"] = "QPushButton { padding: 6px 10px; border-radius: 4px; font-size: 12px; } QPushButton#new_button_notes { background-color: #6c757d; color: white; } QPushButton#delete_button_notes { background-color: #dc3545; color: white; } QPushButton#save_button_notes { background-color: #28a745; color: white; }"


def show_styled_message_box(parent, icon, title, text, buttons):
    """ Temaya uygun (sabit açık tema) QMessageBox gösterir. """
    msg_box = QMessageBox(parent); msg_box.setWindowTitle(title); msg_box.setText(text); msg_box.setStandardButtons(buttons); msg_box.setIcon(icon)
    palette = LIGHT_THEME_PALETTE; bg_color = palette.get('main_card_frame', '#ffffff'); text_color = palette.get('text_primary', '#0b2d4d'); input_border = palette.get('input_border', '#D0D0D0'); menu_checked = palette.get('menu_checked', '#e0e0e0'); btn_bg = "#f0f0f0"; btn_text = "#333333"; btn_border = input_border
    msg_box.setStyleSheet(
        f"QMessageBox {{ background-color: {bg_color}; }} "
        f"QMessageBox QLabel {{ color: {text_color}; font-size: 14px; }} "
        f"QMessageBox QPushButton {{ padding: 6px 15px; border: 1px solid {btn_border}; border-radius: 5px; background-color: {btn_bg}; color: {btn_text}; min-width: 80px; }} "
        f"QMessageBox QPushButton:hover {{ background-color: {input_border}; }} "
        f"QMessageBox QPushButton:pressed {{ background-color: {menu_checked}; }}"
    )
    return msg_box.exec()

# --- Donut Grafik Widget ---
class DonutChartWidget(QWidget):
    def __init__(self, value=0, max_value=100, color=QColor("#007bff"), text="", parent=None):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value if max_value > 0 else 100
        self.color = QColor(color) if isinstance(color, str) else color
        self.label_text = text
        self.display_text = ""
        # <<< DÜZENLEME 1: Donutları küçültmek için boyut sınırları değiştirildi >>>
        self.setMinimumSize(120, 120)
        self.setMaximumSize(200, 200) # Maksimum boyutu da verdik ki çok büyümesin

    def setValue(self, value):
        self.value = value
        self.update()

    def setColor(self, color):
        self.color = QColor(color) if isinstance(color, str) else color
        self.update()

    def setMaxValue(self, max_val):
        self.max_value = max_val if max_val > 0 else 100
        self.update()

    def setText(self, text):
        self.label_text = text
        self.update()

    def setDisplayText(self, text):
        self.display_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(5, 5, -5, -5)
        if rect.width() <= 0 or rect.height() <= 0:
            return
        diameter = min(rect.width(), rect.height())
        thickness = diameter * 0.15
        outer_rect = QRectF(rect.center().x() - diameter / 2, rect.center().y() - diameter / 2, diameter, diameter)
        inner_rect = outer_rect.adjusted(thickness, thickness, -thickness, -thickness)
        base_color = QColor(STYLES.get("palette", {}).get("donut_base_color", "#E9ECEF"))
        painter.setBrush(base_color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        path_outer = QPainterPath(); path_outer.addEllipse(outer_rect); painter.drawPath(path_outer)

        if self.value > 0 and self.max_value > 0:
            display_value = max(0, self.value)
            angle = (display_value / self.max_value) * 360.0
            painter.setBrush(self.color)
            painter.drawPie(outer_rect, 90 * 16, -int(angle * 16))
        
        painter.setBrush(QColor(STYLES.get("palette", {}).get("card_frame", "#FFFFFF")))
        painter.drawEllipse(inner_rect)

        text_to_draw = ""
        font_size_multiplier = 0.12 # Oran korundu, donut büyüdüğü için yazı da büyüyecek

        if self.display_text:
            text_to_draw = self.display_text
            if len(text_to_draw) > 7:
                font_size_multiplier = 0.08
            elif len(text_to_draw) > 5:
                font_size_multiplier = 0.10
        else:
            percent_value = int((self.value / self.max_value) * 100) if self.max_value > 0 else 0
            text_to_draw = f"{percent_value}%"

        font = self.font()
        font.setPointSize(int(diameter * font_size_multiplier))
        font.setBold(True)
        painter.setFont(font)
        text_color = QColor(STYLES.get("palette", {}).get("donut_text_color", "#495057"))
        painter.setPen(text_color)
        painter.drawText(outer_rect, Qt.AlignmentFlag.AlignCenter, text_to_draw)


# --- Tekilleştirilmiş Fatura Sekmesi ---
class InvoiceTab(QWidget):
    def __init__(self, invoice_type, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.invoice_type = invoice_type
        self.current_invoice_id = None
        self.config = {
            "outgoing": {"title": "Giden Faturalar (Gelir)", "file_name": "giden_faturalar.xlsx"},
            "incoming": {"title": "Gelen Faturalar (Gider)", "file_name": "gelen_faturalar.xlsx"}
        }
        self._setup_ui()
        self._connect_signals()
        self.refresh_table()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addLayout(self._create_header_layout())
        main_layout.addLayout(self._create_form_layout())
        main_layout.addWidget(self._create_table())

    def _create_header_layout(self):
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.config[self.invoice_type]["title"])
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.export_button = QPushButton("Excel'e Aktar")
        header_layout.addWidget(self.export_button)
        return header_layout

    def _create_form_layout(self):
        form_layout = QVBoxLayout()
        fields_layout = QHBoxLayout()
        self.edit_fields = {}
        headers = ["İRSALİYE NO", "TARİH", "FİRMA", "MALZEME", "MİKTAR", "TOPLAM TUTAR", "BİRİM", "KDV %"]
        tr_locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
        for header in headers:
            key = header.replace("İ", "I").replace(" ", "_").replace("%", "yuzdesi").lower()
            if header == "BİRİM":
                widget = QComboBox()
                widget.addItems(["TL", "USD", "EUR"])
            else:
                widget = QLineEdit()
                placeholders = {"TARİH": "gg.aa.yyyy", "KDV %": "Örn: 20"}
                widget.setPlaceholderText(placeholders.get(header, header))
                if header in ["MİKTAR", "TOPLAM TUTAR", "KDV %"]:
                    validator = QDoubleValidator()
                    validator.setLocale(tr_locale)
                    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                    widget.setValidator(validator)
            self.edit_fields[key] = widget
            fields_layout.addWidget(widget)
        self.kdv_dahil_checkbox = QCheckBox("KDV Dahil")
        fields_layout.addWidget(self.kdv_dahil_checkbox)
        form_layout.addLayout(fields_layout)
        form_layout.addLayout(self._create_button_layout())
        return form_layout

    def _create_button_layout(self):
        button_layout = QHBoxLayout()
        self.new_button = QPushButton("Yeni / Temizle"); self.add_button = QPushButton("Ekle"); self.update_button = QPushButton("Güncelle"); self.delete_button = QPushButton("Sil")
        button_layout.addWidget(self.new_button); button_layout.addWidget(self.add_button); button_layout.addWidget(self.update_button); button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        return button_layout

    def _create_table(self):
        self.invoice_table = QTableWidget(); self.invoice_table.setColumnCount(10)
        table_headers = ["İRSALİYE NO", "TARİH", "FİRMA", "MALZEME", "MİKTAR", "TUTAR (TL)", "TUTAR (USD)", "TUTAR (EUR)", "KDV %", "KDV TUTARI"]
        self.invoice_table.setHorizontalHeaderLabels(table_headers); self.invoice_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.invoice_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); self.invoice_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); self.invoice_table.verticalHeader().setVisible(False)
        return self.invoice_table

    def _connect_signals(self):
        self.new_button.clicked.connect(self.clear_edit_fields)
        self.add_button.clicked.connect(lambda: self._handle_invoice_operation('add'))
        self.update_button.clicked.connect(lambda: self._handle_invoice_operation('update'))
        self.delete_button.clicked.connect(lambda: self._handle_invoice_operation('delete'))
        self.invoice_table.itemSelectionChanged.connect(self.on_row_selected)
        self.export_button.clicked.connect(self.export_table_data)
        if self.backend and hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'):
            self.backend.data_updated.connect(self.refresh_table)

    def gather_data_from_fields(self):
        data = {}
        numeric_keys_map = {"miktar": "miktar", "toplam_tutar": "toplam_tutar", "kdv_yuzdesi": "kdv_yuzdesi"}
        for key, field in self.edit_fields.items():
            if isinstance(field, QComboBox): data[key] = field.currentText()
            else:
                text_value = field.text()
                if key in numeric_keys_map:
                    backend_key = numeric_keys_map[key]
                    data[backend_key] = text_value.replace('.', '').replace(',', '.')
                else: data[key] = text_value
        data['kdv_dahil'] = self.kdv_dahil_checkbox.isChecked()
        return data

    def _handle_invoice_operation(self, operation):
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        if operation in ['update', 'delete'] and not self.current_invoice_id: show_styled_message_box(self, QMessageBox.Icon.Warning, "İşlem Başarısız","Lütfen önce bir fatura seçin.", QMessageBox.StandardButton.Ok); return
        if operation == 'delete':
            reply = show_styled_message_box(self, QMessageBox.Icon.Question, "Silme Onayı", "Bu faturayı silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return
        data = self.gather_data_from_fields()
        success = self.backend.handle_invoice_operation(operation, self.invoice_type, data=data, record_id=self.current_invoice_id)
        if success: self.clear_edit_fields()
        else: show_styled_message_box(self, QMessageBox.Icon.Warning, "İşlem Başarısız", "Veri kaydedilemedi. Lütfen tüm zorunlu alanları (İrsaliye No, Firma, Malzeme) doldurduğunuzdan emin olun.", QMessageBox.StandardButton.Ok)

    def refresh_table(self):
        self.invoice_table.setRowCount(0)
        if not self.backend: return
        invoices = self.backend.handle_invoice_operation('get', self.invoice_type)
        if invoices is None: invoices = []
        for inv in invoices:
            row_pos = self.invoice_table.rowCount()
            self.invoice_table.insertRow(row_pos)
            data_to_display = [inv.get('irsaliye_no', ''), inv.get('tarih', ''), inv.get('firma', ''), inv.get('malzeme', ''), str(inv.get('miktar', '')), f"{inv.get('toplam_tutar_tl', 0):,.2f}", f"{inv.get('toplam_tutar_usd', 0):,.2f}", f"{inv.get('toplam_tutar_eur', 0):,.2f}", f"{inv.get('kdv_yuzdesi', 0):.0f}%", f"{inv.get('kdv_tutari', 0):,.2f}"]
            for col_idx, data in enumerate(data_to_display):
                item = QTableWidgetItem(str(data))
                if col_idx >= 5: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.invoice_table.setItem(row_pos, col_idx, item)
            id_item = QTableWidgetItem(str(inv.get('id', '')))
            self.invoice_table.setVerticalHeaderItem(row_pos, id_item)
        self.invoice_table.resizeColumnsToContents()

    def on_row_selected(self):
        selected_rows = list(set(item.row() for item in self.invoice_table.selectedItems()))
        if not selected_rows: return
        selected_row = selected_rows[0]
        id_item = self.invoice_table.verticalHeaderItem(selected_row)
        if not id_item: return
        if not self.backend: return
        try: self.current_invoice_id = int(id_item.text())
        except (ValueError, TypeError): print(f"Hata: Geçersiz fatura ID'si - {id_item.text() if id_item else 'None'}"); return
        invoice_data = self.backend.handle_invoice_operation('get_by_id', self.invoice_type, record_id=self.current_invoice_id)
        if invoice_data:
            self.edit_fields["irsaliye_no"].setText(invoice_data.get('irsaliye_no', ''))
            self.edit_fields["tarih"].setText(invoice_data.get('tarih', ''))
            self.edit_fields["firma"].setText(invoice_data.get('firma', ''))
            self.edit_fields["malzeme"].setText(invoice_data.get('malzeme', ''))
            self.edit_fields["miktar"].setText(str(invoice_data.get('miktar', '')))
            kdv_yuzdesi = invoice_data.get('kdv_yuzdesi', '')
            self.edit_fields["kdv_yuzdesi"].setText(str(int(kdv_yuzdesi)) if kdv_yuzdesi and isinstance(kdv_yuzdesi, (int, float)) else str(kdv_yuzdesi))
            birim = invoice_data.get('birim', 'TL')
            matrah_tl = float(invoice_data.get('toplam_tutar_tl', 0))
            kdv_dahil = invoice_data.get('kdv_dahil', 0)
            original_total_amount_tl = matrah_tl
            if kdv_dahil and kdv_yuzdesi and float(kdv_yuzdesi) > 0: original_total_amount_tl = matrah_tl * (1 + float(kdv_yuzdesi) / 100)
            original_amount_in_currency = self.backend.convert_currency(original_total_amount_tl, 'TRY', birim)
            formatted_amount = f"{original_amount_in_currency:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            self.edit_fields["toplam_tutar"].setText(formatted_amount)
            birim_index = self.edit_fields["birim"].findText(birim)
            if birim_index != -1: self.edit_fields["birim"].setCurrentIndex(birim_index)
            else: self.edit_fields["birim"].setCurrentIndex(0)
            self.kdv_dahil_checkbox.setChecked(bool(kdv_dahil))

    def clear_edit_fields(self):
        self.invoice_table.clearSelection()
        for key, field in self.edit_fields.items():
            if isinstance(field, QComboBox): field.setCurrentIndex(0)
            else: field.clear()
        self.kdv_dahil_checkbox.setChecked(False)
        self.current_invoice_id = None

    def export_table_data(self):
        config = self.config[self.invoice_type]; file_path, _ = QFileDialog.getSaveFileName(self, f"{config['title']} Listesini Kaydet", config['file_name'], "Excel Dosyaları (*.xlsx)");
        if not file_path: return
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        invoices_data = self.backend.handle_invoice_operation('get', self.invoice_type);
        if not invoices_data: show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Yok", f"Dışa aktarılacak {self.invoice_type} faturası bulunamadı.", QMessageBox.StandardButton.Ok); return;
        export_data = []
        for inv in invoices_data:
            inv_copy = inv.copy()
            for key_to_remove in ['id', 'toplam_tutar_usd', 'toplam_tutar_eur']:
                if key_to_remove in inv_copy: del inv_copy[key_to_remove]
            export_data.append(inv_copy)
        sheets_data = {config["title"]: {"data": export_data}}; self.backend.export_to_excel(file_path, sheets_data); show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{config['title']} başarıyla dışa aktarıldı:\n{file_path}", QMessageBox.StandardButton.Ok)

    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"]); self.export_button.setStyleSheet(STYLES["export_button"]); self.invoice_table.setStyleSheet(STYLES["table_style"]); self.new_button.setStyleSheet("padding: 5px; background-color: #6c757d; color: white; border-radius: 5px;"); self.add_button.setStyleSheet("padding: 5px; background-color: #33A0A0; color: white; border-radius: 5px;"); self.update_button.setStyleSheet("padding: 5px; background-color: #0066CC; color: white; border-radius: 5px;"); self.delete_button.setStyleSheet("padding: 5px; background-color: #FF6666; color: white; border-radius: 5px;");
        for field in self.edit_fields.values(): field.setStyleSheet(STYLES["input_style"])

# --- NotesWidget (Takvim + Not Listesi/Düzenleme) ---
class NotesDatabase:
    def __init__(self, db_name="notes_mult.db"): self.conn = sqlite3.connect(db_name); self.conn.row_factory = sqlite3.Row; self.create_table()
    def create_table(self): self.conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, title TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"); self.conn.commit()
    def get_notes(self, date_str): cursor = self.conn.execute("SELECT id, title, content FROM notes WHERE date = ? ORDER BY created_at DESC", (date_str,)); return cursor.fetchall()
    def get_note_by_id(self, note_id): cursor = self.conn.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,)); return cursor.fetchone()
    def get_dates_with_notes(self): cursor = self.conn.execute("SELECT DISTINCT date FROM notes"); return [row['date'] for row in cursor.fetchall()]
    def save_note(self, date_str, title, content): self.conn.execute("INSERT INTO notes (date, title, content) VALUES (?, ?, ?)", (date_str, title, content)); self.conn.commit(); return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    def delete_note(self, note_id): self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,)); self.conn.commit()
    def update_note(self, note_id, title, content): self.conn.execute("UPDATE notes SET title = ?, content = ? WHERE id = ?", (title, content, note_id)); self.conn.commit()

# <<< YENİ: NotesWidget tamamen çizime göre düzenlendi >>>
class NotesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = NotesDatabase()
        self.selected_date = QDate.currentDate()
        self.current_note_id = None
        self.locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
        self.marked_dates = set()
        self._setup_ui()
        self._connect_signals()
        self.apply_styles()
        self.load_notes_for_selected_date()
        self.update_calendar_notes()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Takvim başlığı
        calendar_title = QLabel("takvim")
        calendar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.calendar_title_label = calendar_title # restyle için sakla
        main_layout.addWidget(calendar_title)

        # Takvim
        self.calendar = QCalendarWidget()
        self.calendar.setLocale(self.locale)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setGridVisible(True)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader) # Hafta numaralarını gizle

        # Takvim için QFrame kapsayıcı
        calendar_frame = QFrame()
        self.calendar_frame = calendar_frame # restyle için sakla
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(5, 5, 5, 5)
        calendar_layout.addWidget(self.calendar)
        main_layout.addWidget(calendar_frame)

        # Notlar başlığı
        notes_title = QLabel("notlar başlığı")
        notes_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_title_label = notes_title # restyle için sakla
        main_layout.addWidget(notes_title)

        # Not Listesi ve Giriş Alanı için QFrame kapsayıcı
        notes_content_frame = QFrame()
        self.notes_content_frame = notes_content_frame # restyle için sakla
        notes_content_layout = QVBoxLayout(notes_content_frame)
        notes_content_layout.setContentsMargins(5, 5, 5, 5)

        # Not listesi
        self.notes_list = QListWidget()
        self.notes_list.setAlternatingRowColors(False) # Alternatif renkleri kaldır
        self.notes_list.setMaximumHeight(150) # Yüksekliği sınırla
        notes_content_layout.addWidget(self.notes_list)

        # Giriş alanları
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Not başlığı...")
        notes_content_layout.addWidget(self.title_input)
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Not içeriği...")
        self.content_input.setFixedHeight(60) # Yüksekliği sabitle
        notes_content_layout.addWidget(self.content_input)

        # Butonlar
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        self.new_button = QPushButton("Yeni"); self.new_button.setObjectName("new_button_notes")
        self.save_button = QPushButton("Kaydet"); self.save_button.setObjectName("save_button_notes")
        self.delete_button = QPushButton("Sil"); self.delete_button.setObjectName("delete_button_notes")
        buttons_layout.addWidget(self.new_button); buttons_layout.addStretch(); buttons_layout.addWidget(self.delete_button); buttons_layout.addWidget(self.save_button)
        notes_content_layout.addLayout(buttons_layout)
        main_layout.addWidget(notes_content_frame)
        main_layout.addStretch()

    def _connect_signals(self):
        self.calendar.selectionChanged.connect(self._date_selected)
        self.notes_list.itemClicked.connect(self.note_selected)
        self.new_button.clicked.connect(self.clear_selection_and_inputs)
        self.save_button.clicked.connect(self.save_or_update_note)
        self.delete_button.clicked.connect(self.delete_note)

    def apply_styles(self):
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
        # Çerçeveler ve Başlıklar
        self.calendar_frame.setStyleSheet(STYLES.get("notes_drawing_frame", ""))
        self.notes_content_frame.setStyleSheet(STYLES.get("notes_drawing_frame", ""))
        self.calendar_title_label.setStyleSheet(STYLES.get("notes_drawing_label_bg", ""))
        self.notes_title_label.setStyleSheet(STYLES.get("notes_drawing_label_bg", ""))

        # Takvim İç Stili (Çerçeve dışında kalanlar)
        calendar_widget_style = f"""
            QCalendarWidget {{ background-color: transparent; border: none; }}
            QCalendarWidget QToolButton {{ color: {palette['notes_drawing_text_color']}; background-color: transparent; border: none; border-radius: 4px; font-size: 13px; padding: 4px 6px; margin: 1px; }}
            QCalendarWidget QToolButton:hover {{ background-color: rgba(255, 255, 255, 0.2); }} /* Hafif beyaz overlay */
            QWidget#qt_calendar_navigationbar {{ background-color: transparent; border-bottom: 1px solid {palette['notes_drawing_border']}; }}
            QCalendarWidget QAbstractItemView:enabled {{ font-size: 11px; color: {palette['notes_drawing_text_color']}; background-color: transparent; selection-background-color: {palette['notes_drawing_border']}; selection-color: {palette['notes_list_item_selected_text']}; }}
            QCalendarWidget QTableView {{ gridline-color: {palette['notes_drawing_border']}; }}
            QCalendarWidget QTableView::item {{ color: {palette['notes_drawing_text_color']}; border-radius: 0px; }}
            QCalendarWidget QTableView::item:selected {{ background-color: {palette['notes_drawing_border']}; color: {palette['notes_list_item_selected_text']}; font-weight: bold; }}
        """
        self.calendar.setStyleSheet(calendar_widget_style)

        # Input ve Liste Stilleri
        self.title_input.setStyleSheet(STYLES.get("input_style", "").replace(palette['card_frame'], 'transparent')) # Arkaplanı şeffaf yap
        self.content_input.setStyleSheet(STYLES.get("input_style", "").replace(palette['card_frame'], 'transparent')) # Arkaplanı şeffaf yap
        self.notes_list.setStyleSheet(STYLES.get("notes_list_item_drawing_style", ""))

        # Buton Stilleri
        self.new_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.delete_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.new_button.setObjectName("new_button_notes") # Emin olmak için tekrar ata
        self.delete_button.setObjectName("delete_button_notes")
        self.save_button.setObjectName("save_button_notes")

    def _date_selected(self):
        self.selected_date = self.calendar.selectedDate()
        self.clear_selection_and_inputs()
        self.load_notes_for_selected_date()

    def load_notes_for_selected_date(self):
        self.notes_list.clear(); date_str = self.selected_date.toString("yyyy-MM-dd"); notes = self.db.get_notes(date_str);
        if not notes:
            item = QListWidgetItem("Bu tarihe ait not bulunamadı.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(QColor(STYLES.get("palette", {}).get("text_tertiary", "#AAAAAA")))
            self.notes_list.addItem(item)
        else:
            for note in notes:
                item = QListWidgetItem(f"{note['title']}")
                item.setData(Qt.ItemDataRole.UserRole, note['id'])
                item.setToolTip(note['content'])
                self.notes_list.addItem(item)
        self.clear_selection_and_inputs()

    def note_selected(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if note_id is None: self.clear_selection_and_inputs(); return
        note = self.db.get_note_by_id(note_id)
        if note:
            self.current_note_id = note_id
            self.title_input.setText(note['title'])
            self.content_input.setPlainText(note['content'])
            self.save_button.setText("Güncelle")
            # Güncelle butonu stilini ayarla (isteğe bağlı, şimdilik aynı kalabilir)
            self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", "").replace("#28a745", "#007bff")) # Yeşil yerine mavi
            self.save_button.setObjectName("save_button_notes")
        else: self.clear_selection_and_inputs()

    def clear_selection_and_inputs(self):
        self.notes_list.clearSelection(); self.title_input.clear(); self.content_input.clear(); self.current_note_id = None; self.save_button.setText("Kaydet");
        self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", "")) # Orijinal stile dön
        self.save_button.setObjectName("save_button_notes")

    def save_or_update_note(self):
        title = self.title_input.text().strip(); content = self.content_input.toPlainText().strip();
        if not title: show_styled_message_box(self, QMessageBox.Icon.Warning, "Uyarı", "Not başlığı boş bırakılamaz!", QMessageBox.StandardButton.Ok); return
        date_str = self.selected_date.toString("yyyy-MM-dd");
        if self.current_note_id is not None: self.db.update_note(self.current_note_id, title, content)
        else: self.db.save_note(date_str, title, content)
        self.load_notes_for_selected_date(); self.update_calendar_notes(); self.clear_selection_and_inputs()

    def delete_note(self):
        if self.current_note_id is None: show_styled_message_box(self, QMessageBox.Icon.Warning, "Uyarı", "Lütfen silinecek bir not seçin.", QMessageBox.StandardButton.Ok); return
        reply = show_styled_message_box(self, QMessageBox.Icon.Question, "Silme Onayı", "Seçili notu silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.db.delete_note(self.current_note_id); self.load_notes_for_selected_date(); self.update_calendar_notes(); self.clear_selection_and_inputs()

    def update_calendar_notes(self):
        default_format = QTextCharFormat()
        for date in self.marked_dates: self.calendar.setDateTextFormat(date, default_format)
        self.marked_dates.clear()
        dates_with_notes = self.db.get_dates_with_notes()
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
        note_format = QTextCharFormat()
        note_format.setBackground(QBrush(QColor(palette.get("notes_drawing_border", "#FF9999")))) # Notlu gün rengi
        note_format.setForeground(QBrush(QColor(palette.get("notes_list_item_selected_text", "#FFFFFF"))))
        for date_str in dates_with_notes:
            try:
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if date.isValid(): self.calendar.setDateTextFormat(date, note_format); self.marked_dates.add(date)
            except Exception as e: print(f"Takvim işareti hatası: {date_str}, {e}")

    def restyle(self): self.apply_styles()


# <<< DEĞİŞİKLİK: HomePage sınıfı güncellendi >>>
class HomePage(QWidget):
    CONFIG = {"page_title": "Genel Durum Paneli", "currencies": [{"code": "TRY", "symbol": "₺"}, {"code": "USD", "symbol": "$"}, {"code": "EUR", "symbol": "€"}]}
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.current_currency = "TRY"
        self.current_graph_year = datetime.now().year
        self.base_data = {}
        self.monthly_data = {'income': [0]*12, 'expenses': [0]*12}
        self._setup_ui()
        self._connect_signals()
        if self.backend:
            self.backend.data_updated.connect(self.refresh_data)
        self.populate_graph_year_dropdown()
        self.refresh_data()

    def _get_monthly_data_for_year(self, year):
        if not self.backend: return {'income': [0]*12, 'expenses': [0]*12}
        monthly_results, _ = self.backend.get_calculations_for_year(year)
        income = [m['kesilen'] for m in monthly_results]
        expenses = [m['gelen'] for m in monthly_results]
        return {'income': income, 'expenses': expenses}

    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        self.main_content_card = QFrame()
        self.main_content_card.setObjectName("mainContentCard")
        self.main_content_card.setMaximumWidth(1400)
        self.main_content_card.setStyleSheet("#mainContentCard { background-color: transparent; border: none; }")
        
        card_layout = QVBoxLayout(self.main_content_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        
        card_layout.addLayout(self._create_header())
        
        # <<< DÜZENLEME 1: Donutlar 2x2'den 1x4'e (tek sıra) alındı >>>
        # --- Donutlar ve Altındaki Etiketler (Tek sıra halinde) ---
        all_donuts_layout = QHBoxLayout(); all_donuts_layout.setSpacing(15)
        self.donut_profit = DonutChartWidget(color="#a2d5f2"); all_donuts_layout.addWidget(self.donut_profit)
        self.donut_income = DonutChartWidget(color="#fceecb"); all_donuts_layout.addWidget(self.donut_income)
        self.donut_avg = DonutChartWidget(color="#f5d4e5"); all_donuts_layout.addWidget(self.donut_avg)
        self.donut_expense = DonutChartWidget(color="#c8e6c9"); all_donuts_layout.addWidget(self.donut_expense)

        all_labels_layout = QHBoxLayout(); all_labels_layout.setSpacing(15)
        self.donut_profit_label = QLabel("Anlık Net Kâr"); self.donut_profit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.donut_income_label = QLabel("Toplam Gelir"); self.donut_income_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.donut_avg_label = QLabel("Aylık Ortalama"); self.donut_avg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.donut_expense_label = QLabel("Toplam Gider"); self.donut_expense_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        all_labels_layout.addWidget(self.donut_profit_label)
        all_labels_layout.addWidget(self.donut_income_label)
        all_labels_layout.addWidget(self.donut_avg_label)
        all_labels_layout.addWidget(self.donut_expense_label)

        card_layout.addLayout(all_donuts_layout)
        card_layout.addLayout(all_labels_layout)
        # --- Donutlar Bitti ---
        
        bottom_layout = QHBoxLayout(); bottom_layout.setSpacing(20)
        
        graph_container = QFrame()
        graph_container_layout = QVBoxLayout(graph_container)
        graph_container_layout.setContentsMargins(0,0,0,0)
        
        graph_title_layout = QHBoxLayout()
        self.graph_title_label = QLabel(f"{self.current_graph_year} Yılı Analiz Grafiği")
        self.graph_year_dropdown = QComboBox(); self.graph_year_dropdown.setMinimumWidth(80)
        graph_title_layout.addWidget(self.graph_title_label); graph_title_layout.addStretch()
        graph_title_layout.addWidget(QLabel("Yıl:")); graph_title_layout.addWidget(self.graph_year_dropdown)
        graph_container_layout.addLayout(graph_title_layout)
        
        self.plot_widget = self._create_financial_graph_widget()
        graph_container_layout.addWidget(self.plot_widget)
        bottom_layout.addWidget(graph_container, 3)
        
        self.notes_widget = NotesWidget() # Direkt NotesWidget ekleniyor
        bottom_layout.addWidget(self.notes_widget, 2)

        card_layout.addLayout(bottom_layout)
        
        page_layout = QHBoxLayout(self); page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addStretch(); page_layout.addWidget(self.main_content_card); page_layout.addStretch()

    def _create_header(self):
        header_layout = QHBoxLayout(); self.title_label = QLabel(self.CONFIG["page_title"]); header_layout.addWidget(self.title_label); header_layout.addStretch(); self.exchange_rate_label = QLabel(); self.update_exchange_rate_display(); header_layout.addWidget(self.exchange_rate_label); header_layout.addSpacing(15); header_layout.addWidget(self._create_currency_selector()); self.export_button = QPushButton("Excel'e Aktar"); header_layout.addWidget(self.export_button)
        return header_layout

    def _create_currency_selector(self):
        self.currency_selector_frame = QFrame()
        layout = QHBoxLayout(self.currency_selector_frame)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(5)
        self.currency_group = QButtonGroup(self)
        for currency_info in self.CONFIG["currencies"]:
            btn = QPushButton(f"{currency_info['symbol']} {currency_info['code']}")
            btn.setCheckable(True); btn.setProperty("currency", currency_info["code"])
            self.currency_group.addButton(btn); layout.addWidget(btn)
            if currency_info["code"] == self.current_currency: btn.setChecked(True)
        return self.currency_selector_frame
        
    def _create_financial_graph_widget(self): plot_widget = pg.PlotWidget(); months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]; ticks = [(i, month) for i, month in enumerate(months)]; plot_widget.getAxis('bottom').setTicks([ticks]); self.legend = plot_widget.addLegend(offset=(10, 10)); self.income_line = pg.PlotDataItem(pen=pg.mkPen(color=(40, 167, 69), width=2.5), symbol='o', symbolBrush=(40, 167, 69), symbolSize=7, name='Gelir'); self.expenses_line = pg.PlotDataItem(pen=pg.mkPen(color=(220, 53, 69), width=2.5), symbol='o', symbolBrush=(220, 53, 69), symbolSize=7, name='Gider'); plot_widget.addItem(self.income_line); plot_widget.addItem(self.expenses_line); return plot_widget
    
    def _connect_signals(self): 
        self.currency_group.buttonClicked.connect(self.update_currency)
        self.export_button.clicked.connect(self.export_graph_data)
        self.graph_year_dropdown.currentTextChanged.connect(self.on_graph_year_changed)
        if self.backend and hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'): self.backend.data_updated.connect(self.refresh_data)
        
    def populate_graph_year_dropdown(self):
        years = [str(datetime.now().year)]
        if self.backend: years = self.backend.get_year_range()
        current_selection = self.graph_year_dropdown.currentText()
        self.graph_year_dropdown.blockSignals(True)
        self.graph_year_dropdown.clear()
        self.graph_year_dropdown.addItems(years if years else [])
        index = self.graph_year_dropdown.findText(current_selection) if current_selection in years else (0 if years else -1)
        self.graph_year_dropdown.setCurrentIndex(index)
        self.current_graph_year = int(self.graph_year_dropdown.currentText()) if self.graph_year_dropdown.count() > 0 else datetime.now().year
        self.graph_year_dropdown.blockSignals(False)
        self.graph_title_label.setText(f"{self.current_graph_year} Yılı Analiz Grafiği")
        
    def on_graph_year_changed(self, year_str):
        if year_str:
            try:
                self.current_graph_year = int(year_str)
                self.graph_title_label.setText(f"{self.current_graph_year} Yılı Analiz Grafiği")
                if self.backend: self.monthly_data = self._get_monthly_data_for_year(self.current_graph_year)
                else: self.monthly_data = {'income': [0]*12, 'expenses': [0]*12}
                self.update_graph()
            except ValueError: print(f"Hata: Geçersiz yıl formatı - {year_str}")
            except Exception as e: print(f"Grafik yılı değiştirme hatası: {e}")
        
    def restyle(self):
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE); self.main_content_card.setStyleSheet(STYLES.get("main_card_frame")); self.title_label.setStyleSheet(STYLES.get("title")); self.export_button.setStyleSheet(STYLES.get("export_button")); self.currency_selector_frame.setStyleSheet("background-color: #f0f5fa; border-radius: 8px; padding: 3px;");
        for btn in self.currency_group.buttons(): btn.setStyleSheet("QPushButton { background-color: transparent; border: none; padding: 6px 18px; color: #505050; font-weight: 500; border-radius: 6px; font-size: 13px; } QPushButton:checked { background-color: #ffffff; color: #0066CC; font-weight: 600; }")
        
        # Donut altı etiket stilleri
        if hasattr(self, 'donut_profit_label'):
            self.donut_profit_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_avg_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_income_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_expense_label.setStyleSheet(STYLES.get("donut_label_style"))
                
        self.load_donuts()
        
        self.graph_title_label.setStyleSheet(STYLES.get("info_panel_title"))
        self.graph_year_dropdown.setStyleSheet(STYLES.get("input_style"))
        graph_bg = STYLES.get("palette", {}).get("graph_background", 'w'); graph_fg = STYLES.get("palette", {}).get("graph_foreground", '#404040')
        pg.setConfigOption('background', graph_bg); pg.setConfigOption('foreground', graph_fg); self.plot_widget.setBackground(graph_bg); self.plot_widget.getAxis('left').setTextPen(graph_fg); self.plot_widget.getAxis('bottom').setTextPen(graph_fg); self.plot_widget.showGrid(x=True, y=True, alpha=0.2);
        if hasattr(self, 'legend'): self.legend.setLabelTextColor(graph_fg)
        
        # NotesWidget restyle
        if hasattr(self, 'notes_widget') and hasattr(self.notes_widget, 'restyle'):
            self.notes_widget.restyle()
        
    def refresh_data(self):
        if not self.backend: print("UYARI: Backend bulunamadığı için HomePage verileri yenilenemiyor."); self.base_data = {'net_kar':0, 'aylik_ortalama':0, 'son_gelirler':0, 'toplam_giderler':0}; self.monthly_data = {'income': [0]*12, 'expenses': [0]*12}; self.update_exchange_rate_display(); self.load_donuts(); self.update_graph(); self.populate_graph_year_dropdown(); return
        self.base_data, _ = self.backend.get_summary_data() 
        self.monthly_data = self._get_monthly_data_for_year(self.current_graph_year)
        self.update_exchange_rate_display(); self.load_donuts(); self.update_graph(); self.populate_graph_year_dropdown()
        if hasattr(self, 'notes_widget'): self.notes_widget.update_calendar_notes()
        
    def update_currency(self, button):
        self.current_currency = button.property("currency")
        self.refresh_data()
        
    def update_exchange_rate_display(self):
        if not self.backend: self.exchange_rate_label.setText("Kur bilgisi yok"); return
        try:
            rates = getattr(self.backend, 'exchange_rates', {})
            usd_tl = 1.0 / rates.get('USD', 0) if rates.get('USD', 0) > 0 else 0
            eur_tl = 1.0 / rates.get('EUR', 0) if rates.get('EUR', 0) > 0 else 0
            rate_text = f"💱 1 USD = {usd_tl:.2f} TL  |  1 EUR = {eur_tl:.2f} TL"
            self.exchange_rate_label.setText(rate_text)
            self.exchange_rate_label.setStyleSheet("font-size: 11px; color: #505050; padding: 5px 10px; background-color: #f0f5fa; border-radius: 6px;")
        except Exception as e: self.exchange_rate_label.setText("Kur bilgisi yok"); print(f"Kur gösterme hatası: {e}")
        
    def load_donuts(self):
        donuts_data = [{"value_key": "net_kar", "donut": self.donut_profit}, {"value_key": "aylik_ortalama", "donut": self.donut_avg}, {"value_key": "son_gelirler", "donut": self.donut_income}, {"value_key": "toplam_giderler", "donut": self.donut_expense}]
        max_donut_value = 0
        for data in donuts_data:
            value_tl = abs(self.base_data.get(data["value_key"], 0.0))
            if value_tl > max_donut_value: max_donut_value = value_tl
        if max_donut_value == 0: max_donut_value = 1
        
        for data in donuts_data:
            value_tl = self.base_data.get(data["value_key"], 0.0)
            converted_value, symbol = self._convert_value(value_tl)
            
            donut_fill_value = max(0, value_tl)
            data["donut"].setValue(donut_fill_value)
            data["donut"].setMaxValue(max_donut_value)
            
            formatted_donut_text = ""
            abs_converted_value_for_format = abs(converted_value)
            sign = "-" if converted_value < 0 else ""
            
            if abs_converted_value_for_format >= 1_000_000: formatted_donut_text = f"{sign}{symbol} {abs_converted_value_for_format / 1_000_000:.1f}M"
            elif abs_converted_value_for_format >= 1_000: formatted_donut_text = f"{sign}{symbol} {abs_converted_value_for_format / 1_000:.1f}K"
            else: formatted_donut_text = f"{sign}{symbol} {abs_converted_value_for_format:.0f}"
            
            data["donut"].setDisplayText(formatted_donut_text) 
            
    def _convert_value(self, value_tl: float):
        if not self.backend: return value_tl, "₺"
        currency_info = next((c for c in self.CONFIG["currencies"] if c["code"] == self.current_currency), None)
        symbol = currency_info["symbol"] if currency_info else ""
        converter = getattr(self.backend, 'convert_currency', lambda v, f, t: v)
        converted_value = converter(value_tl, 'TRY', self.current_currency)
        return converted_value, symbol
        
    def update_graph(self):
        if not self.backend: self.income_line.setData([], []); self.expenses_line.setData([], []); return
        converter = getattr(self.backend, 'convert_currency', lambda v, f, t: v); income = [converter(v, 'TRY', self.current_currency) for v in self.monthly_data.get('income', [0]*12)]; expenses = [converter(v, 'TRY', self.current_currency) for v in self.monthly_data.get('expenses', [0]*12)]; months_indices = list(range(12)); self.income_line.setData(x=months_indices, y=income); self.expenses_line.setData(x=months_indices, y=expenses); graph_fg = '#404040'; self.plot_widget.setLabel('left', f"Tutar ({self.current_currency})", color=graph_fg); self.plot_widget.autoRange()
        
    def export_graph_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Grafik Verisini Kaydet", f"{self.current_graph_year}_analiz_grafiği.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path: return
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        monthly_data_to_export = self._get_monthly_data_for_year(self.current_graph_year)
        if not any(monthly_data_to_export.get('income', [])) and not any(monthly_data_to_export.get('expenses', [])): show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Yok", f"{self.current_graph_year} yılı için dışa aktarılacak grafik verisi bulunamadı.", QMessageBox.StandardButton.Ok); return
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        converter = getattr(self.backend, 'convert_currency', lambda v, f, t: v)
        income_converted = [converter(v, 'TRY', self.current_currency) for v in monthly_data_to_export.get('income', [0]*12)]
        expenses_converted = [converter(v, 'TRY', self.current_currency) for v in monthly_data_to_export.get('expenses', [0]*12)]
        data = {"Ay": months, f"Gelir ({self.current_currency})": income_converted, f"Gider ({self.current_currency})": expenses_converted}
        sheets_data = {f"{self.current_graph_year} Grafik Verisi": {"data": data, "headers": list(data.keys())}}; self.backend.export_to_excel(file_path, sheets_data); show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{self.current_graph_year} yılı grafik verisi başarıyla dışa aktarıldı.", QMessageBox.StandardButton.Ok)

# --- Fatura Sayfası ---
class InvoicesPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self._setup_ui()
        self.restyle()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Header layout with title and QR button
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Fatura Yönetimi")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # QR Processing buttons
        if QR_PROCESSING_AVAILABLE:
            # QR İşleme butonu
            self.qr_button = QPushButton("⬜ QR İşle")
            self.qr_button.setToolTip("QR Kod ile Fatura İşleme\n\nKlasördeki PDF ve resim dosyalarından\nQR kodlarını okur ve Excel'e aktarır")
            self.qr_button.clicked.connect(self.open_qr_processing)
            header_layout.addWidget(self.qr_button)
            
            # QR'dan Gelen Fatura İmport butonu
            self.qr_import_incoming_button = QPushButton("📄 QR→Gelen")
            self.qr_import_incoming_button.setToolTip("QR Excel dosyasından Gelen Faturalara import et")
            self.qr_import_incoming_button.clicked.connect(lambda: self.import_qr_data_to_invoice('incoming'))
            header_layout.addWidget(self.qr_import_incoming_button)
            
            # QR'dan Giden Fatura İmport butonu
            self.qr_import_outgoing_button = QPushButton("📤 QR→Giden")
            self.qr_import_outgoing_button.setToolTip("QR Excel dosyasından Giden Faturalara import et")
            self.qr_import_outgoing_button.clicked.connect(lambda: self.import_qr_data_to_invoice('outgoing'))
            header_layout.addWidget(self.qr_import_outgoing_button)
        
        main_layout.addLayout(header_layout)
        
        self.tab_widget = QTabWidget()
        self.outgoing_tab = InvoiceTab("outgoing", self.backend)
        self.incoming_tab = InvoiceTab("incoming", self.backend)
        self.tab_widget.addTab(self.outgoing_tab, "Giden Faturalar (Gelir)")
        self.tab_widget.addTab(self.incoming_tab, "Gelen Faturalar (Gider)")
        main_layout.addWidget(self.tab_widget)

    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"])
        
        # QR buttons styling
        if QR_PROCESSING_AVAILABLE:
            qr_button_style = """
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 12px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """
            
            qr_import_style = """
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 12px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
                QPushButton:pressed {
                    background-color: #155724;
                }
            """
            
            if hasattr(self, 'qr_button'):
                self.qr_button.setStyleSheet(qr_button_style)
            if hasattr(self, 'qr_import_incoming_button'):
                self.qr_import_incoming_button.setStyleSheet(qr_import_style)
            if hasattr(self, 'qr_import_outgoing_button'):
                self.qr_import_outgoing_button.setStyleSheet(qr_import_style)
        
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
        tab_style = f""" QTabWidget::pane {{ border: 1px solid {palette.get('card_border', '#E0E0E0')}; border-top: none; border-radius: 0 0 8px 8px; background-color: {palette.get('card_frame', '#FFFFFF')}; }} QTabBar::tab {{ background-color: {palette.get('table_header', '#F0F0F0')}; color: {palette.get('text_secondary', '#505050')}; font-weight: 500; font-size: 14px; padding: 10px 20px; border: 1px solid {palette.get('card_border', '#E0E0E0')}; border-bottom: none; margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; }} QTabBar::tab:hover {{ background-color: {palette.get('menu_hover', '#f0f5fa')}; }} QTabBar::tab:selected {{ background-color: #d1e7dd; color: {palette.get('text_primary', '#0b2d4d')}; font-weight: 600; border-color: {palette.get('card_border', '#E0E0E0')}; }} """
        self.tab_widget.setStyleSheet(tab_style)
        self.outgoing_tab.restyle()
        self.incoming_tab.restyle()

    def refresh_data(self):
        self.outgoing_tab.refresh_table()
        self.incoming_tab.refresh_table()
    
    def _write_formatted_json(self, json_data, json_path):
        """JSON verilerini okunaklı formatta yazar - BASİT VE GÜVENİLİR"""
        try:
            # Standart json.dump kullan ama güzel formatla
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))
            print(f"✅ JSON dosyası başarıyla yazıldı: {json_path}")
        except Exception as e:
            print(f"❌ JSON yazma hatası: {e}")
            # Yedek basit yazma
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(json_data, ensure_ascii=False, indent=2))
                print(f"✅ Yedek yöntemle JSON yazıldı: {json_path}")
            except Exception as e2:
                print(f"❌ Yedek JSON yazma da başarısız: {e2}")
                raise

    def save_qr_data_to_json(self, qr_results, json_path):
        """QR verilerini JSON dosyasına kaydeder (sadece başarılı olanlar) - BASİT VE GÜVENİLİR"""
        print(f"🚀 JSON kaydetme başlatılıyor...")
        print(f"   📁 Hedef dosya: {json_path}")
        print(f"   📊 Toplam QR sonucu: {len(qr_results) if qr_results else 0}")
        
        if not qr_results:
            print("❌ QR sonucu listesi boş!")
            return False
        
        try:
            # BASİT VE GÜVENİLİR FİLTRELEME
            print(f"🔍 {len(qr_results)} QR sonucu filtreleniyor...")
            
            successful_files = []
            failed_count = 0
            
            for i, r in enumerate(qr_results):
                dosya_adi = r.get('dosya_adi', f'Dosya_{i}')
                durum = r.get('durum', 'Bilinmeyen')
                
                if durum == 'BAŞARILI':
                    successful_files.append(r)
                    print(f"✅ {dosya_adi} - Başarılı")
                else:
                    failed_count += 1
                    print(f"⏭️ {dosya_adi} - {durum} (Atlandı)")
            
            print(f"📊 Filtreleme tamamlandı: {len(successful_files)} başarılı, {failed_count} hatalı")
            
            if len(successful_files) == 0:
                print("❌ Hiç başarılı QR verisi yok, JSON kaydedilmiyor!")
                return False
            
            # JSON verisi hazırla
            json_data = {
                'timestamp': datetime.now().isoformat(),
                'total_processed_files': len(qr_results),
                'saved_successful_files': len(successful_files),
                'skipped_failed_files': failed_count,
                'success_rate_percentage': round((len(successful_files) / len(qr_results)) * 100, 1) if qr_results else 0,
                'qr_data': successful_files
            }
            
            print(f"💾 JSON verisi hazırlandı, kaydediliyor...")
            
            # JSON kaydet - yedekli sistemle
            try:
                self._write_formatted_json(json_data, json_path)
                print(f"✅ JSON başarıyla kaydedildi: {json_path}")
            except Exception as json_error:
                print(f"❌ Özel JSON yazma başarısız: {json_error}")
                print("🔄 Basit JSON yazma deneniyor...")
                
                # Yedek: Basit JSON yazma
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                print(f"✅ Basit yöntemle JSON kaydedildi: {json_path}")
            
            print(f"📊 Özet:")
            print(f"   ✅ Kaydedilen başarılı: {len(successful_files)}")
            print(f"   ❌ Atlanan hatalı: {failed_count}")
            print(f"   🎯 Başarı oranı: %{json_data['success_rate_percentage']}")
            print(f"   📁 Dosya boyutu: {round(os.path.getsize(json_path)/1024, 1)} KB")
            
            return True
            
        except Exception as e:
            print(f"❌ KRİTİK JSON kaydetme hatası: {e}")
            print(f"   Dosya yolu: {json_path}")
            print(f"   Veri tipi: {type(qr_results)}")
            return False
    
    def load_qr_data_from_json(self, json_path):
        """JSON dosyasından QR verilerini yükler (sadece başarılı olanlar)"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            qr_results = json_data.get('qr_data', [])
            print(f"✅ JSON dosyasından {len(qr_results)} başarılı QR verisi yüklendi")
            print(f"   📅 Tarih: {json_data.get('timestamp', 'Bilinmiyor')}")
            
            # Yeni format kontrolü
            if 'saved_successful_files' in json_data:
                print(f"   📊 Orijinal işlenen dosya: {json_data.get('total_processed_files', 'Bilinmiyor')}")
                print(f"   ✅ Kaydedilen başarılı: {json_data.get('saved_successful_files', len(qr_results))}")
                print(f"   ❌ Atlanan hatalı: {json_data.get('skipped_failed_files', 0)}")
                print(f"   🎯 Başarı oranı: %{json_data.get('success_rate_percentage', 0)}")
            else:
                # Eski format desteği
                total_files = json_data.get('total_files', len(qr_results))
                successful_files = json_data.get('successful_files', len(qr_results))
                print(f"   📊 Toplam: {successful_files}/{total_files}")
            
            return qr_results
        except Exception as e:
            print(f"❌ JSON yükleme hatası: {e}")
            return []

    def open_qr_processing(self):
        """QR kod işleme diyalogu açar"""
        if not QR_PROCESSING_AVAILABLE:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "QR İşleme Hatası", 
                                   "QR işleme modülü yüklenemedi. qr_fast.py dosyasının mevcut olduğundan emin olun.", 
                                   QMessageBox.StandardButton.Ok)
            return
        
        # Kullanıcıya seçenek sun: Yeni QR işleme mi, yoksa var olan JSON'dan yükleme mi?
        choice = show_styled_message_box(self, QMessageBox.Icon.Question, "QR İşleme Seçenekleri",
                                       "QR verilerini nasıl almak istiyorsunuz?\n\n"
                                       "• 'Yes' - Yeni klasörden QR kodları işle\n"
                                       "• 'No' - Daha önce kaydedilmiş JSON dosyasından yükle",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        
        if choice == QMessageBox.StandardButton.Cancel:
            return
        
        qr_results = []
        
        if choice == QMessageBox.StandardButton.Yes:
            # Yeni QR işleme
            # Klasör seçimi
            folder_path = QFileDialog.getExistingDirectory(self, "QR Kod İçeren Dosyaların Bulunduğu Klasörü Seçin")
            if not folder_path:
                return
            
            # JSON dosyası kayıt yeri seçimi
            json_path, _ = QFileDialog.getSaveFileName(self, "QR Verilerini JSON Olarak Kaydet", 
                                                     "qr_verileri.json", 
                                                     "JSON Dosyaları (*.json)")
            if not json_path:
                return
            
            # Excel dosyası kayıt yeri seçimi (isteğe bağlı)
            excel_choice = show_styled_message_box(self, QMessageBox.Icon.Question, "Excel Kaydı",
                                                  "QR verilerini Excel dosyasına da kaydetmek istiyor musunuz?",
                                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            excel_path = None
            if excel_choice == QMessageBox.StandardButton.Yes:
                excel_path, _ = QFileDialog.getSaveFileName(self, "QR Sonuçlarını Excel Olarak Kaydet", 
                                                           "qr_fatura_sonuclari.xlsx", 
                                                           "Excel Dosyaları (*.xlsx)")
        else:
            # Mevcut JSON dosyasından yükleme
            json_path, _ = QFileDialog.getOpenFileName(self, "QR Verileri JSON Dosyasını Seçin", 
                                                     "", "JSON Dosyaları (*.json)")
            if not json_path:
                return
            
            qr_results = self.load_qr_data_from_json(json_path)
            if qr_results:
                show_styled_message_box(self, QMessageBox.Icon.Information, "JSON Yüklendi",
                                       f"✅ {len(qr_results)} QR verisi başarıyla yüklendi!\n\n"
                                       f"Artık 'QR→Gelen' veya 'QR→Giden' butonlarını kullanarak "
                                       f"bu verileri faturalara aktarabilirsiniz.",
                                       QMessageBox.StandardButton.Ok)
                return qr_results
            else:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Yükleme Hatası",
                                       "JSON dosyasından QR verisi yüklenemedi.",
                                       QMessageBox.StandardButton.Ok)
                return
        
        progress_msg = None
        try:
            # QR işleme başlatılıyor mesajı
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("QR İşleme")
            progress_msg.setText("QR kodları işleniyor, lütfen bekleyin...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_msg.setModal(True)
            progress_msg.show()
            
            # QT eventlerini işle ki mesaj görünsün
            QApplication.processEvents()
            
            # QR işleme fonksiyonunu çağır
            if excel_path:
                result = fatura_bilgilerini_isle_hizli(folder_path, excel_path, max_workers=4)
            else:
                result = fatura_bilgilerini_isle_hizli(folder_path, "temp_qr_results.xlsx", max_workers=4)
            
            # Progress mesajını kesinlikle kapat
            if progress_msg:
                progress_msg.close()
                progress_msg.deleteLater()
                progress_msg = None
            
            # Eventleri tekrar işle
            QApplication.processEvents()
            
            if result is not None:
                # DataFrame'i dictionary formatına çevir (JSON için)
                qr_results = result.to_dict('records')
                
                # JSON dosyasına kaydet
                if self.save_qr_data_to_json(qr_results, json_path):
                    json_save_msg = f"✅ JSON dosyası: {json_path}\n"
                else:
                    json_save_msg = "❌ JSON kaydedilemedi!\n"
                
                successful_count = len(result[result['durum'] == 'BAŞARILI']) if 'durum' in result.columns else 0
                total_count = len(result)
                success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
                
                excel_msg = f"✅ Excel dosyası: {excel_path}\n" if excel_path else ""
                
                show_styled_message_box(self, QMessageBox.Icon.Information, "QR İşleme Tamamlandı", 
                                       f"QR kod işleme tamamlandı!\n\n"
                                       f"Toplam dosya: {total_count}\n"
                                       f"Başarılı: {successful_count} (%{success_rate:.1f})\n\n"
                                       f"{json_save_msg}"
                                       f"{excel_msg}\n"
                                       f"Artık 'QR→Gelen' veya 'QR→Giden' butonlarını kullanarak "
                                       f"bu verileri faturalara aktarabilirsiniz.", 
                                       QMessageBox.StandardButton.Ok)
                
                # Geçici Excel dosyasını sil (eğer oluşturulduysa)
                if not excel_path and os.path.exists("temp_qr_results.xlsx"):
                    os.remove("temp_qr_results.xlsx")
                
                return qr_results
            else:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "QR İşleme Hatası", 
                                       "QR kod işleme sırasında bir hata oluştu. Klasörde geçerli dosya bulunamadı veya işlem başarısız oldu.", 
                                       QMessageBox.StandardButton.Ok)
                
        except Exception as e:
            # Hata durumunda progress mesajını kesinlikle kapat
            if progress_msg:
                progress_msg.close()
                progress_msg.deleteLater()
                
            QApplication.processEvents()
            
            show_styled_message_box(self, QMessageBox.Icon.Critical, "QR İşleme Hatası", 
                                   f"QR kod işleme sırasında bir hata oluştu:\n{str(e)}", 
                                   QMessageBox.StandardButton.Ok)

    def parse_qr_invoice_data(self, qr_json_data):
        """QR'dan gelen JSON verilerini fatura alanlarına uygun formata dönüştürür"""
        parsed_data = {}  # Boş başla, sadece bulunan verileri ekle
        
        if not qr_json_data or not isinstance(qr_json_data, dict):
            return parsed_data
        
        try:
            # İrsaliye/Fatura No - Türk e-fatura sisteminde yaygın alanlar
            for key in ['invoiceId', 'faturaNo', 'belgeno', 'uuid', 'id', 'no', 'invoiceNumber', 'belgeNo', 'seriNo']:
                if key in qr_json_data and qr_json_data[key]:
                    invoice_id = str(qr_json_data[key]).strip()
                    if invoice_id and invoice_id not in ['null', 'None', '']:
                        parsed_data['irsaliye_no'] = invoice_id[:20]  # Max 20 karakter
                        break
            
            # Tarih - sadece QR'da varsa ekle
            for key in ['invoiceDate', 'faturaTarihi', 'tarih', 'date']:
                if key in qr_json_data and qr_json_data[key]:
                    date_str = str(qr_json_data[key])
                    # Tarih formatını düzenle (2024-01-15 -> 15.01.2024)
                    if '-' in date_str and len(date_str.split('-')) == 3:
                        parts = date_str.split('-')
                        if len(parts[0]) == 4:  # YYYY-MM-DD formatı
                            parsed_data['tarih'] = f"{parts[2]}.{parts[1]}.{parts[0]}"
                        else:  # DD-MM-YYYY formatı
                            parsed_data['tarih'] = date_str.replace('-', '.')
                    else:
                        parsed_data['tarih'] = date_str[:10]
                    break
            
            # Firma - sadece QR'da varsa ekle
            for key in ['sellerName', 'saticiUnvan', 'firma', 'supplier', 'company', 'companyName', 'firmaUnvan', 'aliciUnvan', 'buyerName']:
                if key in qr_json_data and qr_json_data[key]:
                    company_name = str(qr_json_data[key]).strip()
                    if company_name and company_name not in ['null', 'None', '']:
                        parsed_data['firma'] = company_name[:50]  # Max 50 karakter
                        break
            
            # Malzeme/Açıklama
            description_sources = []
            for key in ['description', 'aciklama', 'malzeme', 'item', 'productName']:
                if key in qr_json_data and qr_json_data[key]:
                    description_sources.append(str(qr_json_data[key]))
            
            # Eğer lineItems varsa, ilk item'ın bilgilerini al
            if 'lineItems' in qr_json_data and isinstance(qr_json_data['lineItems'], list) and qr_json_data['lineItems']:
                first_item = qr_json_data['lineItems'][0]
                if isinstance(first_item, dict):
                    for key in ['description', 'aciklama', 'productName', 'malzeme']:
                        if key in first_item and first_item[key]:
                            description_sources.append(str(first_item[key]))
                            break
            
            # Malzeme - sadece QR'da varsa ekle
            if description_sources:
                parsed_data['malzeme'] = description_sources[0][:100]  # Max 100 karakter
            
            # Miktar
            quantity = 0.0
            for key in ['quantity', 'miktar', 'adet', 'amount']:
                if key in qr_json_data and qr_json_data[key]:
                    try:
                        quantity = float(str(qr_json_data[key]).replace(',', '.'))
                        break
                    except (ValueError, TypeError):
                        continue
            
            # lineItems'dan miktar al
            if quantity == 0.0 and 'lineItems' in qr_json_data and isinstance(qr_json_data['lineItems'], list) and qr_json_data['lineItems']:
                first_item = qr_json_data['lineItems'][0]
                if isinstance(first_item, dict):
                    for key in ['quantity', 'miktar', 'adet']:
                        if key in first_item and first_item[key]:
                            try:
                                quantity = float(str(first_item[key]).replace(',', '.'))
                                break
                            except (ValueError, TypeError):
                                continue
            
            # Miktar - sadece QR'da varsa ve geçerliyse ekle
            if quantity > 0:
                parsed_data['miktar'] = quantity
            
            # Toplam Tutar - önce KDV matrahından hesapla
            total_amount = 0.0
            kdv_rate = 0.0
            
            # KDV Matrahı ve oranını bul (Türk e-fatura QR kodlarında sık görülen formatlar)
            for key in ['kdvmatrah', 'taxableAmount', 'matrah', 'netAmount']:
                if key in qr_json_data:
                    matrah_data = qr_json_data[key]
                    if isinstance(matrah_data, dict):
                        # kdvmatrah(20) formatı gibi - key içinde oran, value içinde tutar
                        for matrah_key, matrah_value in matrah_data.items():
                            try:
                                # Parantez içindeki sayıyı KDV oranı olarak al
                                if '(' in str(matrah_key) and ')' in str(matrah_key):
                                    rate_str = str(matrah_key).split('(')[1].split(')')[0]
                                    kdv_rate = float(rate_str)
                                elif str(matrah_key).replace('.', '').replace(',', '').isdigit():
                                    # Sadece sayı ise KDV oranı
                                    kdv_rate = float(str(matrah_key).replace(',', '.'))
                                
                                # Matrah tutarını al
                                if matrah_value and str(matrah_value).replace('.', '').replace(',', '').replace('-', '').isdigit():
                                    total_amount = float(str(matrah_value).replace(',', '.'))
                                    break
                            except (ValueError, TypeError):
                                continue
                    elif isinstance(matrah_data, (str, int, float)):
                        try:
                            total_amount = float(str(matrah_data).replace(',', '.'))
                        except (ValueError, TypeError):
                            continue
                    
                    if total_amount > 0:
                        break
            
            # Özel olarak kdvmatrah20, kdvmatrah18 gibi alanları ara
            for potential_key in qr_json_data.keys():
                if 'kdvmatrah' in str(potential_key).lower():
                    try:
                        # kdvmatrah20 -> oran: 20
                        key_str = str(potential_key).lower()
                        if key_str.startswith('kdvmatrah'):
                            rate_part = key_str.replace('kdvmatrah', '')
                            if rate_part.isdigit():
                                kdv_rate = float(rate_part)
                                total_amount = float(str(qr_json_data[potential_key]).replace(',', '.'))
                                break
                    except (ValueError, TypeError):
                        continue
            
            # Eğer matrah bulunamadıysa, toplam tutardan bak
            if total_amount == 0.0:
                for key in ['totalAmount', 'toplamTutar', 'total', 'amount', 'tutar']:
                    if key in qr_json_data and qr_json_data[key]:
                        try:
                            total_amount = float(str(qr_json_data[key]).replace(',', '.'))
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Toplam tutar - sadece QR'da varsa ve geçerliyse ekle
            if total_amount > 0:
                parsed_data['toplam_tutar'] = total_amount
            
            # KDV Yüzdesi
            if kdv_rate == 0.0:
                for key in ['taxRate', 'kdvOrani', 'kdv', 'vatRate']:
                    if key in qr_json_data and qr_json_data[key]:
                        try:
                            kdv_rate = float(str(qr_json_data[key]).replace(',', '.'))
                            break
                        except (ValueError, TypeError):
                            continue
            
            # KDV yüzdesi - sadece QR'da varsa ve geçerliyse ekle
            if kdv_rate > 0:
                parsed_data['kdv_yuzdesi'] = kdv_rate
            
            # Birim - para birimi (sadece QR'da varsa, yoksa varsayılan TL)
            currency_found = False
            for key in ['currency', 'birim', 'parabirimi', 'currencyCode']:
                if key in qr_json_data and qr_json_data[key]:
                    currency = str(qr_json_data[key]).upper()
                    if currency in ['TL', 'TRY', 'USD', 'EUR']:
                        parsed_data['birim'] = 'TL' if currency in ['TL', 'TRY'] else currency
                        currency_found = True
                        break
            
            # Para birimi bulunamazsa varsayılan değer verme, boş bırak
            if not currency_found:
                parsed_data['birim'] = 'TL'  # En yaygın olduğu için varsayılan TL
            
            # KDV Dahil durumu - sadece açıkça belirtilmişse ekle
            for key in ['kdvDahil', 'taxIncluded', 'vatIncluded']:
                if key in qr_json_data and qr_json_data[key] is not None:
                    parsed_data['kdv_dahil'] = bool(qr_json_data[key])
                    break
            
        except Exception as e:
            print(f"QR veri ayrıştırma hatası: {e}")
            print(f"QR JSON verisi: {qr_json_data}")
        
        # Debug bilgisi yazdır - sadece bulunan alanları göster
        print(f"QR'dan ayrıştırılan veriler:")
        for key, value in parsed_data.items():
            print(f"  {key}: '{value}'")
        
        if not parsed_data:
            print("  ⚠️ QR kodundan hiçbir veri ayrıştırılamadı!")
        
        return parsed_data
    
    def import_qr_data_to_invoice(self, invoice_type='outgoing'):
        """QR verilerini fatura formuna import eder"""
        if not QR_PROCESSING_AVAILABLE:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "QR İşleme Hatası", 
                                   "QR işleme modülü yüklenemedi. qr_fast.py dosyasının mevcut olduğundan emin olun.", 
                                   QMessageBox.StandardButton.Ok)
            return
        
        # Kullanıcıya veri kaynağı seçtir
        source_choice = show_styled_message_box(self, QMessageBox.Icon.Question, "Veri Kaynağı Seçimi",
                                              "QR verilerini nereden yüklemek istiyorsunuz?\n\n"
                                              "• 'Yes' - JSON dosyasından (Önerilen)\n"
                                              "• 'No' - Excel dosyasından",
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        
        if source_choice == QMessageBox.StandardButton.Cancel:
            return
        
        qr_data_list = []
        
        if source_choice == QMessageBox.StandardButton.Yes:
            # JSON dosyasından yükle
            json_path, _ = QFileDialog.getOpenFileName(self, "QR Verileri JSON Dosyasını Seçin", 
                                                     "", "JSON Dosyaları (*.json)")
            if not json_path:
                return
            
            qr_results = self.load_qr_data_from_json(json_path)
            if not qr_results:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Bulunamadı", 
                                       "JSON dosyasından QR verisi yüklenemedi.", 
                                       QMessageBox.StandardButton.Ok)
                return
            
            # Başarılı QR verilerini filtrele
            qr_data_list = [item for item in qr_results if item.get('durum') == 'BAŞARILI']
            
        else:
            # Excel dosyasından yükle (eski yöntem)
            excel_path, _ = QFileDialog.getOpenFileName(self, "QR Sonuçları Excel Dosyasını Seçin", 
                                                       "", "Excel Dosyaları (*.xlsx)")
            if not excel_path:
                return
            
            try:
                try:
                    import pandas as pd
                except ImportError:
                    show_styled_message_box(self, QMessageBox.Icon.Critical, "Kütüphane Hatası", 
                                           "pandas kütüphanesi yüklü değil. QR import özelliği için pandas gereklidir.\n\n"
                                           "Yüklemek için: pip install pandas", 
                                           QMessageBox.StandardButton.Ok)
                    return
                
                df = pd.read_excel(excel_path, engine='openpyxl')
                
                # Başarılı QR verilerini filtrele
                successful_data = df[df['durum'] == 'BAŞARILI']
                
                if len(successful_data) == 0:
                    show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Bulunamadı", 
                                           "Excel dosyasında başarılı QR verisi bulunamadı.", 
                                           QMessageBox.StandardButton.Ok)
                    return
                
                # DataFrame'i dictionary listesine çevir
                for index, row in successful_data.iterrows():
                    qr_data = {}
                    # DataFrame'deki JSON sütunlarını topla
                    for col in df.columns:
                        if col not in ['dosya_adi', 'durum'] and pd.notna(row[col]):
                            qr_data[col] = row[col]
                    
                    if qr_data:  # Boş değilse ekle
                        qr_data['dosya_adi'] = row.get('dosya_adi', f'Dosya_{index}')
                        qr_data['durum'] = 'BAŞARILI'
                        qr_data_list.append(qr_data)
                        
            except Exception as e:
                show_styled_message_box(self, QMessageBox.Icon.Critical, "Excel Okuma Hatası", 
                                       f"Excel dosyası okunurken hata oluştu:\n{str(e)}", 
                                       QMessageBox.StandardButton.Ok)
                return
        
        # Ortak işleme kısmı - hem JSON hem Excel için
        if not qr_data_list:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Bulunamadı", 
                                   "Başarılı QR verisi bulunamadı.", 
                                   QMessageBox.StandardButton.Ok)
            return
        
        try:
            # İlgili sekmeyi al
            target_tab = self.outgoing_tab if invoice_type == 'outgoing' else self.incoming_tab
            
            imported_count = 0
            error_count = 0
            skipped_count = 0
            
            # Kullanıcıya kaç adet fatura bulunduğunu sor
            choice = show_styled_message_box(self, QMessageBox.Icon.Question, "QR Import Onayı", 
                                           f"{len(qr_data_list)} adet başarılı QR verisi bulundu.\n\n"
                                           f"Bu verileri '{('Giden' if invoice_type == 'outgoing' else 'Gelen')} Faturalar' sekmesine import etmek istiyor musunuz?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if choice != QMessageBox.StandardButton.Yes:
                return
            
            for index, qr_item in enumerate(qr_data_list):
                try:
                    # QR item'dan json_data kısmını al (JSON'dan geliyorsa) veya kendisi (Excel'den geliyorsa)
                    if 'json_data' in qr_item and isinstance(qr_item['json_data'], dict):
                        qr_data = qr_item['json_data']
                    else:
                        # Excel'den gelen veri - kendisi zaten dictionary
                        qr_data = {k: v for k, v in qr_item.items() if k not in ['dosya_adi', 'durum']}
                    
                    # QR verisini fatura formatına dönüştür
                    parsed_data = self.parse_qr_invoice_data(qr_data)
                    
                    # Fatura alanlarına yerleştir - sadece QR'da bulunan verileri
                    if 'irsaliye_no' in parsed_data:
                        target_tab.edit_fields['irsaliye_no'].setText(parsed_data['irsaliye_no'])
                    if 'tarih' in parsed_data:
                        target_tab.edit_fields['tarih'].setText(parsed_data['tarih'])
                    if 'firma' in parsed_data:
                        target_tab.edit_fields['firma'].setText(parsed_data['firma'])
                    if 'malzeme' in parsed_data:
                        target_tab.edit_fields['malzeme'].setText(parsed_data['malzeme'])
                    if 'miktar' in parsed_data:
                        target_tab.edit_fields['miktar'].setText(str(parsed_data['miktar']))
                    if 'toplam_tutar' in parsed_data:
                        target_tab.edit_fields['toplam_tutar'].setText(str(parsed_data['toplam_tutar']))
                    if 'birim' in parsed_data:
                        target_tab.edit_fields['birim'].setCurrentText(parsed_data['birim'])
                    if 'kdv_yuzdesi' in parsed_data:
                        target_tab.edit_fields['kdv_yuzdesi'].setText(str(parsed_data['kdv_yuzdesi']))
                    if 'kdv_dahil' in parsed_data:
                        target_tab.kdv_dahil_checkbox.setChecked(parsed_data['kdv_dahil'])
                    
                    # Backend var mı kontrol et ve faturayı kaydet
                    if self.backend and hasattr(target_tab, '_handle_invoice_operation'):
                        # Backend ile faturayı kaydet
                        if target_tab._handle_invoice_operation('add'):
                            imported_count += 1
                            # Alanları temizle
                            target_tab.clear_edit_fields()
                        else:
                            error_count += 1
                    else:
                        # Backend yoksa sadece forma yerleştir
                        dosya_adi = qr_item.get('dosya_adi', f'Dosya_{index}')
                        print(f"Backend mevcut değil, veri sadece forma yerleştirildi: {dosya_adi}")
                        imported_count += 1
                        # Son kaydı görmek için temizleme yapma
                        break  # İlk kaydı göster ve dur
                        
                except Exception as e:
                    dosya_adi = qr_item.get('dosya_adi', f'Dosya_{index}')
                    print(f"{dosya_adi} import hatası: {e}")
                    error_count += 1
                    continue
            
            # Tabloyu yenile
            target_tab.refresh_table()
            
            # Sonuç mesajı
            result_msg = f"QR verilerinden fatura import işlemi tamamlandı!\n\n"
            result_msg += f"✅ Başarılı: {imported_count}\n"
            if error_count > 0:
                result_msg += f"❌ Hatalı: {error_count}\n"
            result_msg += f"📊 Toplam: {len(qr_data_list)}\n\n"
            
            if not self.backend:
                result_msg += "⚠️ Backend bağlantısı olmadığı için veriler sadece forma yerleştirildi.\n"
                result_msg += "Manuel olarak 'Ekle' butonuna basmanız gerekiyor."
            
            show_styled_message_box(self, QMessageBox.Icon.Information, "Import Tamamlandı", 
                                   result_msg, QMessageBox.StandardButton.Ok)
                                   
        except Exception as e:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "Import Hatası", 
                                   f"QR verisi import edilirken hata oluştu:\n{str(e)}", 
                                   QMessageBox.StandardButton.Ok)

# --- Dönemsel/Yıllık Gelir Sayfası ---
# <<< DÜZENLEME 2: Bu sınıf, Excel'e benzemesi için büyük ölçüde değiştirildi >>>
class MonthlyIncomePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self._setup_ui()
        self._connect_signals()
        self.populate_years_dropdown()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(10,10,10,10)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Dönemsel ve Yıllık Gelir"); header_layout.addWidget(self.title_label); header_layout.addStretch()
        self.tax_label = QLabel("Kurumlar Vergisi (%):"); self.tax_input = QLineEdit(); self.tax_input.setValidator(QDoubleValidator(0, 100, 2)); self.tax_input.setMaximumWidth(60); self.tax_input.setText(f"{getattr(self.backend, 'settings', {}).get('kurumlar_vergisi_yuzdesi', 22.0):.1f}")
        self.tax_save_btn = QPushButton("Kaydet"); self.tax_save_btn.setStyleSheet("background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px;"); self.tax_save_btn.setFixedWidth(60)
        header_layout.addWidget(self.tax_label); header_layout.addWidget(self.tax_input); header_layout.addWidget(self.tax_save_btn); header_layout.addSpacing(20)
        self.year_dropdown = QComboBox(); self.year_dropdown.setPlaceholderText("Yıl Seçin"); self.year_dropdown.setMinimumWidth(100)
        header_layout.addWidget(QLabel("Yıl:")); header_layout.addWidget(self.year_dropdown)
        self.export_button = QPushButton("Excel'e Aktar"); header_layout.addWidget(self.export_button)
        main_layout.addLayout(header_layout)
        
        tables_layout = QHBoxLayout()
        
        # Ana tabloyu 14 satır (12 ay + 2 toplam) ve 5 sütun olarak ayarla
        self.income_table = QTableWidget(14, 5) 
        self.income_table.setHorizontalHeaderLabels(["AYLAR", "GELİR (Kesilen)", "GİDER (Gelen)", "KDV FARKI", "ÖDENECEK VERGİ"])
        
        months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
        self.colors = {"mavi": "#D4EBF2", "pembe": "#F9E7EF", "sarı": "#FFF2D6", "yeşil": "#D9F2E7"}
        
        for row, month_name in enumerate(months):
            month_item = QTableWidgetItem(month_name); month_item.setFlags(month_item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.income_table.setItem(row, 0, month_item)

        # Toplam satır başlıklarını ekle
        total_item = QTableWidgetItem("GENEL TOPLAM")
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.income_table.setItem(12, 0, total_item)
        
        kar_zarar_item = QTableWidgetItem("YILLIK NET KÂR")
        kar_zarar_item.setFlags(kar_zarar_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.income_table.setItem(13, 0, kar_zarar_item)

        self.income_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.income_table.verticalHeader().setVisible(False)
        tables_layout.addWidget(self.income_table) # Sadece bu tabloyu ekle

        # self.profit_table kaldırıldı
        # yearly_group kaldırıldı
        
        main_layout.addLayout(tables_layout)
        main_layout.setStretchFactor(tables_layout, 1) # Tablonun tüm dikey alanı kaplamasını sağla

    def _connect_signals(self):
        self.year_dropdown.currentTextChanged.connect(self.refresh_data)
        self.export_button.clicked.connect(self.export_table_data)
        self.tax_save_btn.clicked.connect(self.save_tax_percentage)
        if self.backend and hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'):
            self.backend.data_updated.connect(self.refresh_data)

    def save_tax_percentage(self):
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için ayar kaydedilemiyor.", QMessageBox.StandardButton.Ok); return
        try:
            tax_percent = float(self.tax_input.text().replace(',', '.'))
            if 0 <= tax_percent <= 100: self.backend.save_setting('kurumlar_vergisi_yuzdesi', tax_percent)
            else: show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Vergi oranı 0-100 arasında olmalıdır.", QMessageBox.StandardButton.Ok)
        except ValueError: show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Geçerli bir sayı giriniz.", QMessageBox.StandardButton.Ok)

    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"])
        self.export_button.setStyleSheet(STYLES["export_button"])
        self.income_table.setStyleSheet(STYLES["table_style"])
        # profit_table, yearly_income_table, profit_label, profit_value stilleri kaldırıldı
        self.tax_input.setStyleSheet(STYLES["input_style"])
        self.year_dropdown.setStyleSheet(STYLES["input_style"])
        
        # Ay renkleri
        for row in range(12):
            month_item = self.income_table.item(row, 0)
            if month_item:
                color_key = "mavi" if row < 3 else "pembe" if row < 6 else "sarı" if row < 9 else "yeşil"
                month_item.setBackground(QBrush(QColor(self.colors[color_key])))

        # Toplam satırlarını biçimlendir
        try:
            palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
            total_bg_color = QColor(palette.get("table_header", "#F0F0F0"))
            total_font = QFont(); total_font.setBold(True)

            for col in range(5):
                # GENEL TOPLAM satırı
                item12 = self.income_table.item(12, col)
                if not item12: item12 = QTableWidgetItem(); self.income_table.setItem(12, col, item12)
                item12.setBackground(total_bg_color); item12.setFont(total_font)
                item12.setFlags(item12.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # YILLIK NET KÂR satırı (sadece 0 ve 4. sütunlar)
                if col == 0 or col == 4:
                    item13 = self.income_table.item(13, col)
                    if not item13: item13 = QTableWidgetItem(); self.income_table.setItem(13, col, item13)
                    item13.setBackground(total_bg_color); item13.setFont(total_font)
                    item13.setFlags(item13.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # YILLIK NET KÂR için hücreleri birleştir (Excel'deki gibi 0-3 arası)
            self.income_table.setSpan(13, 0, 1, 4) # Satır 13, Sütun 0'dan başla, 1 satır, 4 sütun kapla
            kar_item_label = self.income_table.item(13, 0)
            if kar_item_label: kar_item_label.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        except Exception as e:
            print(f"Toplam satırlarını stillerken hata: {e}")

    def populate_years_dropdown(self):
        years = [str(datetime.now().year)]
        if self.backend: years = self.backend.get_year_range()
        current_selection = self.year_dropdown.currentText()
        self.year_dropdown.blockSignals(True)
        self.year_dropdown.clear(); self.year_dropdown.addItems(years if years else [])
        index = self.year_dropdown.findText(current_selection) if current_selection in years else (0 if years else -1)
        self.year_dropdown.setCurrentIndex(index)
        self.year_dropdown.blockSignals(False)
        self.refresh_data() # Dropdown değişince veriyi yenile

    def refresh_data(self):
        if self.backend: self.tax_input.setText(f"{getattr(self.backend, 'settings', {}).get('kurumlar_vergisi_yuzdesi', 22.0):.1f}")
        year_str = self.year_dropdown.currentText();
        
        # Tüm veri hücrelerini temizle (14 satır, 1'den 4'e kadar sütunlar)
        for i in range(14):
            for j in range(1, 5): 
                self.income_table.setItem(i, j, QTableWidgetItem(""))
        
        # profit_table, yearly_income_table, profit_value temizlemeleri kaldırıldı
        if not year_str or not self.backend: return
        
        try:
            year = int(year_str)
            monthly_results, quarterly_results = self.backend.get_calculations_for_year(year)
            summary = self.backend.get_yearly_summary(year)

            total_kdv_farki = 0.0
            total_odenen_vergi = 0.0

            # Aylık verileri doldur
            for i, data in enumerate(monthly_results):
                kdv_farki = data.get('kdv', 0)
                total_kdv_farki += kdv_farki
                self.income_table.setItem(i, 1, QTableWidgetItem(f"{data.get('kesilen', 0):,.2f} TL"))
                self.income_table.setItem(i, 2, QTableWidgetItem(f"{data.get('gelen', 0):,.2f} TL"))
                self.income_table.setItem(i, 3, QTableWidgetItem(f"{kdv_farki:,.2f} TL"))

            # Dönemsel vergileri ayarla (Mart, Haziran, Eylül, Aralık)
            quarter_indices = {0: 2, 1: 5, 2: 8, 3: 11} # Çeyrek -> Ay İndeksi
            for q, data in enumerate(quarterly_results):
                odenecek_kv = data.get('odenecek_kv', data.get('vergi', 0))
                total_odenen_vergi += odenecek_kv
                if q in quarter_indices:
                    row_index = quarter_indices[q]
                    self.income_table.setItem(row_index, 4, QTableWidgetItem(f"{odenecek_kv:,.2f} TL"))

            # Satır 12: GENEL TOPLAM
            self.income_table.setItem(12, 1, QTableWidgetItem(f"{summary.get('toplam_gelir', 0):,.2f} TL"))
            self.income_table.setItem(12, 2, QTableWidgetItem(f"{summary.get('toplam_gider', 0):,.2f} TL"))
            self.income_table.setItem(12, 3, QTableWidgetItem(f"{total_kdv_farki:,.2f} TL"))
            self.income_table.setItem(12, 4, QTableWidgetItem(f"{total_odenen_vergi:,.2f} TL"))
            
            # Satır 13: YILLIK NET KÂR (Değeri son sütuna ata)
            self.income_table.setItem(13, 4, QTableWidgetItem(f"{summary.get('yillik_kar', 0):,.2f} TL"))
            
            # profit_table ve yearly_group ile ilgili doldurma kodları kaldırıldı

            # Tüm sayısal hücreleri sağa hizala
            for r in range(14):
                for c in range(1, 5):
                    item = self.income_table.item(r, c)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Stil (font, bg, birleştirme) için restyle'ı çağır
            self.restyle()

        except ValueError: print(f"Hata: Geçersiz yıl formatı - {year_str}")
        except Exception as e: print(f"Veri yenileme hatası (MonthlyIncomePage): {e}")

    def export_table_data(self):
        year_str = self.year_dropdown.currentText()
        if not year_str: show_styled_message_box(self, QMessageBox.Icon.Warning, "Yıl Seçilmedi", "Lütfen dışa aktarmak için bir yıl seçin.", QMessageBox.StandardButton.Ok); return
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        file_path, _ = QFileDialog.getSaveFileName(self, f"{year_str} Yılı Raporunu Kaydet", f"{year_str}_gelir_gider_raporu.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path: return
        
        # Excel'e aktarmayı yeni tablo formatına göre güncelle
        try:
            year = int(year_str)
            monthly_results, quarterly_results = self.backend.get_calculations_for_year(year)
            summary = self.backend.get_yearly_summary(year)
            months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            
            data_to_export = []
            total_kdv_farki_export = 0.0
            total_vergi_export = 0.0
            quarter_indices_map = {2: 0, 5: 1, 8: 2, 11: 3} # Ay index'i -> Çeyrek index'i

            for i, month_name in enumerate(months):
                monthly_data = monthly_results[i]
                kdv_farki = monthly_data.get('kdv', 0)
                total_kdv_farki_export += kdv_farki
                
                odenecek_vergi = 0.0
                if i in quarter_indices_map:
                    q_index = quarter_indices_map[i]
                    if q_index < len(quarterly_results):
                        odenecek_vergi = quarterly_results[q_index].get('odenecek_kv', quarterly_results[q_index].get('vergi', 0))
                        total_vergi_export += odenecek_vergi

                row_data = {
                    "AYLAR": month_name,
                    "GELİR (Kesilen)": monthly_data.get('kesilen', 0),
                    "GİDER (Gelen)": monthly_data.get('gelen', 0),
                    "KDV FARKI": kdv_farki,
                    "ÖDENECEK VERGİ": odenecek_vergi
                }
                data_to_export.append(row_data)
            
            # Toplam satırlarını ekle (Excel'e daha güzel görünmesi için boş satır)
            data_to_export.append({}) # Boş satır
            data_to_export.append({
                "AYLAR": "GENEL TOPLAM",
                "GELİR (Kesilen)": summary.get('toplam_gelir', 0),
                "GİDER (Gelen)": summary.get('toplam_gider', 0),
                "KDV FARKI": total_kdv_farki_export,
                "ÖDENECEK VERGİ": total_vergi_export
            })
            data_to_export.append({
                "AYLAR": "YILLIK NET KÂR",
                "GELİR (Kesilen)": None, # Bu hücreler boş olacak
                "GİDER (Gelen)": None,
                "KDV FARKI": None,
                "ÖDENECEK VERGİ": summary.get('yillik_kar', 0)
            })

            sheets_data = {f"{year_str} Raporu": {"data": data_to_export}}
            self.backend.export_to_excel(file_path, sheets_data)
            show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{year_str} yılı raporu başarıyla dışa aktarıldı:\n{file_path}", QMessageBox.StandardButton.Ok)
        except ValueError: show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", f"Geçersiz yıl formatı: {year_str}", QMessageBox.StandardButton.Ok)
        except Exception as e: show_styled_message_box(self, QMessageBox.Icon.Warning, "Dışa Aktarma Hatası", f"Excel'e aktarma sırasında bir hata oluştu: {e}", QMessageBox.StandardButton.Ok)


# --- Ana Pencere ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excellent Finans Yönetimi")
        self.setGeometry(100, 100, 1600, 900)
        self.backend = Backend()
        self.setup_main_window_ui() # <- BURADA KESİLMİŞTİ
        self.page_home = HomePage(self.backend)
        self.page_invoices = InvoicesPage(self.backend)
        self.page_monthly_income = MonthlyIncomePage(self.backend)
        self.all_pages = [self.page_home, self.page_invoices, self.page_monthly_income]
        for page in self.all_pages:
            self.content_widget.addWidget(page)
        self.apply_theme()
        self.connect_signals()
        self.set_page(0, self.btn_home)
        self.setStatusBar(QStatusBar(self))

    def setup_main_window_ui(self):
        self.main_widget = QWidget(); self.setCentralWidget(self.main_widget)
        main_layout = QHBoxLayout(self.main_widget); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        self.menu_frame = QFrame(); self.menu_frame.setFixedWidth(260)
        menu_layout = QVBoxLayout(self.menu_frame); menu_layout.setContentsMargins(10, 20, 10, 10); menu_layout.setSpacing(15)
        logo_widget = QWidget(); logo_layout = QHBoxLayout(logo_widget); logo_layout.setContentsMargins(10, 0, 0, 0); logo_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        logo_icon_label = QLabel(); logo_icon_label.setFixedSize(32, 32); logo_icon_label.setStyleSheet("background-color: #33A0A0; border-radius: 8px; border: 2px solid #0066CC;")
        self.logo_text_label = QLabel("Excellent"); logo_layout.addWidget(logo_icon_label); logo_layout.addSpacing(10); logo_layout.addWidget(self.logo_text_label); menu_layout.addWidget(logo_widget); menu_layout.addSpacing(30)
        self.btn_home = QPushButton("Giriş Paneli"); self.btn_invoices = QPushButton("Faturalar"); self.btn_monthly_income = QPushButton("Dönemsel/Yıllık Gelir")
        self.button_group = QButtonGroup(self); buttons = [self.btn_home, self.btn_invoices, self.btn_monthly_income]
        for btn in buttons: btn.setCheckable(True); self.button_group.addButton(btn); menu_layout.addWidget(btn)
        menu_layout.addStretch()
        self.content_widget = QStackedWidget(); self.content_widget.setStyleSheet("background-color: transparent;")
        main_layout.addWidget(self.menu_frame); main_layout.addWidget(self.content_widget)

    def connect_signals(self):
        if self.backend:
            if hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'): self.backend.data_updated.connect(self.refresh_all_pages)
            if hasattr(self.backend, 'status_updated') and hasattr(self.backend.status_updated, 'connect'): self.backend.status_updated.connect(lambda msg, timeout: self.statusBar().showMessage(msg, timeout))
        else: print("UYARI: Backend bulunamadığı için backend sinyalleri bağlanamadı.")
        if hasattr(self, 'btn_home'): self.btn_home.clicked.connect(lambda: self.set_page(0, self.btn_home))
        if hasattr(self, 'btn_invoices'): self.btn_invoices.clicked.connect(lambda: self.set_page(1, self.btn_invoices))
        if hasattr(self, 'btn_monthly_income'): self.btn_monthly_income.clicked.connect(lambda: self.set_page(2, self.btn_monthly_income))

    def refresh_all_pages(self):
        self.apply_theme()
        if not self.backend: return
        for i, page in enumerate(self.all_pages):
            page_backend = getattr(page, 'backend', None)
            if page_backend:
                if hasattr(page, 'refresh_data'):
                    try: page.refresh_data()
                    except Exception as e: print(f"    Error refreshing data in {type(page).__name__}: {e}")
                if hasattr(page, 'populate_years_dropdown'):
                    try: page.populate_years_dropdown()
                    except Exception as e: print(f"    Error populating dropdown in {type(page).__name__}: {e}")

    def apply_theme(self):
        palette = LIGHT_THEME_PALETTE; update_styles(palette)
        self.main_widget.setStyleSheet(STYLES['page_background'])
        self.menu_frame.setStyleSheet(STYLES["menu_frame_style"])
        self.logo_text_label.setStyleSheet(STYLES.get("logo_text_style"))
        if hasattr(self, 'button_group'):
            for btn in self.button_group.buttons(): btn.setStyleSheet(STYLES["menu_button_style"])
        if hasattr(self, 'all_pages'):
            for page in self.all_pages:
                if hasattr(page, 'restyle'):
                    try: page.restyle()
                    except Exception as e: print(f"Sayfa {type(page).__name__} restyle hatası: {e}")

    def set_page(self, index, button):
        if hasattr(self, 'content_widget') and 0 <= index < self.content_widget.count():
            self.content_widget.setCurrentIndex(index)
            if button and hasattr(self, 'button_group') and button in self.button_group.buttons():
                for btn in self.button_group.buttons(): btn.setChecked(btn == button)
        else: print(f"UYARI: Geçersiz sayfa indexi veya content_widget yok: {index}")


# --- Uygulama Başlatma ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        if hasattr(sys, '_MEIPASS'): project_path = sys._MEIPASS
        else: project_path = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(os.path.dirname(project_path), "fonts")
        font_path_regular = os.path.join(font_dir, "Inter_18pt-Regular.ttf")
        if os.path.exists(font_path_regular):
            font_id = QFontDatabase.addApplicationFont(font_path_regular)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families: app.setFont(QFont(font_families[0], 10))
                else: print("UYARI: Font dosyası yüklendi ama font ailesi bulunamadı.")
            else: print(f"UYARI: Font dosyası yüklenemedi: {font_path_regular}")
        else: print(f"UYARI: Font dosyası bulunamadı: {font_path_regular}\nSistem varsayılan fontları kullanılacak.")
    except Exception as e: print(f"Font yükleme sırasında hata: {e}")
    update_styles(LIGHT_THEME_PALETTE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

    