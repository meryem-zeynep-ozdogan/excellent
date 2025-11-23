# --- BU KODUN TAMAMINI KOPYALAYIP frontend.py İÇİNE YAPIŞTIRIN ---

# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import json
from datetime import datetime
import math
import logging

# QR işleme için backend'e güveniyoruz, bu yüzden bu bayrağı kaldırabiliriz.
# QR_PROCESSING_AVAILABLE = True 

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QMessageBox, QCalendarWidget,
    QTextEdit, QFileDialog, QStatusBar, QComboBox, QTabWidget,
    QGroupBox, QListWidget, QListWidgetItem, QCheckBox, QProgressDialog,
    QInputDialog, QFormLayout,
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QPainterPath, QColor, QFont,
    QFontDatabase, QDoubleValidator, QTextCharFormat, QPixmap,QIcon
)
from PyQt6.QtCore import Qt, QDate, QLocale, QTimer, QRectF, QPointF, QSize

# pyqtgraph'ı import et (eğer backend'den ayrıldıysa)
try:
    import pyqtgraph as pg
except ImportError:
    print("UYARI: pyqtgraph kütüphanesi eksik. 'pip install pyqtgraph' komutuyla kurun.")
    pg = None

# Backend'i import et
try:
    from backend import Backend
except ImportError as e:
    print(f"HATA: backend.py dosyası bulunamadı veya import edilemedi: {e}")
    # Backend olmadan çalışabilmek için sahte bir sınıf oluştur
    class Backend:
        data_updated = pyqtSignal()
        status_updated = pyqtSignal(str, int)
        def __init__(self, parent=None):
            print("SAHTE BACKEND BAŞLATILDI")
        def start_timers(self):
            pass # Hiçbir şey yapma
        def handle_invoice_operation(self, *args, **kwargs):
            return [] # Boş liste döndür
        def get_summary_data(self):
            return {}, {"income": [0]*12, "expenses": [0]*12} # Boş veri döndür
        def get_year_range(self):
            return [str(datetime.now().year)] # Geçerli yılı döndür
        def get_calculations_for_year(self, year):
            return [], [] # Boş veri döndür
        def get_yearly_summary(self, year):
            return {} # Boş veri döndür
        def convert_currency(self, amount, from_curr, to_curr):
            return amount # Dönüşüm yapma
        def save_setting(self, key, value):
            pass # Hiçbir şey yapma


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
    # Button colors - light theme
    "button_bg": "#6c757d", "button_text": "#ffffff", "button_border": "#6c757d",
    "button_bg_hover": "#5a6268", "button_border_hover": "#545b62", "button_bg_pressed": "#545b62",
    "button_bg_disabled": "#6c757d", "button_border_disabled": "#6c757d", "button_text_disabled": "#ffffff",
    "button_success_bg": "#198754", "button_success_text": "#ffffff", "button_success_border": "#198754",
    "button_success_bg_hover": "#157347", "button_success_border_hover": "#146c43", "button_success_bg_pressed": "#146c43",
    "button_warning_bg": "#0d6efd", "button_warning_text": "#ffffff", "button_warning_border": "#0d6efd",
    "button_warning_bg_hover": "#0a58ca", "button_warning_border_hover": "#0951ba", "button_warning_bg_pressed": "#0951ba",
    "button_danger_bg": "#dc3545", "button_danger_text": "#ffffff", "button_danger_border": "#dc3545",
    "button_danger_bg_hover": "#c82333", "button_danger_border_hover": "#bd2130", "button_danger_bg_pressed": "#bd2130",
    # <<< YENİ: Not Defteri Renkleri >>>
    "notes_drawing_bg": "#FFCCCC", "notes_drawing_border": "#FF9999",
    "notes_drawing_label_bg": "#FF9999", "notes_drawing_text_color": "#333333"
}

DARK_THEME_PALETTE = {
    "page_background": "#1e1e1e", "main_card_frame": "#2d2d2d", "card_frame": "#2d2d2d",
    "card_border": "#404040", "text_primary": "#ffffff", "text_secondary": "#cccccc",
    "text_tertiary": "#aaaaaa", "title_color": "#ffffff", "page_title_color": "#ffffff",
    "table_background": "#2d2d2d", "table_border": "#404040", "table_header": "#383838",
    "table_selection": "#0d6efd", "input_border": "#404040", "menu_background": "#2d2d2d",
    "menu_hover": "#383838", "menu_checked": "#0d6efd", "graph_background": "#2d2d2d", "graph_foreground": "#ffffff",
    "notes_list_bg": "#2d2d2d", "notes_list_border": "#404040", "notes_list_item_selected_bg": "#0d6efd",
    "notes_list_item_selected_text": "#ffffff", "calendar_note_bg": "#198754", "calendar_note_text": "#ffffff",
    "donut_base_color": "#383838", "donut_text_color": "#ffffff",
    # Button colors - dark theme
    "button_bg": "#6c757d", "button_text": "#ffffff", "button_border": "#6c757d",
    "button_bg_hover": "#5a6268", "button_border_hover": "#545b62", "button_bg_pressed": "#545b62",
    "button_bg_disabled": "#6c757d", "button_border_disabled": "#6c757d", "button_text_disabled": "#cccccc",
    "button_success_bg": "#198754", "button_success_text": "#ffffff", "button_success_border": "#198754",
    "button_success_bg_hover": "#157347", "button_success_border_hover": "#146c43", "button_success_bg_pressed": "#146c43",
    "button_warning_bg": "#0d6efd", "button_warning_text": "#ffffff", "button_warning_border": "#0d6efd",
    "button_warning_bg_hover": "#0a58ca", "button_warning_border_hover": "#0951ba", "button_warning_bg_pressed": "#0951ba",
    "button_danger_bg": "#dc3545", "button_danger_text": "#ffffff", "button_danger_border": "#dc3545",
    "button_danger_bg_hover": "#c82333", "button_danger_border_hover": "#bd2130", "button_danger_bg_pressed": "#bd2130",
    # Not Defteri Renkleri - dark theme
    "notes_drawing_bg": "#4d2d2d", "notes_drawing_border": "#666666",
    "notes_drawing_label_bg": "#666666", "notes_drawing_text_color": "#ffffff"
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
    STYLES["combobox_style"] = (f"QComboBox {{ "
        f"padding: 8px 12px; "
        f"border: 1px solid {palette.get('input_border', '#D0D0D0')}; "
        f"border-radius: 6px; "
        f"font-size: 13px; "
        f"color: {palette.get('text_primary', '#0b2d4d')}; "
        f"background-color: {palette.get('card_frame', '#FFFFFF')}; "
        f"selection-background-color: {palette.get('table_selection', '#DFF0D8')}; "
        f"}} "
        f"QComboBox:drop-down {{ "
        f"subcontrol-origin: padding; "
        f"subcontrol-position: top right; "
        f"width: 15px; "
        f"border-left-width: 1px; "
        f"border-left-color: {palette.get('input_border', '#D0D0D0')}; "
        f"border-left-style: solid; "
        f"border-top-right-radius: 3px; "
        f"border-bottom-right-radius: 3px; "
        f"}} "
        f"QComboBox::down-arrow {{ "
        f"image: none; "
        f"border-left: 3px solid transparent; "
        f"border-right: 3px solid transparent; "
        f"border-top: 5px solid {palette.get('text_secondary', '#505050')}; "
        f"margin-left: 3px; "
        f"}} "
        f"QComboBox QAbstractItemView {{ "
        f"border: 1px solid {palette.get('input_border', '#D0D0D0')}; "
        f"background-color: {palette.get('card_frame', '#FFFFFF')}; "
        f"color: {palette.get('text_primary', '#0b2d4d')}; "
        f"selection-background-color: {palette.get('table_selection', '#DFF0D8')}; "
        f"}})")
    STYLES["menu_frame_style"] = f"background-color: {palette['menu_background']};"
    STYLES["menu_button_style"] = (f"QPushButton {{ text-align: left; padding: 15px 20px; border: none; color: {palette['text_secondary']}; font-size: 15px; font-weight: 500; border-radius: 8px; background-color: transparent; }} QPushButton:hover {{ background-color: {palette['menu_hover']}; color: #0088ff; }} QPushButton:checked {{ background-color: {palette['menu_checked']}; color: {palette['text_primary']}; font-weight: 600; }}")
    STYLES["export_button"] = "padding: 8px 12px; background-color: #17a2b8; color: white; border-radius: 6px; font-weight: 600; font-size: 12px;"
    STYLES["logo_text_style"] = f"font-size: 20px; font-weight: 600; color: {palette['text_primary']}; padding-left: 10px;"
    STYLES["notes_list_style"] = f"QListWidget {{ border: 1px solid {palette['notes_list_border']}; border-radius: 6px; padding: 5px; background-color: {palette['notes_list_bg']}; color: {palette['text_primary']}; }} QListWidget::item {{ padding: 8px; margin: 2px 0; border-radius: 4px; color: {palette['text_primary']}; }} QListWidget::item:selected {{ background-color: {palette['notes_list_item_selected_bg']}; color: {palette['notes_list_item_selected_text']}; }} QListWidget::item:hover {{ background-color: {palette['menu_hover']}; }}"
    
    # Uniform button styles - works in both light and dark mode
    STYLES["button_style"] = (f"QPushButton {{ "
        f"background-color: {palette.get('button_bg', '#0d6efd')}; "
        f"color: {palette.get('button_text', '#ffffff')}; "
        f"border: 2px solid {palette.get('button_border', '#0d6efd')}; "
        f"border-radius: 6px; "
        f"padding: 8px 16px; "
        f"font-size: 13px; "
        f"font-weight: 500; "
        f"min-width: 80px; "
        f"}} "
        f"QPushButton:hover {{ "
        f"background-color: {palette.get('button_bg_hover', '#0b5ed7')}; "
        f"border-color: {palette.get('button_border_hover', '#0a58ca')}; "
        f"}} "
        f"QPushButton:pressed {{ "
        f"background-color: {palette.get('button_bg_pressed', '#0a58ca')}; "
        f"}} "
        f"QPushButton:disabled {{ "
        f"background-color: {palette.get('button_bg_disabled', '#6c757d')}; "
        f"border-color: {palette.get('button_border_disabled', '#6c757d')}; "
        f"color: {palette.get('button_text_disabled', '#ffffff')}; "
        f"}}")
    
    # Success button - green styling (Ekle)
    STYLES["success_button_style"] = (f"QPushButton {{ "
        f"background-color: {palette.get('button_success_bg', '#198754')}; "
        f"color: {palette.get('button_success_text', '#ffffff')}; "
        f"border: 2px solid {palette.get('button_success_border', '#198754')}; "
        f"border-radius: 6px; "
        f"padding: 8px 16px; "
        f"font-size: 13px; "
        f"font-weight: 500; "
        f"min-width: 80px; "
        f"}} "
        f"QPushButton:hover {{ "
        f"background-color: {palette.get('button_success_bg_hover', '#157347')}; "
        f"border-color: {palette.get('button_success_border_hover', '#146c43')}; "
        f"}} "
        f"QPushButton:pressed {{ "
        f"background-color: {palette.get('button_success_bg_pressed', '#146c43')}; "
        f"}}")
    
    # Warning button - yellow styling (Güncelle)
    STYLES["warning_button_style"] = (f"QPushButton {{ "
        f"background-color: {palette.get('button_warning_bg', '#ffc107')}; "
        f"color: {palette.get('button_warning_text', '#000000')}; "
        f"border: 2px solid {palette.get('button_warning_border', '#ffc107')}; "
        f"border-radius: 6px; "
        f"padding: 8px 16px; "
        f"font-size: 13px; "
        f"font-weight: 500; "
        f"min-width: 80px; "
        f"}} "
        f"QPushButton:hover {{ "
        f"background-color: {palette.get('button_warning_bg_hover', '#e0a800')}; "
        f"border-color: {palette.get('button_warning_border_hover', '#d39e00')}; "
        f"}} "
        f"QPushButton:pressed {{ "
        f"background-color: {palette.get('button_warning_bg_pressed', '#d39e00')}; "
        f"}}")
    
    # Delete button - red styling
    STYLES["delete_button_style"] = (f"QPushButton {{ "
        f"background-color: {palette.get('button_danger_bg', '#dc3545')}; "
        f"color: {palette.get('button_danger_text', '#ffffff')}; "
        f"border: 2px solid {palette.get('button_danger_border', '#dc3545')}; "
        f"border-radius: 6px; "
        f"padding: 8px 16px; "
        f"font-size: 13px; "
        f"font-weight: 500; "
        f"min-width: 80px; "
        f"}} "
        f"QPushButton:hover {{ "
        f"background-color: {palette.get('button_danger_bg_hover', '#c82333')}; "
        f"border-color: {palette.get('button_danger_border_hover', '#bd2130')}; "
        f"}} "
        f"QPushButton:pressed {{ "
        f"background-color: {palette.get('button_danger_bg_pressed', '#bd2130')}; "
        f"}}")

    STYLES["notes_date_label_style"] = f"font-size: 16px; font-weight: 600; color: {palette['text_primary']}; margin-bottom: 5px;"
    STYLES["notes_section_title_style"] = f"font-size: 14px; font-weight: 600; color: {palette['text_secondary']}; margin-top: 10px; margin-bottom: 5px;"
    STYLES["donut_label_style"] = f"font-size: 12px; color: {palette.get('text_secondary', '#505050')}; font-weight: 500;"

    STYLES["notes_drawing_frame"] = f"QFrame {{ background-color: {palette['notes_drawing_bg']}; border: 2px solid {palette['notes_drawing_border']}; border-radius: 8px; }}"
    STYLES["notes_drawing_label_bg"] = f"background-color: {palette['notes_drawing_label_bg']}; color: {palette['notes_drawing_text_color']}; font-weight: bold; padding: 5px; border-radius: 5px;"
    STYLES["notes_list_item_drawing_style"] = f"QListWidget {{ border: none; background-color: transparent; }} QListWidget::item {{ padding: 8px 5px; color: {palette['notes_drawing_text_color']}; background-color: transparent; border-bottom: 1px dashed {palette['notes_drawing_border']}; }} QListWidget::item:selected {{ background-color: {palette['notes_drawing_border']}; color: {palette['notes_list_item_selected_text']}; }}"
    STYLES["notes_buttons_drawing_style"] = "QPushButton { padding: 6px 10px; border-radius: 4px; font-size: 12px; } QPushButton#new_button_notes { background-color: #6c757d; color: white; } QPushButton#delete_button_notes { background-color: #dc3545; color: white; } QPushButton#save_button_notes { background-color: #28a745; color: white; }"
    
    STYLES["kdv_checkbox_style"] = "QCheckBox { font-weight: 600; padding: 5px; } QCheckBox:checked { color: #28a745; }"
    STYLES["preview_button_style"] = "QPushButton { padding: 8px 12px; background-color: #6c757d; color: white; border-radius: 6px; font-weight: 600; font-size: 12px; } QPushButton:hover { background-color: #5a6268; }"


def show_styled_message_box(parent, icon, title, text, buttons):
    """ Temaya uygun (sabit açık tema) QMessageBox gösterir ve buton metinlerini Türkçeleştirir. """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    msg_box.setIcon(icon)
    
    # Buton metinlerini Türkçeleştir
    for button in msg_box.buttons():
        button_role = msg_box.buttonRole(button)
        if button_role == QMessageBox.ButtonRole.AcceptRole:
            if buttons & QMessageBox.StandardButton.Ok:
                button.setText("Tamam")
            elif buttons & QMessageBox.StandardButton.Yes:
                button.setText("Evet")
        elif button_role == QMessageBox.ButtonRole.RejectRole:
            if buttons & QMessageBox.StandardButton.No:
                button.setText("Hayır")
            elif buttons & QMessageBox.StandardButton.Cancel:
                button.setText("İptal")
        elif button_role == QMessageBox.ButtonRole.ApplyRole:
            button.setText("Uygula")
        elif button_role == QMessageBox.ButtonRole.ResetRole:
            button.setText("Sıfırla")
    
    palette = LIGHT_THEME_PALETTE
    bg_color = palette.get('main_card_frame', '#ffffff')
    text_color = palette.get('text_primary', '#0b2d4d')
    input_border = palette.get('input_border', '#D0D0D0')
    menu_checked = palette.get('menu_checked', '#e0e0e0')
    btn_bg = "#f0f0f0"
    btn_text = "#333333"
    btn_border = input_border
    
    msg_box.setStyleSheet(
        f"QMessageBox {{ "
        f"    background-color: {bg_color}; "
        f"    font-size: 15px; "
        f"    font-weight: 500; "
        f"    color: {text_color};"
        f"}} "
        f"QMessageBox QLabel {{ "
        f"    color: {text_color}; "
        f"    font-size: 15px; "
        f"    font-weight: 500; "
        f"    padding: 15px; "
        f"    margin: 10px;"
        f"}} "
        f"QMessageBox QPushButton {{ "
        f"    padding: 12px 24px; "
        f"    border: 1px solid {btn_border}; "
        f"    border-radius: 8px; "
        f"    background-color: {btn_bg}; "
        f"    color: {btn_text}; "
        f"    min-width: 120px; "
        f"    font-size: 15px; "
        f"    font-weight: 500; "
        f"    margin: 5px;"
        f"}} "
        f"QMessageBox QPushButton:hover {{ "
        f"    background-color: #3498db; "
        f"    color: white; "
        f"    border-color: #2980b9;"
        f"}} "
        f"QMessageBox QPushButton:pressed {{ "
        f"    background-color: #2980b9; "
        f"    color: white;"
        f"}}"
    )
    return msg_box.exec()


def get_save_file_name_turkish(parent, title, default_name, file_filter):
    """
    Türkçeleştirilmiş dosya kaydetme dialogu.
    """
    dialog = QFileDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setNameFilter(file_filter)
    dialog.selectFile(default_name)
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Kaydet")
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, "İptal")
    dialog.setLabelText(QFileDialog.DialogLabel.FileName, "Dosya Adı")
    dialog.setLabelText(QFileDialog.DialogLabel.FileType, "Dosya Türü")
    
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        selected_files = dialog.selectedFiles()
        return selected_files[0] if selected_files else None, file_filter
    return None, None

# --- Donut Grafik Widget ---
class DonutChartWidget(QWidget):
    def __init__(self, value=0, max_value=100, color=QColor("#007bff"), text="", parent=None):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value if max_value > 0 else 100
        self.color = QColor(color) if isinstance(color, str) else color
        self.label_text = text
        self.display_text = ""
        self.setMinimumSize(120, 120)
        self.setMaximumSize(200, 200)

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
        font_size_multiplier = 0.12

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
        self.current_page = 0
        self.page_size = 100  
        self.total_count = 0
        self.sort_order = "tarih DESC"  # Varsayılan sıralama: Yakın tarihten uzak tarihe
        
        self._setup_ui()
        self._connect_signals()
        self.refresh_table()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addLayout(self._create_header_layout())
        main_layout.addLayout(self._create_form_layout())
        main_layout.addWidget(self._create_table())
        main_layout.addLayout(self._create_pagination_layout())

    def _create_header_layout(self):
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.config[self.invoice_type]["title"])
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Tarihe göre sıralama dropdown'ı
        sort_label = QLabel("Sıralama:")
        header_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Yakın tarihten uzak tarihe", "tarih DESC")
        self.sort_combo.addItem("Uzak tarihten yakın tarihe", "tarih ASC")
        self.sort_combo.addItem("Girilen sıra (ID)", "id ASC")
        self.sort_combo.setCurrentIndex(0)  # Varsayılan: yakın tarihten uzak tarihe
        self.sort_combo.setToolTip("Faturaları tarihe göre nasıl sıralayacağınızı seçin")
        self.sort_combo.setMinimumWidth(200)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header_layout.addWidget(self.sort_combo)
        
        self.delete_selected_button = QPushButton("🗑️ Seçilenleri Sil")
        self.delete_selected_button.setToolTip("Seçili faturaları sil")
        self.delete_selected_button.clicked.connect(self.delete_selected_invoices)
        self.delete_selected_button.setEnabled(False)
        header_layout.addWidget(self.delete_selected_button)
        
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
            key = header.replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ç", "C").replace("Ö", "O").replace(" ", "_").replace("%", "yuzdesi").lower()
            if key == "birim":
                widget = QComboBox()
                widget.addItems(["TL", "USD", "EUR"])
            else:
                widget = QLineEdit()
                placeholders = {"TARİH": "gg.aa.yyyy", "KDV %": "Örn: 20", "TOPLAM TUTAR": "ZORUNLU - Tutar girin"}
                widget.setPlaceholderText(placeholders.get(header, header))
                if key in ["miktar", "toplam_tutar", "kdv_yuzdesi"]:
                    validator = QDoubleValidator()
                    validator.setLocale(tr_locale)
                    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                    widget.setValidator(validator)
            
            # Tooltip'leri ekle
            tooltips = {
                "İRSALİYE NO": "İrsaliye/Fatura numarası\nBoş bırakılabilir",
                "TARİH": "Fatura tarihi\nBoş bırakılırsa bugünün tarihi kullanılır\nFormat: gg.aa.yyyy",
                "FİRMA": "Firma/müşteri adı\nBoş bırakılabilir",
                "MALZEME": "Ürün/hizmet açıklaması\nBoş bırakılabilir",
                "MİKTAR": "Miktar bilgisi\nBoş bırakılabilir",
                "TOPLAM TUTAR": "ZORUNLU ALAN\nToplam tutar mutlaka girilmelidir\nVirgül veya nokta kullanabilirsiniz",
                "BİRİM": "Para birimi seçimi",
                "KDV %": "KDV yüzdesi\nBoş bırakılırsa varsayılan %20 kullanılır"
            }
            widget.setToolTip(tooltips.get(header, header))
            
            self.edit_fields[key] = widget
            fields_layout.addWidget(widget)
        
        form_layout.addLayout(fields_layout)
        
        # KDV kontrol alanı kaldırıldı - sistem otomatik KDV dahil çalışıyor
        
        form_layout.addLayout(self._create_button_layout())
        return form_layout

    def _create_button_layout(self):
        button_layout = QHBoxLayout()
        self.new_button = QPushButton("🔄 Yeni / Temizle")
        self.add_button = QPushButton("➕ Ekle")
        self.update_button = QPushButton("📝 Güncelle")
        self.delete_button = QPushButton("🗑️ Sil")
        
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        return button_layout

    def _create_table(self):
        self.invoice_table = QTableWidget(); self.invoice_table.setColumnCount(10)
        table_headers = ["İRSALİYE NO", "TARİH", "FİRMA", "MALZEME", "MİKTAR", "TUTAR (TL)", "TUTAR (USD)*", "TUTAR (EUR)*", "KDV %", "KDV TUTARI"]
        self.invoice_table.setHorizontalHeaderLabels(table_headers); self.invoice_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.invoice_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        # --- İSTEĞİNİZ ÜZERİNE DEĞİŞİKLİK ---
        # Sütunları içeriğe göre değil, PENCEREYE GÖRE ESNETECEK şekilde ayarla
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.invoice_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); self.invoice_table.verticalHeader().setVisible(False)
        
        # Tooltip ekle USD/EUR sütunları için
        self.invoice_table.horizontalHeaderItem(6).setToolTip("* Fatura giriş tarihindeki kurla hesaplanmış değer (Historik Kur)")
        self.invoice_table.horizontalHeaderItem(7).setToolTip("* Fatura giriş tarihindeki kurla hesaplanmış değer (Historik Kur)")
        
        return self.invoice_table
    
    def _create_pagination_layout(self):
        """Sayfalama butonları"""
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        
        self.prev_button = QPushButton("◀ Önceki")
        self.prev_button.clicked.connect(self.previous_page)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel("Sayfa 1 / 1")
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("Sonraki ▶")
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        
        pagination_layout.addStretch()
        return pagination_layout
    
    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_table()
    
    def next_page(self):
        max_page = (self.total_count - 1) // self.page_size
        if self.current_page < max_page:
            self.current_page += 1
            self.refresh_table()
    
    def update_pagination_controls(self):
        """Sayfalama kontrollerini güncelle"""
        max_page = max(0, (self.total_count - 1) // self.page_size)
        self.page_label.setText(f"Sayfa {self.current_page + 1} / {max_page + 1} (Toplam: {self.total_count:,} fatura)")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < max_page)

    def _connect_signals(self):
        self.new_button.clicked.connect(self.clear_edit_fields)
        self.add_button.clicked.connect(lambda: self._handle_invoice_operation('add'))
        self.update_button.clicked.connect(lambda: self._handle_invoice_operation('update'))
        self.delete_button.clicked.connect(lambda: self._handle_invoice_operation('delete'))
        self.invoice_table.itemSelectionChanged.connect(self.on_row_selected)
        self.invoice_table.itemSelectionChanged.connect(self.update_delete_button_state)
        self.export_button.clicked.connect(self.export_table_data)
        if self.backend and hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'):
            self.backend.data_updated.connect(self.refresh_table)

    def _on_sort_changed(self):
        """Sıralama seçimi değiştiğinde çağrılır."""
        selected_sort = self.sort_combo.currentData()
        if selected_sort:
            self.sort_order = selected_sort
            self.current_page = 0  # İlk sayfaya dön
            self.refresh_table()

    def gather_data_from_fields(self):
        """Form alanlarından veri toplar ve backend'in beklediği formata dönüştürür."""
        data = {}
        numeric_keys_map = {"miktar": "miktar", "toplam_tutar": "toplam_tutar", "kdv_yuzdesi": "kdv_yuzdesi"}
        
        for key, field in self.edit_fields.items():
            if isinstance(field, QComboBox): 
                data[key] = field.currentText()
            else:
                text_value = field.text()
                if key in numeric_keys_map:
                    backend_key = numeric_keys_map[key]
                    data[backend_key] = text_value.replace('.', '').replace(',', '.')
                else: 
                    data[key] = text_value
        
        # KDV dahil sistemi - otomatik olarak true
        data['kdv_dahil'] = True  # Sistem artık hep KDV dahil çalışıyor
        data['kdv_tutari'] = 0  # KDV tutarı backend'de hesaplanır
        
        return data

    # KDV önizleme fonksiyonu kaldırıldı - sistem artık KDV dahil çalışıyor

    def _handle_invoice_operation(self, operation):
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        if operation in ['update', 'delete'] and not self.current_invoice_id: show_styled_message_box(self, QMessageBox.Icon.Warning, "İşlem Başarısız","Lütfen önce bir fatura seçin.", QMessageBox.StandardButton.Ok); return
        if operation == 'delete':
            reply = show_styled_message_box(self, QMessageBox.Icon.Question, "Silme Onayı", "Bu faturayı silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return
        
        data = self.gather_data_from_fields() if operation != 'delete' else None
        success = self.backend.handle_invoice_operation(operation, self.invoice_type, data=data, record_id=self.current_invoice_id)
        
        if success: 
            self.clear_edit_fields()
        else: 
            show_styled_message_box(self, QMessageBox.Icon.Warning, "İşlem Başarısız", "Veri kaydedilemedi. Lütfen en az toplam tutar alanını doldurduğunuzdan emin olun.", QMessageBox.StandardButton.Ok)

    def refresh_table(self):
        self.invoice_table.setRowCount(0)
        if not self.backend: return
        
        offset = self.current_page * self.page_size
        invoices = self.backend.handle_invoice_operation('get', self.invoice_type, limit=self.page_size, offset=offset, order_by=self.sort_order)
        if invoices is None: invoices = []
        
        self.total_count = self.backend.handle_invoice_operation('count', self.invoice_type) or 0
        self.update_pagination_controls()
        
        self.invoice_table.setSortingEnabled(False) 
        for inv in invoices:
            row_pos = self.invoice_table.rowCount()
            self.invoice_table.insertRow(row_pos)
            
            item_id = QTableWidgetItem()
            item_id.setData(Qt.ItemDataRole.UserRole, inv.get('id'))
            self.invoice_table.setVerticalHeaderItem(row_pos, item_id)

            # Historik kurları kullan (eğer mevcutsa)
            usd_amount = inv.get('toplam_tutar_usd', 0)
            eur_amount = inv.get('toplam_tutar_eur', 0)
            
            # Eğer historik kur yoksa (eski faturalar için), hesapla
            if usd_amount == 0 and inv.get('toplam_tutar_tl', 0) > 0:
                usd_amount = self.backend.convert_currency(inv.get('toplam_tutar_tl', 0), 'TRY', 'USD')
            if eur_amount == 0 and inv.get('toplam_tutar_tl', 0) > 0:
                eur_amount = self.backend.convert_currency(inv.get('toplam_tutar_tl', 0), 'TRY', 'EUR')

            data_to_display = [
                inv.get('irsaliye_no', ''), 
                inv.get('tarih', ''), 
                inv.get('firma', ''), 
                inv.get('malzeme', ''), 
                str(inv.get('miktar', '')), 
                f"{inv.get('toplam_tutar_tl', 0):,.2f}", 
                f"{usd_amount:,.2f}", 
                f"{eur_amount:,.2f}", 
                f"{inv.get('kdv_yuzdesi', 0):.0f}%", 
                f"{inv.get('kdv_tutari', 0):,.2f}"
            ]
            for col_idx, data in enumerate(data_to_display):
                item = QTableWidgetItem(str(data))
                if col_idx >= 5: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.invoice_table.setItem(row_pos, col_idx, item)

        self.invoice_table.setSortingEnabled(True)

    def on_row_selected(self):
        selected_rows = list(set(item.row() for item in self.invoice_table.selectedItems()))
        if not selected_rows: return
        
        selected_row = selected_rows[0]
        id_item = self.invoice_table.verticalHeaderItem(selected_row)
        if not id_item or not self.backend: return
        
        try: 
            self.current_invoice_id = id_item.data(Qt.ItemDataRole.UserRole)
            if self.current_invoice_id is None: return
        except (ValueError, TypeError): 
            print(f"Hata: Geçersiz fatura ID'si - {id_item.text() if id_item else 'None'}")
            return

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
            kdv_tutari_tl = float(invoice_data.get('kdv_tutari', 0))
            kdv_dahil = invoice_data.get('kdv_dahil', 0)
            
            # Historik kurları kullan (eğer mevcutsa)
            usd_kur = invoice_data.get('usd_kur', 0)
            eur_kur = invoice_data.get('eur_kur', 0)
            
            original_total_amount_tl = matrah_tl
            if kdv_dahil and kdv_yuzdesi and float(kdv_yuzdesi) > 0:
                original_total_amount_tl = matrah_tl * (1 + float(kdv_yuzdesi) / 100)
            
            # Orijinal para birimindeki tutarı hesapla
            if birim == 'TL':
                original_amount_in_currency = original_total_amount_tl
                kdv_tutari_in_currency = kdv_tutari_tl
            elif birim == 'USD' and usd_kur > 0:
                # Historik kuru kullan
                original_amount_in_currency = original_total_amount_tl / usd_kur
                kdv_tutari_in_currency = kdv_tutari_tl / usd_kur
            elif birim == 'EUR' and eur_kur > 0:
                # Historik kuru kullan
                original_amount_in_currency = original_total_amount_tl / eur_kur
                kdv_tutari_in_currency = kdv_tutari_tl / eur_kur
            else:
                # Fallback: Güncel kurları kullan (eski faturalar için)
                original_amount_in_currency = self.backend.convert_currency(original_total_amount_tl, 'TRY', birim)
                kdv_tutari_in_currency = self.backend.convert_currency(kdv_tutari_tl, 'TRY', birim)
            
            locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
            formatted_amount = locale.toString(original_amount_in_currency, 'f', 2)
            formatted_kdv = locale.toString(kdv_tutari_in_currency, 'f', 2)
            
            self.edit_fields["toplam_tutar"].setText(formatted_amount)
            
            birim_index = self.edit_fields["birim"].findText(birim)
            self.edit_fields["birim"].setCurrentIndex(birim_index if birim_index != -1 else 0)
            # KDV dahil checkbox kaldırıldı - sistem otomatik KDV dahil çalışıyor

    def clear_edit_fields(self):
        self.invoice_table.clearSelection()
        for key, field in self.edit_fields.items():
            if isinstance(field, QComboBox): field.setCurrentIndex(0)
            else: field.clear()
        # KDV dahil checkbox ve KDV tutarı field kaldırıldı
        self.current_invoice_id = None

    def export_table_data(self):
        config = self.config[self.invoice_type]
        file_path, _ = get_save_file_name_turkish(self, f"{config['title']} Listesini Kaydet", config['file_name'], "Excel Dosyaları (*.xlsx)")
        if not file_path: return
        if not self.backend: show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok); return
        invoices_data = self.backend.handle_invoice_operation('get', self.invoice_type);
        if not invoices_data: show_styled_message_box(self, QMessageBox.Icon.Warning, "Veri Yok", f"Dışa aktarılacak {self.invoice_type} faturası bulunamadı.", QMessageBox.StandardButton.Ok); return;
        
        export_data = []
        for inv in invoices_data:
            # Historik kurları kullan
            usd_amount = inv.get('toplam_tutar_usd', 0)
            eur_amount = inv.get('toplam_tutar_eur', 0)
            
            # Eğer historik kur yoksa (eski faturalar için), hesapla
            if usd_amount == 0 and inv.get('toplam_tutar_tl', 0) > 0:
                usd_amount = self.backend.convert_currency(inv.get('toplam_tutar_tl', 0), 'TRY', 'USD')
            if eur_amount == 0 and inv.get('toplam_tutar_tl', 0) > 0:
                eur_amount = self.backend.convert_currency(inv.get('toplam_tutar_tl', 0), 'TRY', 'EUR')
            
            export_data.append({
                "İrsaliye No": inv.get('irsaliye_no'),
                "Tarih": inv.get('tarih'),
                "Firma": inv.get('firma'),
                "Malzeme": inv.get('malzeme'),
                "Miktar": inv.get('miktar'),
                "Birim": inv.get('birim'),
                "Tutar (TL)": inv.get('toplam_tutar_tl'),
                "Tutar (USD - Historik)": usd_amount,
                "Tutar (EUR - Historik)": eur_amount,
                "KDV (%)": inv.get('kdv_yuzdesi'),
                "KDV Tutarı (TL)": inv.get('kdv_tutari'),
                "KDV Dahil mi": "Evet" if inv.get('kdv_dahil') else "Hayır",
                "USD Kuru (Giriş)": inv.get('usd_kur', 0),
                "EUR Kuru (Giriş)": inv.get('eur_kur', 0),
                "Kayıt Tarihi": inv.get('kayit_tarihi', '')
            })

        sheets_data = {config["title"]: {"data": export_data}}; 
        if self.backend.export_to_excel(file_path, sheets_data):
            show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{config['title']} başarıyla dışa aktarıldı:\n{file_path}", QMessageBox.StandardButton.Ok)
        else:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Dışa Aktarma Hatası", "Excel dosyası oluşturulurken bir hata oluştu.", QMessageBox.StandardButton.Ok)


    def update_delete_button_state(self):
        """Seçili satır sayısına göre çoklu silme butonunu aktif/pasif yapar."""
        selected_rows = self.invoice_table.selectionModel().selectedRows()
        self.delete_selected_button.setEnabled(len(selected_rows) > 0)

    def delete_selected_invoices(self):
        """Seçili faturaları siler."""
        selected_items = self.invoice_table.selectionModel().selectedRows()
        if not selected_items:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Seçim Yok", "Lütfen silmek istediğiniz faturaları seçin.", QMessageBox.StandardButton.Ok)
            return

        count = len(selected_items)
        reply = show_styled_message_box(self, QMessageBox.Icon.Question, "Silme Onayı", 
                                        f"{count} faturayı silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!", 
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        invoice_ids = []
        for index in selected_items:
            id_item = self.invoice_table.verticalHeaderItem(index.row())
            if id_item and id_item.data(Qt.ItemDataRole.UserRole) is not None:
                invoice_ids.append(id_item.data(Qt.ItemDataRole.UserRole))

        if not invoice_ids:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Seçili faturaların ID'leri alınamadı.", QMessageBox.StandardButton.Ok)
            return

        try:
            deleted_count = self.backend.delete_multiple_invoices(self.invoice_type, invoice_ids)
            
            if deleted_count > 0:
                show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{deleted_count} fatura başarıyla silindi.", QMessageBox.StandardButton.Ok)
            else:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Faturalar silinemedi veya hiç fatura seçilmedi.", QMessageBox.StandardButton.Ok)
        except Exception as e:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "Kritik Hata", f"Silme işlemi sırasında beklenmedik bir hata oluştu: {str(e)}", QMessageBox.StandardButton.Ok)


    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"])
        self.export_button.setStyleSheet(STYLES["export_button"])
        self.invoice_table.setStyleSheet(STYLES["table_style"])
        
        # ComboBox için temel stil
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
        self.sort_combo.setStyleSheet(f"padding: 8px; border: 1px solid {palette.get('input_border', '#D0D0D0')}; border-radius: 6px; font-size: 13px; color: {palette.get('text_primary', '#0b2d4d')}; background-color: {palette.get('card_frame', '#FFFFFF')};")
        
        # Renkli buton stilleri
        self.new_button.setStyleSheet(STYLES.get("button_style", ""))  # Gri
        self.add_button.setStyleSheet(STYLES.get("success_button_style", ""))  # Yeşil
        self.update_button.setStyleSheet(STYLES.get("warning_button_style", ""))  # Mavi
        self.delete_button.setStyleSheet(STYLES.get("delete_button_style", ""))  # Kırmızı
        self.delete_selected_button.setStyleSheet("padding: 5px; background-color: #dc3545; color: white; border-radius: 5px;")
        for field in self.edit_fields.values(): field.setStyleSheet(STYLES["input_style"])

# --- Genel Giderler Sekmesi ---
class GenelGiderTab(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.current_gider_id = None
        self.current_page = 0
        self.page_size = 100
        self.setup_ui()
        self.refresh_table()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        # Header layout
        header_layout = QHBoxLayout()
        title_label = QLabel("💼 Genel Giderler")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Form layout - kutucuklu tasarım
        form_layout = QVBoxLayout()
        
        # Input fields - horizontal layout
        fields_layout = QHBoxLayout()
        tr_locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
        
        # Miktar field
        self.miktar_input = QLineEdit()
        self.miktar_input.setPlaceholderText("💰 ZORUNLU - Miktar girin")
        self.miktar_input.setToolTip("Genel gider tutarı (zorunlu)\nVirgül veya nokta kullanabilirsiniz")
        self.miktar_input.setStyleSheet(STYLES.get("input_style", ""))
        miktar_validator = QDoubleValidator()
        miktar_validator.setLocale(tr_locale)
        miktar_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.miktar_input.setValidator(miktar_validator)
        fields_layout.addWidget(self.miktar_input)
        
        # Tür field
        self.tur_input = QLineEdit()
        self.tur_input.setPlaceholderText("🏷️ Tür (Opsiyonel)")
        self.tur_input.setToolTip("Gider türü (opsiyonel)\nÖrn: Ofis kira, elektrik, yakıt, temizlik...")
        self.tur_input.setStyleSheet(STYLES.get("input_style", ""))
        fields_layout.addWidget(self.tur_input)
        
        # Tarih field
        self.tarih_input = QLineEdit()
        self.tarih_input.setText(datetime.now().strftime('%d.%m.%Y'))
        self.tarih_input.setPlaceholderText("📅 gg.aa.yyyy")
        self.tarih_input.setToolTip("Gider tarihi\nFormat: gg.aa.yyyy\nBoş bırakılırsa bugünün tarihi kullanılır")
        self.tarih_input.setStyleSheet(STYLES.get("input_style", ""))
        fields_layout.addWidget(self.tarih_input)
        
        form_layout.addLayout(fields_layout)
        
        # Buttons layout - InvoiceTab stilinde
        button_layout = QHBoxLayout()
        self.new_button = QPushButton("🔄 Yeni / Temizle")
        self.add_button = QPushButton("➕ Ekle")
        self.update_button = QPushButton("📝 Güncelle")
        self.delete_button = QPushButton("🗑️ Sil")
        
        # Button styling with specific colors
        self.new_button.setStyleSheet(STYLES.get("button_style", ""))
        self.add_button.setStyleSheet(STYLES.get("success_button_style", ""))  # Yeşil
        self.update_button.setStyleSheet(STYLES.get("warning_button_style", ""))  # Sarı
        self.delete_button.setStyleSheet(STYLES.get("delete_button_style", ""))  # Kırmızı
        
        # Connect signals
        self.new_button.clicked.connect(self.clear_fields)
        self.add_button.clicked.connect(lambda: self._handle_operation('add'))
        self.update_button.clicked.connect(lambda: self._handle_operation('update'))
        self.delete_button.clicked.connect(lambda: self._handle_operation('delete'))
        
        # Add buttons to layout - same order as InvoiceTab
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        form_layout.addLayout(button_layout)
        main_layout.addLayout(form_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Miktar (TL)", "Tür", "Tarih"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(STYLES.get("table_style", ""))
        
        # Connect table signals
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        main_layout.addWidget(self.table)
    
    def _handle_operation(self, operation):
        if not self.backend:
            QMessageBox.warning(self, "Hata", "Backend yüklenemedi.")
            return
        
        if operation in ['update', 'delete'] and not self.current_gider_id:
            QMessageBox.warning(self, "Seçim Gerekli", "Lütfen önce bir kayıt seçin.")
            return
        
        if operation == 'delete':
            reply = QMessageBox.question(self, "Silme Onayı", 
                                       "Bu genel gider kaydını silmek istediğinizden emin misiniz?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        data = self.gather_data() if operation != 'delete' else None
        success = self.backend.handle_genel_gider_operation(operation, data=data, record_id=self.current_gider_id)
        
        if success:
            self.clear_fields()
            self.refresh_table()
            QMessageBox.information(self, "Başarılı", f"İşlem başarıyla tamamlandı.")
        else:
            QMessageBox.warning(self, "Hata", "İşlem başarısız. Lütfen bilgileri kontrol edin.")
    
    def gather_data(self):
        miktar_text = self.miktar_input.text().strip().replace(',', '.')
        
        if not miktar_text:
            QMessageBox.warning(self, "Eksik Bilgi", "Miktar alanı zorunludur.")
            return None
        
        try:
            miktar = float(miktar_text)
            if miktar <= 0:
                QMessageBox.warning(self, "Geçersiz Miktar", "Miktar pozitif olmalıdır.")
                return None
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Miktar", "Lütfen geçerli bir sayı girin.")
            return None
        
        # Tarihi backend formatına çevir (YYYY-MM-DD)
        tarih_text = self.tarih_input.text().strip()
        try:
            if '.' in tarih_text:
                day, month, year = tarih_text.split('.')
                tarih = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                tarih = tarih_text
        except:
            tarih = datetime.now().strftime('%Y-%m-%d')
        
        return {
            'miktar': miktar,
            'tur': self.tur_input.text().strip(),
            'tarih': tarih
        }
    
    def refresh_table(self):
        if not self.backend:
            return
        
        giderler = self.backend.handle_genel_gider_operation('get', limit=self.page_size, offset=self.current_page * self.page_size)
        
        if giderler is None:
            giderler = []
        
        self.table.setRowCount(len(giderler))
        
        for row, gider in enumerate(giderler):
            # Tarihi DD.MM.YYYY formatına çevir
            tarih = gider.get('tarih', '')
            if '-' in tarih:
                try:
                    year, month, day = tarih.split('-')
                    tarih_formatted = f"{day}.{month}.{year}"
                except:
                    tarih_formatted = tarih
            else:
                tarih_formatted = tarih
            
            self.table.setItem(row, 0, QTableWidgetItem(str(gider.get('id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(f"{gider.get('miktar', 0):.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(gider.get('tur', '')))
            self.table.setItem(row, 3, QTableWidgetItem(tarih_formatted))
    
    def on_selection_changed(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            id_item = self.table.item(current_row, 0)
            miktar_item = self.table.item(current_row, 1)
            tur_item = self.table.item(current_row, 2)
            tarih_item = self.table.item(current_row, 3)
            
            if id_item:
                self.current_gider_id = int(id_item.text())
                self.miktar_input.setText(miktar_item.text() if miktar_item else "")
                self.tur_input.setText(tur_item.text() if tur_item else "")
                self.tarih_input.setText(tarih_item.text() if tarih_item else "")
    
    def clear_fields(self):
        self.table.clearSelection()
        self.miktar_input.clear()
        self.tur_input.clear()
        self.tarih_input.setText(datetime.now().strftime('%d.%m.%Y'))
        self.current_gider_id = None

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

        calendar_title = QLabel("takvim")
        calendar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.calendar_title_label = calendar_title 
        main_layout.addWidget(calendar_title)

        self.calendar = QCalendarWidget()
        self.calendar.setLocale(self.locale)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setGridVisible(True)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader) 

        calendar_frame = QFrame()
        self.calendar_frame = calendar_frame 
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(5, 5, 5, 5)
        calendar_layout.addWidget(self.calendar)
        main_layout.addWidget(calendar_frame)

        notes_title = QLabel("notlar başlığı")
        notes_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_title_label = notes_title 
        main_layout.addWidget(notes_title)

        notes_content_frame = QFrame()
        self.notes_content_frame = notes_content_frame 
        notes_content_layout = QVBoxLayout(notes_content_frame)
        notes_content_layout.setContentsMargins(5, 5, 5, 5)

        self.notes_list = QListWidget()
        self.notes_list.setAlternatingRowColors(False) 
        self.notes_list.setMaximumHeight(150) 
        notes_content_layout.addWidget(self.notes_list)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Not başlığı...")
        notes_content_layout.addWidget(self.title_input)
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Not içeriği...")
        self.content_input.setFixedHeight(60) 
        notes_content_layout.addWidget(self.content_input)

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
        self.calendar_frame.setStyleSheet(STYLES.get("notes_drawing_frame", ""))
        self.notes_content_frame.setStyleSheet(STYLES.get("notes_drawing_frame", ""))
        self.calendar_title_label.setStyleSheet(STYLES.get("notes_drawing_label_bg", ""))
        self.notes_title_label.setStyleSheet(STYLES.get("notes_drawing_label_bg", ""))

        calendar_widget_style = f"""
            QCalendarWidget {{ background-color: transparent; border: none; }}
            QCalendarWidget QToolButton {{ color: {palette['notes_drawing_text_color']}; background-color: transparent; border: none; border-radius: 4px; font-size: 13px; padding: 4px 6px; margin: 1px; }}
            QCalendarWidget QToolButton:hover {{ background-color: rgba(255, 255, 255, 0.2); }}
            QWidget#qt_calendar_navigationbar {{ background-color: transparent; border-bottom: 1px solid {palette['notes_drawing_border']}; }}
            QCalendarWidget QAbstractItemView:enabled {{ font-size: 11px; color: {palette['notes_drawing_text_color']}; background-color: transparent; selection-background-color: {palette['notes_drawing_border']}; selection-color: {palette['notes_list_item_selected_text']}; }}
            QCalendarWidget QTableView {{ gridline-color: {palette['notes_drawing_border']}; }}
            QCalendarWidget QTableView::item {{ color: {palette['notes_drawing_text_color']}; border-radius: 0px; }}
            QCalendarWidget QTableView::item:selected {{ background-color: {palette['notes_drawing_border']}; color: {palette['notes_list_item_selected_text']}; font-weight: bold; }}
        """
        self.calendar.setStyleSheet(calendar_widget_style)

        self.title_input.setStyleSheet(STYLES.get("input_style", "").replace(palette['card_frame'], 'transparent')) 
        self.content_input.setStyleSheet(STYLES.get("input_style", "").replace(palette['card_frame'], 'transparent')) 
        self.notes_list.setStyleSheet(STYLES.get("notes_list_item_drawing_style", ""))

        self.new_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.delete_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", ""))
        self.new_button.setObjectName("new_button_notes") 
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
            self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", "").replace("#28a745", "#007bff")) 
            self.save_button.setObjectName("save_button_notes")
        else: self.clear_selection_and_inputs()

    def clear_selection_and_inputs(self):
        self.notes_list.clearSelection(); self.title_input.clear(); self.content_input.clear(); self.current_note_id = None; self.save_button.setText("Kaydet");
        self.save_button.setStyleSheet(STYLES.get("notes_buttons_drawing_style", "")) 
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
        note_format.setBackground(QBrush(QColor(palette.get("notes_drawing_border", "#FF9999")))) 
        note_format.setForeground(QBrush(QColor(palette.get("notes_list_item_selected_text", "#FFFFFF"))))
        for date_str in dates_with_notes:
            try:
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if date.isValid(): self.calendar.setDateTextFormat(date, note_format); self.marked_dates.add(date)
            except Exception as e: print(f"Takvim işareti hatası: {date_str}, {e}")

    def restyle(self): self.apply_styles()


# --- HomePage ---
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
        
        self.notes_widget = NotesWidget()
        bottom_layout.addWidget(self.notes_widget, 2)

        card_layout.addLayout(bottom_layout)
        
        page_layout = QHBoxLayout(self); page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addStretch(); page_layout.addWidget(self.main_content_card); page_layout.addStretch()

    def _create_header(self):
        header_layout = QHBoxLayout(); self.title_label = QLabel(self.CONFIG["page_title"]); header_layout.addWidget(self.title_label); header_layout.addStretch(); self.exchange_rate_label = QLabel(); self.update_exchange_rate_display(); header_layout.addWidget(self.exchange_rate_label); header_layout.addSpacing(15); header_layout.addWidget(self._create_currency_selector())
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
        
    def _create_financial_graph_widget(self): 
        if pg:
            plot_widget = pg.PlotWidget(); months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]; ticks = [(i, month) for i, month in enumerate(months)]; plot_widget.getAxis('bottom').setTicks([ticks]); self.legend = plot_widget.addLegend(offset=(10, 10)); self.income_line = pg.PlotDataItem(pen=pg.mkPen(color=(40, 167, 69), width=2.5), symbol='o', symbolBrush=(40, 167, 69), symbolSize=7, name='Gelir'); self.expenses_line = pg.PlotDataItem(pen=pg.mkPen(color=(220, 53, 69), width=2.5), symbol='o', symbolBrush=(220, 53, 69), symbolSize=7, name='Gider'); plot_widget.addItem(self.income_line); plot_widget.addItem(self.expenses_line); return plot_widget
        else:
            return QLabel("Grafik kütüphanesi (pyqtgraph) yüklenemedi.") # Kütüphane yoksa
    
    def _connect_signals(self): 
        self.currency_group.buttonClicked.connect(self.update_currency)
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
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE); self.main_content_card.setStyleSheet(STYLES.get("main_card_frame")); self.title_label.setStyleSheet(STYLES.get("title")); self.currency_selector_frame.setStyleSheet("background-color: #f0f5fa; border-radius: 8px; padding: 3px;");
        for btn in self.currency_group.buttons(): btn.setStyleSheet("QPushButton { background-color: transparent; border: none; padding: 6px 18px; color: #505050; font-weight: 500; border-radius: 6px; font-size: 13px; } QPushButton:checked { background-color: #ffffff; color: #0066CC; font-weight: 600; }")
        
        if hasattr(self, 'donut_profit_label'):
            self.donut_profit_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_avg_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_income_label.setStyleSheet(STYLES.get("donut_label_style"))
            self.donut_expense_label.setStyleSheet(STYLES.get("donut_label_style"))
                    
        self.load_donuts()
        
        self.graph_title_label.setStyleSheet(STYLES.get("info_panel_title"))
        self.graph_year_dropdown.setStyleSheet(STYLES.get("input_style"))
        
        if pg and isinstance(self.plot_widget, pg.PlotWidget):
            graph_bg = STYLES.get("palette", {}).get("graph_background", 'w'); graph_fg = STYLES.get("palette", {}).get("graph_foreground", '#404040')
            pg.setConfigOption('background', graph_bg); pg.setConfigOption('foreground', graph_fg); self.plot_widget.setBackground(graph_bg); self.plot_widget.getAxis('left').setTextPen(graph_fg); self.plot_widget.getAxis('bottom').setTextPen(graph_fg); self.plot_widget.showGrid(x=True, y=True, alpha=0.2);
            if hasattr(self, 'legend'): self.legend.setLabelTextColor(graph_fg)
        
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
        if not pg or not isinstance(self.plot_widget, pg.PlotWidget): return
        if not self.backend: self.income_line.setData([], []); self.expenses_line.setData([], []); return
        converter = getattr(self.backend, 'convert_currency', lambda v, f, t: v); income = [converter(v, 'TRY', self.current_currency) for v in self.monthly_data.get('income', [0]*12)]; expenses = [converter(v, 'TRY', self.current_currency) for v in self.monthly_data.get('expenses', [0]*12)]; months_indices = list(range(12)); self.income_line.setData(x=months_indices, y=income); self.expenses_line.setData(x=months_indices, y=expenses); graph_fg = '#404040'; self.plot_widget.setLabel('left', f"Tutar ({self.current_currency})", color=graph_fg); self.plot_widget.autoRange()
        
# --- Fatura Sayfası ---
class InvoicesPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self._setup_ui()
        self.restyle()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Fatura Yönetimi")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.qr_button = QPushButton("📷 Otomatik Fatura Ekle (QR)")
        self.qr_button.setToolTip("Bir klasördeki tüm faturaları QR kodlarını okuyarak otomatik olarak sisteme ekler.")
        self.qr_button.clicked.connect(self.start_qr_processing_flow)
        header_layout.addWidget(self.qr_button)
        
        main_layout.addLayout(header_layout)
        
        self.tab_widget = QTabWidget()
        self.outgoing_tab = InvoiceTab("outgoing", self.backend)
        self.incoming_tab = InvoiceTab("incoming", self.backend)
        self.genel_gider_tab = GenelGiderTab(self.backend)
        self.tab_widget.addTab(self.outgoing_tab, "Giden Faturalar (Gelir)")
        self.tab_widget.addTab(self.incoming_tab, "Gelen Faturalar (Gider)")
        self.tab_widget.addTab(self.genel_gider_tab, "Genel Giderler")
        main_layout.addWidget(self.tab_widget)

    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"])
        
        qr_button_style = """
            QPushButton {
                background-color: #007bff; color: white; border: none;
                border-radius: 6px; font-size: 12px; font-weight: bold;
                padding: 8px 12px; margin: 2px;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:pressed { background-color: #004085; }
        """
        self.qr_button.setStyleSheet(qr_button_style)
        
        palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
        tab_style = f"""
            QTabWidget::pane {{ 
                border: 1px solid {palette.get('card_border', '#E0E0E0')}; 
                background-color: {palette.get('card_background', '#FFFFFF')};
            }}
            QTabBar::tab {{ 
                background-color: {palette.get('tab_background', '#F8F9FA')};
                border: 1px solid {palette.get('card_border', '#E0E0E0')};
                padding: 10px 15px;
                margin-right: 2px;
                font-size: 14px;
                font-weight: bold;
                color: {palette.get('text_color', '#2C3E50')};
                min-width: 180px;
            }}
            QTabBar::tab:selected {{ 
                background-color: {palette.get('primary', '#3498DB')};
                color: white;
                border-bottom: none;
            }}
            QTabBar::tab:hover {{
                background-color: {palette.get('secondary', '#95A5A6')};
                color: white;
            }}
        """
        self.tab_widget.setStyleSheet(tab_style)
        self.outgoing_tab.restyle()
        self.incoming_tab.restyle()

    def refresh_data(self):
        self.outgoing_tab.refresh_table()
        self.incoming_tab.refresh_table()

    def start_qr_processing_flow(self):
        """GELİŞTİRİLMİŞ QR sistemi - QR'dan fatura ekleme akışını yönetir."""
        if not self.backend:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "Hata", "Backend modülü bulunamadı.", QMessageBox.StandardButton.Ok)
            return

        # QR modülünü test et
        try:
            logging.info("🔧 QR modülü test ediliyor...")
            
            # Backend'deki QR processor'ü kullan
            self.backend.qr_processor._init_qr_tools()
            logging.info("✅ QR modülü hazır.")
            
        except ImportError as e:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "QR Kütüphaneleri Eksik", 
                                  f"❌ QR okuma kütüphaneleri eksik:\n{e}\n\n"
                                  f"🔧 Gerekli kütüphaneler:\n"
                                  f"• PyMuPDF (PDF okuma)\n"
                                  f"• opencv-python-headless (görüntü işleme)\n"
                                  f"• pyzbar (QR kod okuma)\n\n"
                                  f"💻 Kurulum komutu:\n"
                                  f"pip install PyMuPDF opencv-python-headless pyzbar", 
                                  QMessageBox.StandardButton.Ok)
            return
        except Exception as e:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "QR Sistemi Hatası", 
                                  f"❌ QR okuma sistemi başlatılamadı:\n{e}\n\n"
                                  f"🔧 Olası çözümler:\n"
                                  f"1. Kütüphaneleri yeniden kurun\n"
                                  f"2. Python sürümünü kontrol edin\n"
                                  f"3. Sistem yeniden başlatın", 
                                  QMessageBox.StandardButton.Ok)
            return

        # Klasör seçimi
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("📁 QR Kodlu Fatura Dosyalarının Klasörünü Seçin")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        file_dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Seç")
        file_dialog.setLabelText(QFileDialog.DialogLabel.Reject, "İptal")
        
        if file_dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        
        folder_path = file_dialog.selectedFiles()[0] if file_dialog.selectedFiles() else None
        if not folder_path:
            return

        # Klasörde dosya sayısı kontrolü
        try:
            import os
            files = [f for f in os.listdir(folder_path) 
                    if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.bmp'))]
            if not files:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Dosya Bulunamadı", 
                                      f"📂 Seçilen klasörde işlenebilir dosya bulunamadı.\n\n"
                                      f"Desteklenen formatlar: PDF, JPG, PNG, BMP", 
                                      QMessageBox.StandardButton.Ok)
                return
                
            if len(files) > 50:
                reply = show_styled_message_box(self, QMessageBox.Icon.Question, "Çok Fazla Dosya", 
                                              f"⚠️ {len(files)} dosya bulundu. İşlem uzun sürebilir.\n\n"
                                              f"Devam etmek istiyor musunuz?", 
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
                    
            logging.info(f"📁 Klasörde {len(files)} dosya bulundu")
            
        except Exception as e:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Klasör Okuma Hatası", 
                                  f"❌ Klasör okunamadı: {e}", QMessageBox.StandardButton.Ok)
            return

        # İlerleme çubuğu
        progress = QProgressDialog("🔍 QR kodlar okunuyor...", "İptal", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButtonText("İptal")
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        QApplication.processEvents()

        try:
            # Fatura türü seçimi için pop-up
            invoice_type_dialog = InvoiceTypeDialog(self)
            if invoice_type_dialog.exec() != invoice_type_dialog.DialogCode.Accepted:
                progress.close()
                return
            
            selected_type = invoice_type_dialog.get_selected_type()
            logging.info(f"📋 Seçilen fatura türü: {selected_type}")
            
            # QR işleme - backend metodunu kullan
            def status_update(message, progress_val=None):
                if progress.wasCanceled():
                    return False
                progress.setLabelText(f"🔍 {message}")
                if progress_val is not None:
                    progress.setValue(min(progress_val, 99))
                QApplication.processEvents()
                return True

            qr_results = self.backend.process_qr_files_in_folder(folder_path, max_workers=6, status_callback=status_update)
            
        except Exception as e:
            logging.error(f"❌ QR işleme hatası: {e}")
            progress.close()
            show_styled_message_box(self, QMessageBox.Icon.Critical, "QR İşleme Hatası", 
                                  f"❌ QR kodları işlenirken hata oluştu:\n{e}", 
                                  QMessageBox.StandardButton.Ok)
            return

        progress.close()

        if qr_results is None:
            show_styled_message_box(self, QMessageBox.Icon.Critical, "İşlem Hatası", 
                                  "❌ QR kodları işlenirken kritik hata oluştu.", 
                                  QMessageBox.StandardButton.Ok)
            return
        
        # Sonuçları analiz et
        successful_qrs = [r for r in qr_results if r.get('durum') == 'BAŞARILI']
        json_errors = [r for r in qr_results if r.get('durum') == 'JSON HATASI']
        qr_not_found = [r for r in qr_results if r.get('durum') == 'QR BULUNAMADI']
        
        total_files = len(qr_results)
        success_count = len(successful_qrs)

        logging.info(f"📊 QR İşlem Sonuçları - Toplam: {total_files}, Başarılı: {success_count}, JSON Hatası: {len(json_errors)}, QR Yok: {len(qr_not_found)}")

        if success_count == 0:
            error_details = []
            if json_errors:
                error_details.append(f"📝 JSON hatası: {len(json_errors)} dosya")
            if qr_not_found:
                error_details.append(f"🔍 QR bulunamadı: {len(qr_not_found)} dosya")
                
            show_styled_message_box(self, QMessageBox.Icon.Warning, "QR Bulunamadı", 
                                  f"❌ {total_files} dosyadan hiç birinde geçerli QR kod bulunamadı.\n\n"
                                  f"📋 Detaylar:\n" + "\n".join(error_details) +
                                  f"\n\n💡 İpuçları:\n"
                                  f"• PDF dosyaların kaliteli olduğundan emin olun\n"
                                  f"• QR kodun net görünür olduğunu kontrol edin\n"
                                  f"• E-fatura PDF'lerini kullanın", 
                                  QMessageBox.StandardButton.Ok)
            return

        # Başarılı QR'lar varsa veritabanına ekle
        if success_count > 0:
            progress = QProgressDialog("💾 Faturalar veritabanına ekleniyor...", "İptal", 0, success_count, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()

            try:
                # Seçilen fatura türünü kullan
                result = self.backend.add_invoices_from_qr_data(qr_results, selected_type)
                
                progress.close()
                
                if result and result.get('success'):
                    added = result.get('added', 0)
                    failed = result.get('failed', 0)
                    
                    message = f"✅ QR işleme tamamlandı!\n\n"
                    message += f"📊 Sonuçlar:\n"
                    message += f"• Başarılı fatura eklendi: {added}\n"
                    message += f"• Başarısız: {failed}\n"
                    message += f"• Toplam işlenen: {total_files}\n\n"
                    
                    if result.get('processing_details'):
                        message += f"📋 Detaylar:\n"
                        for detail in result['processing_details'][:5]:  # İlk 5 detayı göster
                            status_icon = "✅" if detail.get('status') == 'BAŞARILI' else "❌"
                            message += f"{status_icon} {detail.get('file', 'Bilinmeyen')}: {detail.get('status', 'Durum bilinmiyor')}\n"
                        
                        if len(result['processing_details']) > 5:
                            message += f"... ve {len(result['processing_details']) - 5} dosya daha\n"
                    
                    message += f"\n💡 Faturalar '{selected_type}' kategorisine eklendi."
                    
                    show_styled_message_box(self, QMessageBox.Icon.Information, "QR İşleme Başarılı", message, QMessageBox.StandardButton.Ok)
                    
                    # Tabloları yenile
                    self.refresh_data()
                    
                else:
                    error_msg = result.get('message', 'Bilinmeyen hata') if result else 'Sonuç alınamadı'
                    show_styled_message_box(self, QMessageBox.Icon.Warning, "Fatura Ekleme Hatası", 
                                          f"❌ Faturalar veritabanına eklenemedi:\n{error_msg}", 
                                          QMessageBox.StandardButton.Ok)
                    
            except Exception as e:
                progress.close()
                logging.error(f"❌ Veritabanına ekleme hatası: {e}")
                show_styled_message_box(self, QMessageBox.Icon.Critical, "Veritabanı Hatası", 
                                      f"❌ Faturalar veritabanına eklenirken hata oluştu:\n{e}", 
                                      QMessageBox.StandardButton.Ok)
                return
        
        else:
            # Hata durumu - başarılı QR yok
            show_styled_message_box(self, QMessageBox.Icon.Warning, "QR İşlemi Tamamlanamadı", 
                                  f"❌ QR kodlardan fatura eklenemedi.", 
                                  QMessageBox.StandardButton.Ok)
            return

    def show_export_progress(self, title, export_func, *args):
        """Export işlemi için progress göster."""
        progress = QProgressDialog(title, "İptal", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        try:
            result = export_func(*args)
            progress.close()
            return result
        except Exception as e:
            progress.close()
            raise e
        if result.get('failed', 0) > 0:
            details.append(f"❌ Başarısız: {result.get('failed', 0)}")
        details.append(f"📊 Toplam işlenen QR: {success_count}")
        details.append(f"📂 Tarafanan dosya: {total_files}")

        show_styled_message_box(self, icon, title,
                                f"🎉 Otomatik fatura ekleme tamamlandı!\n\n" + 
                                "\n".join(details) +
                                f"\n\n💾 Veriler güncellendi.",
                                QMessageBox.StandardButton.Ok)

    def _process_qr_files_with_processor(self, qr_processor, folder_path):
        """QR processor kullanarak dosyaları işler."""
        import os
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        file_paths = []
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.pdf'}
        
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path) and os.path.splitext(file_name)[1].lower() in allowed_extensions:
                    file_paths.append(file_path)
        except Exception as e:
            logging.error(f"Klasör okunurken hata: {e}")
            return None
        
        if not file_paths:
            return []
        
        # Dinamik worker sayısı
        cpu_count = 4  # varsayılan değer
        try:
            import psutil
            cpu_count = psutil.cpu_count() or 4
        except (ImportError, AttributeError):
            # psutil yoksa veya çalışmıyorsa os modülünü dene
            try:
                import os
                cpu_count = os.cpu_count() or 4
            except AttributeError:
                cpu_count = 4  # çok eski Python versiyonları için varsayılan
        
        max_workers = min(cpu_count, max(2, len(file_paths) // 2), 8)
        
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(qr_processor.process_file, path): path for path in file_paths}
            
            for i, future in enumerate(as_completed(future_to_path), 1):
                try:
                    result = future.result(timeout=45)
                    results.append(result)
                except Exception as e:
                    file_path = future_to_path[future]
                    logging.error(f"QR işleme hatası '{os.path.basename(file_path)}': {e}")
                    results.append({'dosya_adi': os.path.basename(file_path), 'durum': 'HATA', 'json_data': {}})
        
        return results

    def _add_qr_invoices_to_backend(self, qr_results, invoice_type):
        """QR sonuçlarını backend'e fatura olarak ekler."""
        import time
        
        if not qr_results:
            return 0, 0

        successful_imports = 0
        failed_imports = 0
        
        for result in qr_results:
            if result.get('durum') == 'BAŞARILI':
                json_data = result.get('json_data', {})
                parsed_data = self._parse_qr_to_invoice_fields(json_data)
                
                if self.backend.handle_invoice_operation('add', invoice_type, data=parsed_data):
                    successful_imports += 1
                else:
                    failed_imports += 1
            else:
                failed_imports += 1
        
        return successful_imports, failed_imports

    def _parse_qr_to_invoice_fields(self, qr_json):
        """QR JSON verisini fatura alanlarına dönüştürür."""
        import time
        
        if not qr_json:
            return {}

        key_map = {
            'irsaliye_no': ['invoiceId', 'faturaNo', 'belgeno', 'uuid', 'id', 'no'],
            'tarih': ['invoiceDate', 'faturaTarihi', 'tarih', 'date'],
            'firma': ['sellerName', 'saticiUnvan', 'firma', 'supplier', 'company'],
            'malzeme': ['tip', 'type', 'itemName', 'description', 'malzeme'],
            'miktar': ['quantity', 'miktar', 'adet', 'qty'],
            'toplam_tutar': ['payableAmount', 'totalAmount', 'toplamTutar', 'total'],
            'kdv_yuzdesi': ['taxRate', 'kdvOrani', 'vatRate'],
        }

        def get_value(keys):
            for key in keys:
                if key in qr_json and qr_json[key]:
                    return qr_json[key]
            qr_json_lower = {k.lower(): v for k, v in qr_json.items()}
            for key in keys:
                if key.lower() in qr_json_lower:
                    return qr_json_lower[key.lower()]
            return None

        parsed = {}
        parsed['irsaliye_no'] = str(get_value(key_map['irsaliye_no']) or f"QR-{int(time.time())}")
        parsed['tarih'] = str(get_value(key_map['tarih']) or datetime.now().strftime("%d.%m.%Y"))
        parsed['firma'] = str(get_value(key_map['firma']) or 'QR Fatura Firma')
        parsed['malzeme'] = str(get_value(key_map['malzeme']) or 'QR Kodlu E-Fatura')
        parsed['miktar'] = str(get_value(key_map['miktar']) or '1')
        parsed['toplam_tutar'] = float(get_value(key_map['toplam_tutar']) or 0)
        parsed['kdv_yuzdesi'] = float(get_value(key_map['kdv_yuzdesi']) or 20)
        parsed['birim'] = 'TL'

        return parsed
        

# --- Dönemsel/Yıllık Gelir Sayfası ---
class MonthlyIncomePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self._setup_ui()
        self._connect_signals()
        self.populate_years_dropdown()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10,10,10,10)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Dönemsel ve Yıllık Gelir")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.tax_label = QLabel("Kurumlar Vergisi (%):")
        self.tax_input = QLineEdit()
        self.tax_input.setValidator(QDoubleValidator(0, 100, 2))
        self.tax_input.setMaximumWidth(60)
        self.tax_input.setText(f"{getattr(self.backend, 'settings', {}).get('kurumlar_vergisi_yuzdesi', 22.0):.1f}")
        self.tax_save_btn = QPushButton("Kaydet")
        self.tax_save_btn.setStyleSheet("background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px;")
        self.tax_save_btn.setFixedWidth(60)
        header_layout.addWidget(self.tax_label)
        header_layout.addWidget(self.tax_input)
        header_layout.addWidget(self.tax_save_btn)
        header_layout.addSpacing(20)
        self.year_dropdown = QComboBox()
        self.year_dropdown.setPlaceholderText("Yıl Seçin")
        self.year_dropdown.setMinimumWidth(100)
        header_layout.addWidget(QLabel("Yıl:"))
        header_layout.addWidget(self.year_dropdown)
        self.export_button = QPushButton("Excel'e Aktar")
        header_layout.addWidget(self.export_button)
        main_layout.addLayout(header_layout)
        
        tables_layout = QHBoxLayout()
        self.income_table = QTableWidget(14, 5)
        self.income_table.setHorizontalHeaderLabels(["AYLAR", "GELİR (Kesilen)", "GİDER (Gelen)", "KDV FARKI", "ÖDENECEK VERGİ"])
        months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
        self.colors = {"mavi": "#D4EBF2", "pembe": "#F9E7EF", "sarı": "#FFF2D6", "yeşil": "#D9F2E7"}
        for row, month_name in enumerate(months):
            month_item = QTableWidgetItem(month_name)
            month_item.setFlags(month_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.income_table.setItem(row, 0, month_item)
        total_item = QTableWidgetItem("GENEL TOPLAM")
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.income_table.setItem(12, 0, total_item)
        kar_zarar_item = QTableWidgetItem("YILLIK NET KÂR")
        kar_zarar_item.setFlags(kar_zarar_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.income_table.setItem(13, 0, kar_zarar_item)
        self.income_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.income_table.verticalHeader().setVisible(False)
        # --- İSTEĞİNİZ ÜZERİNE DEĞİŞİKLİK ---
        # Tablonun dikeyde tüm alanı kaplamasını sağla
        self.income_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tables_layout.addWidget(self.income_table)
        main_layout.addLayout(tables_layout)
        main_layout.setStretchFactor(tables_layout, 1)

    def _connect_signals(self):
        self.year_dropdown.currentTextChanged.connect(self.refresh_data)
        self.export_button.clicked.connect(self.export_table_data)
        self.tax_save_btn.clicked.connect(self.save_tax_percentage)
        if self.backend and hasattr(self.backend, 'data_updated') and hasattr(self.backend.data_updated, 'connect'):
            self.backend.data_updated.connect(self.refresh_data)

    def save_tax_percentage(self):
        if not self.backend:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için ayar kaydedilemiyor.", QMessageBox.StandardButton.Ok)
            return
        try:
            tax_percent = float(self.tax_input.text().replace(',', '.'))
            if 0 <= tax_percent <= 100:
                self.backend.save_setting('kurumlar_vergisi_yuzdesi', tax_percent)
                # Ayar kaydedildikten sonra tabloyu yenile
                self.refresh_data()
                show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", 
                                        f"Kurumlar vergisi oranı %{tax_percent:.1f} olarak güncellendi.\nTablo verileri yenilendi.", 
                                        QMessageBox.StandardButton.Ok)
            else:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Vergi oranı 0-100 arasında olmalıdır.", QMessageBox.StandardButton.Ok)
        except ValueError:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", "Geçerli bir sayı giriniz.", QMessageBox.StandardButton.Ok)

    def restyle(self):
        self.title_label.setStyleSheet(STYLES["page_title"])
        self.export_button.setStyleSheet(STYLES["export_button"])
        self.income_table.setStyleSheet(STYLES["table_style"])
        self.tax_input.setStyleSheet(STYLES["input_style"])
        self.year_dropdown.setStyleSheet(STYLES["input_style"])
        for row in range(12):
            month_item = self.income_table.item(row, 0)
            if month_item:
                color_key = "mavi" if row < 3 else "pembe" if row < 6 else "sarı" if row < 9 else "yeşil"
                month_item.setBackground(QBrush(QColor(self.colors[color_key])))
        try:
            palette = STYLES.get("palette", LIGHT_THEME_PALETTE)
            total_bg_color = QColor(palette.get("table_header", "#F0F0F0"))
            total_font = QFont()
            total_font.setBold(True)
            for col in range(5):
                item12 = self.income_table.item(12, col)
                if not item12:
                    item12 = QTableWidgetItem()
                    self.income_table.setItem(12, col, item12)
                item12.setBackground(total_bg_color)
                item12.setFont(total_font)
                item12.setFlags(item12.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0 or col == 4:
                    item13 = self.income_table.item(13, col)
                    if not item13:
                        item13 = QTableWidgetItem()
                        self.income_table.setItem(13, col, item13)
                    item13.setBackground(total_bg_color)
                    item13.setFont(total_font)
                    item13.setFlags(item13.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.income_table.setSpan(13, 0, 1, 4)
            kar_item_label = self.income_table.item(13, 0)
            if kar_item_label:
                kar_item_label.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        except Exception as e:
            print(f"Toplam satırlarını stillerken hata: {e}")

    def populate_years_dropdown(self):
        years = [str(datetime.now().year)]
        if self.backend:
            years = self.backend.get_year_range()
        current_selection = self.year_dropdown.currentText()
        self.year_dropdown.blockSignals(True)
        self.year_dropdown.clear()
        self.year_dropdown.addItems(years if years else [])
        index = self.year_dropdown.findText(current_selection) if current_selection in years else (0 if years else -1)
        self.year_dropdown.setCurrentIndex(index)
        self.year_dropdown.blockSignals(False)
        self.refresh_data()

    def refresh_data(self):
        if self.backend:
            self.tax_input.setText(f"{getattr(self.backend, 'settings', {}).get('kurumlar_vergisi_yuzdesi', 22.0):.1f}")
        year_str = self.year_dropdown.currentText()
        for i in range(14):
            for j in range(1, 5):
                self.income_table.setItem(i, j, QTableWidgetItem(""))
        if not year_str or not self.backend:
            return
        try:
            year = int(year_str)
            monthly_results, quarterly_results = self.backend.get_calculations_for_year(year)
            summary = self.backend.get_yearly_summary(year)
            total_kdv_farki = 0.0
            total_odenen_vergi = 0.0
            for i, data in enumerate(monthly_results):
                kdv_farki = data.get('kdv', 0)
                total_kdv_farki += kdv_farki
                self.income_table.setItem(i, 1, QTableWidgetItem(f"{data.get('kesilen', 0):,.2f} TL"))
                self.income_table.setItem(i, 2, QTableWidgetItem(f"{data.get('gelen', 0):,.2f} TL"))
                self.income_table.setItem(i, 3, QTableWidgetItem(f"{kdv_farki:,.2f} TL"))
            quarter_indices = {0: 2, 1: 5, 2: 8, 3: 11}
            for q, data in enumerate(quarterly_results):
                odenecek_kv = data.get('odenecek_kv', 0)
                total_odenen_vergi += odenecek_kv
                if q in quarter_indices:
                    row_index = quarter_indices[q]
                    self.income_table.setItem(row_index, 4, QTableWidgetItem(f"{odenecek_kv:,.2f} TL"))
            self.income_table.setItem(12, 1, QTableWidgetItem(f"{summary.get('toplam_gelir', 0):,.2f} TL"))
            self.income_table.setItem(12, 2, QTableWidgetItem(f"{summary.get('toplam_gider', 0):,.2f} TL"))
            self.income_table.setItem(12, 3, QTableWidgetItem(f"{total_kdv_farki:,.2f} TL"))
            self.income_table.setItem(12, 4, QTableWidgetItem(f"{total_odenen_vergi:,.2f} TL"))
            self.income_table.setItem(13, 4, QTableWidgetItem(f"{summary.get('yillik_kar', 0):,.2f} TL"))
            for r in range(14):
                for c in range(1, 5):
                    item = self.income_table.item(r, c)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.restyle()
        except ValueError:
            print(f"Hata: Geçersiz yıl formatı - {year_str}")
        except Exception as e:
            print(f"Veri yenileme hatası (MonthlyIncomePage): {e}")

    def export_table_data(self):
        year_str = self.year_dropdown.currentText()
        if not year_str:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Yıl Seçilmedi", "Lütfen dışa aktarmak için bir yıl seçin.", QMessageBox.StandardButton.Ok)
            return
        if not self.backend:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Backend Hatası", "Backend modülü yüklenemediği için işlem yapılamıyor.", QMessageBox.StandardButton.Ok)
            return
        file_path, _ = get_save_file_name_turkish(self, f"{year_str} Yılı Raporunu Kaydet", f"{year_str}_gelir_gider_raporu.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path:
            return
        try:
            year = int(year_str)
            monthly_results, quarterly_results = self.backend.get_calculations_for_year(year)
            summary = self.backend.get_yearly_summary(year)
            months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            data_to_export = []
            total_kdv_farki_export = 0.0
            total_vergi_export = 0.0
            quarter_indices_map = {2: 0, 5: 1, 8: 2, 11: 3}
            for i, month_name in enumerate(months):
                monthly_data = monthly_results[i]
                kdv_farki = monthly_data.get('kdv', 0)
                total_kdv_farki_export += kdv_farki
                odenecek_vergi = 0.0
                if i in quarter_indices_map:
                    q_index = quarter_indices_map[i]
                    if q_index < len(quarterly_results):
                        odenecek_vergi = quarterly_results[q_index].get('odenecek_kv', 0)
                        total_vergi_export += odenecek_vergi
                row_data = {
                    "AYLAR": month_name,
                    "GELİR (Kesilen)": monthly_data.get('kesilen', 0),
                    "GİDER (Gelen)": monthly_data.get('gelen', 0),
                    "KDV FARKI": kdv_farki,
                    "ÖDENECEK VERGİ": odenecek_vergi
                }
                data_to_export.append(row_data)
            data_to_export.append({})
            data_to_export.append({
                "AYLAR": "GENEL TOPLAM",
                "GELİR (Kesilen)": summary.get('toplam_gelir', 0),
                "GİDER (Gelen)": summary.get('toplam_gider', 0),
                "KDV FARKI": total_kdv_farki_export,
                "ÖDENECEK VERGİ": total_vergi_export
            })
            data_to_export.append({
                "AYLAR": "YILLIK NET KÂR",
                "GELİR (Kesilen)": None,
                "GİDER (Gelen)": None,
                "KDV FARKI": None,
                "ÖDENECEK VERGİ": summary.get('yillik_kar', 0)
            })
            sheets_data = {f"{year_str} Raporu": {"data": data_to_export}}
            if self.backend.export_to_excel(file_path, sheets_data):
                show_styled_message_box(self, QMessageBox.Icon.Information, "Başarılı", f"{year_str} yılı raporu başarıyla dışa aktarıldı:\n{file_path}", QMessageBox.StandardButton.Ok)
            else:
                show_styled_message_box(self, QMessageBox.Icon.Warning, "Dışa Aktarma Hatası", "Excel dosyası oluşturulurken bir hata oluştu.", QMessageBox.StandardButton.Ok)
        except ValueError:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Hata", f"Geçersiz yıl formatı: {year_str}", QMessageBox.StandardButton.Ok)
        except Exception as e:
            show_styled_message_box(self, QMessageBox.Icon.Warning, "Dışa Aktarma Hatası", f"Excel'e aktarma sırasında bir hata oluştu: {e}", QMessageBox.StandardButton.Ok)


# --- Ana Pencere ---
from PyQt6.QtWidgets import QDialog, QRadioButton

class InvoiceTypeDialog(QDialog):
    """Fatura türü seçimi için dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_type = 'outgoing'  # Varsayılan
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("📋 Fatura Türü Seçimi")
        self.setFixedSize(480, 320)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel("QR kodlardan okunan faturalar hangi kategoriye eklensin?")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #0b2d4d;
                margin: 15px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 12px;
                border: 1px solid #e5eaf0;
            }
        """)
        layout.addWidget(title_label)
        
        # Seçenekler
        self.outgoing_radio = QRadioButton("💰 GELİR (Outgoing) - Müşteriye kesilen faturalar")
        self.outgoing_radio.setChecked(True)
        self.outgoing_radio.setStyleSheet("""
            QRadioButton {
                font-size: 15px;
                font-weight: 500;
                padding: 15px;
                margin: 10px;
                color: #0b2d4d;
                background-color: #e8f5e8;
                border-radius: 8px;
                border: 1px solid #d1e7dd;
            }
            QRadioButton::indicator {
                width: 24px;
                height: 24px;
                margin-right: 10px;
            }
        """)
        
        self.incoming_radio = QRadioButton("📋 GİDER (Incoming) - Tedarikçiden gelen faturalar")
        self.incoming_radio.setStyleSheet("""
            QRadioButton {
                font-size: 15px;
                font-weight: 500;
                padding: 15px;
                margin: 10px;
                color: #0b2d4d;
                background-color: #fff2e8;
                border-radius: 8px;
                border: 1px solid #ffeaa7;
            }
            QRadioButton::indicator {
                width: 24px;
                height: 24px;
                margin-right: 10px;
            }
        """)
        
        layout.addWidget(self.outgoing_radio)
        layout.addWidget(self.incoming_radio)
        
        # Açıklama
        info_label = QLabel("💡 İpucu: Müşterilerinize kestiğiniz faturalar için 'GELİR', "
                           "satın aldığınız ürün/hizmet faturaları için 'GİDER' seçin.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #505050;
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 5px;
                border: 2px solid #bdc3c7;
            }
        """)
        layout.addWidget(info_label)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("✅ Devam Et")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #157347;
            }
            QPushButton:pressed {
                background-color: #146c43;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_selected_type(self):
        if self.outgoing_radio.isChecked():
            return 'outgoing'
        else:
            return 'incoming'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.backend = Backend(self)
        except Exception as e:
            print(f"KRİTİK HATA: Backend başlatılamadı: {e}")
            self.backend = None # Backend olmadan devam etmeyi dene
            
        self.setWindowTitle("Excellent MVP - Inşaat Finans Yönetimi")
        self.setGeometry(100, 100, 1600, 900)
        icon_path="favicon.ico"
        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            try:
                # PyInstaller geçici bir klasör oluşturur ve yolu _MEIPASS içine saklar
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        app_icon_path = resource_path(icon_path)

        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        else:
            # Geliştirme ortamı için (eğer paketlenmemişse) normal yoldan tekrar dene
            if os.path.exists(icon_path):
                 self.setWindowIcon(QIcon(icon_path))
            else:
                print(f"UYARI: Simge dosyası bulunamadı: {icon_path} veya {app_icon_path}")
        self.setup_fonts()
        update_styles(LIGHT_THEME_PALETTE)
        self.setup_ui()
        self.connect_signals()
        self.restyle_all()
        self.menu_buttons[0].click()
        if hasattr(self.backend, 'start_timers'):
            self.backend.start_timers()

    def setup_fonts(self):
        """Özel font yükleme - opsiyonel, yoksa sistem fontları kullanılır."""
        try:
            # Birkaç olası font konumunu dene
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Poppins-Regular.ttf'),
                os.path.join(os.path.dirname(__file__), 'fonts', 'Poppins-Regular.ttf'),
                'fonts/Poppins-Regular.ttf'
            ]
            
            for font_path in possible_paths:
                if os.path.exists(font_path):
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id != -1:
                        family = QFontDatabase.applicationFontFamilies(font_id)[0]
                        self.setFont(QFont(family, 10))
                        return
            
            self.setFont(QFont("Segoe UI", 10))
        except Exception:
            pass

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        menu_frame = QFrame()
        menu_frame.setFixedWidth(250)
        self.menu_layout = QVBoxLayout(menu_frame)
        self.menu_layout.setContentsMargins(15, 15, 15, 15)
        self.menu_layout.setSpacing(10)
        
        # --- YENİ LOGO DÜZENİ (LOGO SOLDA, YAZI SAĞDA - 60px) ---
        logo_layout = QHBoxLayout() # Düzeni QHBoxLayout (Yatay) olarak değiştirdik
        logo_layout.setSpacing(10) # Logo ile yazı arasına boşluk koyduk

        # 1. Logoyu (logo.png) sola ekliyoruz
        logo_label = QLabel()
        logo_found = False
        try:
            # Logo dosyasını ANA DİZİNDE arayacak
            possible_logo_paths = [
                os.path.join(os.path.dirname(__file__), 'logo.png'),
                'logo.png'
            ]
            
            for logo_path in possible_logo_paths:
                if os.path.exists(logo_path):
                    logo_pixmap = QPixmap(logo_path)
                    if not logo_pixmap.isNull():
                        # Logonun 60x60 piksel boyutunu KORUYORUZ
                        logo_pixmap = logo_pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        logo_label.setPixmap(logo_pixmap)
                        logo_found = True
                        break
            if not logo_found:
                logo_label.setText("[Logo Yok]") # Hata durumunda
                print("UYARI: 'logo.png' dosyası ana dizinde bulunamadı.")
                
        except Exception as e:
            print(f"Logo yükleme hatası: {e}")
            logo_label.setText("[Hata]")
        
        logo_layout.addWidget(logo_label) # Logoyu önce ekle

        # 2. Metni (Excellent MVP) sağa ekliyoruz
        self.logo_text = QLabel("Excellent MVP")
        logo_layout.addWidget(self.logo_text) 

        logo_layout.addStretch() # Öğeleri sola yaslamak için sona esneme ekle
        
        self.menu_layout.addLayout(logo_layout)
        # --- YENİ DÜZENİN SONU ---

        self.menu_layout.addSpacing(20)
        self.menu_button_group = QButtonGroup(self)
        self.menu_button_group.setExclusive(True)
        self.menu_buttons = []
        menu_items = [("🏠", "Genel Durum"), ("📄", "Faturalar"), ("📅", "Dönemsel Gelir")]
        for icon, text in menu_items:
            button = QPushButton(f"{icon}    {text}")
            button.setCheckable(True)
            self.menu_buttons.append(button)
            self.menu_layout.addWidget(button)
            self.menu_button_group.addButton(button)
        self.menu_layout.addStretch()
        main_layout.addWidget(menu_frame)
        self.menu_frame = menu_frame
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_frame)
        self.content_frame = content_frame
        self.home_page = HomePage(self.backend)
        self.invoices_page = InvoicesPage(self.backend)
        self.monthly_income_page = MonthlyIncomePage(self.backend)
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.invoices_page)
        self.stacked_widget.addWidget(self.monthly_income_page)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Durum: Hazır")
        self.status_bar.addPermanentWidget(self.status_label)

    def connect_signals(self):
        for i, button in enumerate(self.menu_buttons):
            button.clicked.connect(lambda checked, idx=i: self.on_menu_button_clicked(idx))
        if self.backend:
            self.backend.status_updated.connect(self.update_status_bar)
            self.backend.data_updated.connect(self.refresh_all_pages)

    def on_menu_button_clicked(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.refresh_all_pages()

    def refresh_all_pages(self):
        try:
            self.home_page.refresh_data()
            self.invoices_page.refresh_data()
            self.monthly_income_page.refresh_data()
        except Exception as e:
            print(f"Sayfa yenileme hatası: {e}")

    def update_status_bar(self, message, timeout=3000):
        self.status_label.setText(f"Durum: {message}")
        QTimer.singleShot(timeout, lambda: self.status_label.setText("Durum: Hazır"))

    def restyle_all(self):
        self.menu_frame.setStyleSheet(STYLES["menu_frame_style"])
        self.logo_text.setStyleSheet(STYLES["logo_text_style"])
        for button in self.menu_buttons:
            button.setStyleSheet(STYLES["menu_button_style"])
        self.content_frame.setStyleSheet(STYLES["page_background"])
        self.home_page.restyle()
        self.invoices_page.restyle()
        self.monthly_income_page.restyle()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




