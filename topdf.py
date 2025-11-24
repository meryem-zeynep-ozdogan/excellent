# -*- coding: utf-8 -*-
"""
PDF Export Module for Invoice Management System
Bu modül fatura listelerini PDF formatına dönüştürür
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class InvoicePDFExporter:
    """Fatura listelerini PDF'e dönüştüren sınıf"""
    
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._setup_custom_styles()
    
    def _register_fonts(self):
        """Türkçe karakterler için font kayıtları"""
        try:
            # Windows varsayılan fontları
            import os
            windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            
            # Arial fontunu kaydet (Türkçe karakter desteği ile)
            arial_path = os.path.join(windows_fonts, 'arial.ttf')
            if os.path.exists(arial_path):
                pdfmetrics.registerFont(TTFont('Arial-Turkish', arial_path))
                print("Arial-Turkish font kaydedildi")
            
            # Arial Bold
            arial_bold_path = os.path.join(windows_fonts, 'arialbd.ttf')
            if os.path.exists(arial_bold_path):
                pdfmetrics.registerFont(TTFont('Arial-Bold-Turkish', arial_bold_path))
                print("Arial-Bold-Turkish font kaydedildi")
            
            # Calibri alternatifi (daha modern görünüm)
            calibri_path = os.path.join(windows_fonts, 'calibri.ttf')
            if os.path.exists(calibri_path):
                pdfmetrics.registerFont(TTFont('Calibri-Turkish', calibri_path))
                print("Calibri-Turkish font kaydedildi")
                
        except Exception as e:
            print(f"Font kayıt hatası: {e}")
            print("Varsayılan fontlar kullanılacak")
    
    def _setup_custom_styles(self):
        """Özel PDF stilleri oluştur"""
        # Türkçe karakter destekli font adları - öncelik sırası
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        
        if 'Calibri-Turkish' in registered_fonts:
            turkish_font = 'Calibri-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Calibri-Turkish'
        elif 'Arial-Turkish' in registered_fonts:
            turkish_font = 'Arial-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Arial-Turkish'
        else:
            turkish_font = 'Helvetica'
            turkish_font_bold = 'Helvetica-Bold'
            print("UYARI: Türkçe font bulunamadı, Helvetica kullanılıyor")
        
        print(f"Kullanılan fontlar: {turkish_font}, {turkish_font_bold}")
        
        # Ana başlık stili - daha büyük ve belirgin
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontName=turkish_font_bold,
            fontSize=20,
            spaceAfter=25,
            spaceBefore=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d'),
            leading=24  # Satır aralığı
        ))
        
        # Alt başlık stili
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontName=turkish_font_bold,
            fontSize=16,
            spaceAfter=20,
            spaceBefore=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#2d3748'),
            leading=20
        ))
        
        # Normal paragraf stili
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontName=turkish_font,
            fontSize=11,
            spaceAfter=8,
            spaceBefore=4,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#2d3748'),
            leading=14
        ))
        
        # Özet stili
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontName=turkish_font,
            fontSize=12,
            spaceAfter=10,
            spaceBefore=5,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#2c5282'),
            leftIndent=200,
            leading=15
        ))
        
        # Normal metin stili
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontName=turkish_font,
            fontSize=10,
            spaceAfter=10,
            spaceBefore=5,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#4a5568'),
            leading=13
        ))
        
        # Footer stili
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#95a5a6')
        ))

    def export_invoices_to_pdf(self, invoice_data, invoice_type, file_path):
        """
        Fatura listesini PDF'e dönüştür - Uygulama tablo formatıyla aynı
        
        Args:
            invoice_data (list): Fatura verileri listesi
            invoice_type (str): Fatura tipi ('outgoing' veya 'incoming')
            file_path (str): PDF dosya yolu
            
        Returns:
            bool: Başarılı ise True, aksi halde False
        """
        try:
            # PDF dokümanı oluştur
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=2*cm,
                bottomMargin=1.5*cm
            )
            
            # Font kaydetme
            self._register_fonts()
            
            # Uygulama tarzında tablo düzeni oluştur
            story = self._create_invoice_document_layout(invoice_data, invoice_type)
            
            # PDF oluştur
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"PDF oluşturma hatası: {e}")
            return False

    def export_general_expenses_to_pdf(self, expense_data, file_path):
        """
        Genel gider listesini PDF'e dönüştür - Uygulama formatıyla aynı
        
        Args:
            expense_data (list): Genel gider verileri listesi
            file_path (str): PDF dosya yolu
            
        Returns:
            bool: Başarılı ise True, aksi halde False
        """
        try:
            # PDF dokümanı oluştur
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=2*cm,
                bottomMargin=1.5*cm
            )
            
            # Font kaydetme
            self._register_fonts()
            
            # Uygulama tarzında tablo düzen oluştur
            story = self._create_expense_document_layout(expense_data)
            
            # PDF oluştur
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"PDF oluşturma hatası: {e}")
            return False

    def _get_title_by_type(self, invoice_type):
        """Fatura tipine göre başlık döndür"""
        titles = {
            'outgoing': '📈 GİDEN FATURALAR (GELİR) RAPORU',
            'incoming': '📉 GELEN FATURALAR (GİDER) RAPORU'
        }
        return titles.get(invoice_type, '📊 FATURA RAPORU')

    def _create_invoice_document_layout(self, invoice_data, invoice_type):
        """Uygulama fatura tablosu ile tamamen aynı format - irsaliye no hariç"""
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        
        story = []
        
        # Türkçe karakter destekli font seçimi
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        
        if 'Calibri-Turkish' in registered_fonts:
            turkish_font = 'Calibri-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Calibri-Turkish'
        elif 'Arial-Turkish' in registered_fonts:
            turkish_font = 'Arial-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Arial-Turkish'
        else:
            turkish_font = 'Helvetica'
            turkish_font_bold = 'Helvetica-Bold'
        
        print(f"Kullanılan fontlar: {turkish_font}, {turkish_font_bold}")
        
        # Uygulama benzeri tablo başlığı
        story.append(Paragraph('<b>FATURA LISTESI</b>', 
                             ParagraphStyle('TableTitle', fontName=turkish_font_bold, fontSize=12, 
                                          alignment=1, spaceAfter=15)))
        
        # Uygulama ile TAMAMEN AYNI sütun başlıkları (irsaliye no hariç)
        headers = ["FATURA NO", "TARIH", "FIRMA", "MALZEME", "MIKTAR", "TUTAR (TL)", "TUTAR (USD)*", "TUTAR (EUR)*", "KDV TUTARI (%)"]
        
        # Veri satırları hazırla
        table_data = [headers]
        
        for invoice in invoice_data:
            # Tarihi formatla
            tarih = invoice.get('tarih', '')
            if '-' in tarih:
                try:
                    year, month, day = tarih.split('-')
                    tarih_formatted = f"{day}.{month}.{year}"
                except:
                    tarih_formatted = tarih
            else:
                tarih_formatted = tarih
            
            # KDV bilgileri
            kdv_tutari = invoice.get('kdv_tutari', 0) or 0
            kdv_yuzdesi = invoice.get('kdv_yuzdesi', 0) or 0
            toplam_tutar_tl = invoice.get('toplam_tutar_tl', 0) or 0
            
            # USD ve EUR hesaplamalı (historik kur yoksa anlık kurla hesapla)
            usd_amount = invoice.get('toplam_tutar_usd', 0) or 0
            eur_amount = invoice.get('toplam_tutar_eur', 0) or 0
            
            # Eğer historik kur yoksa basit hesaplama (42.44 USD, 48.93 EUR)
            if usd_amount == 0 and toplam_tutar_tl > 0:
                usd_amount = toplam_tutar_tl / 42.44  # Aproximate rate
            if eur_amount == 0 and toplam_tutar_tl > 0:
                eur_amount = toplam_tutar_tl / 48.93  # Aproximate rate
            
            # Uygulama ile TAMAMEN AYNI format
            row_data = [
                invoice.get('fatura_no', ''),                      # FATURA NO
                tarih_formatted,                                   # TARIH
                invoice.get('firma', ''),                          # FIRMA
                invoice.get('malzeme', ''),                        # MALZEME
                str(invoice.get('miktar', '')),                    # MIKTAR
                f"{toplam_tutar_tl:,.2f}",                        # TUTAR (TL)
                f"{usd_amount:,.2f}",                             # TUTAR (USD)*
                f"{eur_amount:,.2f}",                             # TUTAR (EUR)*
                f"{kdv_tutari:,.2f} ({kdv_yuzdesi:.0f}%)"        # KDV TUTARI (%)
            ]
            
            table_data.append(row_data)
        
        # Fatura no genişletilmiş sütun genişlikleri
        col_widths = [2.8*cm, 1.6*cm, 2.2*cm, 2.2*cm, 1.0*cm, 1.6*cm, 1.6*cm, 1.6*cm, 2.4*cm]
        
        # Ana tablo oluştur
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        main_table.setStyle(TableStyle([
            # Header stili - uygulama benzeri
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), turkish_font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            
            # Veri satırları - uygulama benzeri
            ('FONTNAME', (0, 1), (-1, -1), turkish_font),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('FONTSIZE', (0, 1), (0, -1), 6),  # Fatura no sütunu daha küçük font
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 1), (-1, -1), 3),
            ('RIGHTPADDING', (0, 1), (-1, -1), 3),
            
            # Hizalamalar - uygulama ile aynı
            ('ALIGN', (0, 1), (4, -1), 'LEFT'),      # Fatura no, tarih, firma, malzeme, miktar - sol
            ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),    # Tutar sütunları - sağ
            
            # Uygulama benzeri alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            
            # Grid lines - uygulama benzeri
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(main_table)
        story.append(Spacer(1, 20))
        
        # Özet bölümü ekle
        summary_section = self._create_table_summary(invoice_data, invoice_type, turkish_font, turkish_font_bold)
        story.extend(summary_section)
        
        return story

    def _create_table_summary(self, invoice_data, invoice_type, turkish_font, turkish_font_bold):
        """Tablo altına özet bilgileri ekle"""
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        
        summary_story = []
        
        if not invoice_data:
            return summary_story
        
        # Özet başlığı
        summary_story.append(Spacer(1, 15))
        summary_story.append(Paragraph('<b>ÖZET</b>', 
                                     ParagraphStyle('SummaryTitle', fontName=turkish_font_bold, 
                                                  fontSize=10, alignment=1, spaceAfter=10)))
        
        # Finansal özetler hesapla
        total_tl = sum(float(inv.get('toplam_tutar_tl', 0) or 0) for inv in invoice_data)
        total_kdv = sum(float(inv.get('kdv_tutari', 0) or 0) for inv in invoice_data)
        count = len(invoice_data)
        average_tl = total_tl / count if count > 0 else 0
        
        # USD ve EUR toplamları
        total_usd = 0
        total_eur = 0
        for inv in invoice_data:
            usd_amount = inv.get('toplam_tutar_usd', 0) or 0
            eur_amount = inv.get('toplam_tutar_eur', 0) or 0
            
            # Eğer USD/EUR yoksa TL'den hesapla
            if usd_amount == 0:
                tl_amount = float(inv.get('toplam_tutar_tl', 0) or 0)
                usd_amount = tl_amount / 42.44 if tl_amount > 0 else 0
            if eur_amount == 0:
                tl_amount = float(inv.get('toplam_tutar_tl', 0) or 0)
                eur_amount = tl_amount / 48.93 if tl_amount > 0 else 0
                
            total_usd += usd_amount
            total_eur += eur_amount
        
        # Özet tablosu verisi
        summary_data = [
            ['Fatura Sayisi:', f'{count} adet', 'Toplam Tutar (TL):', f'{total_tl:,.2f} TL'],
            ['Toplam USD:', f'{total_usd:,.2f} USD', 'Toplam EUR:', f'{total_eur:,.2f} EUR'],
            ['Toplam KDV:', f'{total_kdv:,.2f} TL', 'Ortalama Fatura:', f'{average_tl:,.2f} TL']
        ]
        
        # Özet tablosu oluştur
        summary_table = Table(summary_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), turkish_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),  # Etiketler sağa
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Değerler sola
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Etiketler sağa
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),   # Değerler sola
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            # Arka plan renkleri
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f8ff')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f8ff')),
            ('FONTNAME', (0, 0), (0, -1), turkish_font_bold),
            ('FONTNAME', (2, 0), (2, -1), turkish_font_bold),
            # Değer sütunları vurgu
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#e8f5e8')),  # Fatura sayısı
            ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#fff2e8')),  # Toplam TL
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0'))
        ]))
        
        summary_story.append(summary_table)
        summary_story.append(Spacer(1, 15))
        
        # Tarih bilgisi
        current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        summary_story.append(Paragraph(f'<i>Rapor Tarihi: {current_date}</i>', 
                                     ParagraphStyle('DateInfo', fontName=turkish_font, 
                                                  fontSize=7, alignment=1, 
                                                  textColor=colors.HexColor('#666666'))))
        
        return summary_story

    def _create_expense_document_layout(self, expense_data):
        """Fatura formatı gibi genel gider tablosu - uygulama benzeri"""
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        
        story = []
        
        # Türkçe karakter destekli font seçimi
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        
        if 'Calibri-Turkish' in registered_fonts:
            turkish_font = 'Calibri-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Calibri-Turkish'
        elif 'Arial-Turkish' in registered_fonts:
            turkish_font = 'Arial-Turkish'
            turkish_font_bold = 'Arial-Bold-Turkish' if 'Arial-Bold-Turkish' in registered_fonts else 'Arial-Turkish'
        else:
            turkish_font = 'Helvetica'
            turkish_font_bold = 'Helvetica-Bold'
        
        print(f"Kullanılan fontlar: {turkish_font}, {turkish_font_bold}")
        
        # Fatura benzeri tablo başlığı
        story.append(Paragraph('<b>GENEL GIDERLER LISTESI</b>', 
                             ParagraphStyle('TableTitle', fontName=turkish_font_bold, fontSize=12, 
                                          alignment=1, spaceAfter=15)))
        
        # Fatura benzeri sütun başlıkları
        headers = ["TARIH", "GIDER TURU", "MIKTAR", "BIRIM", "TUTAR"]
        
        # Veri satırları hazırla
        table_data = [headers]
        
        for expense in expense_data:
            # Tarihi formatla
            tarih = expense.get('tarih', '')
            if '-' in tarih:
                try:
                    year, month, day = tarih.split('-')
                    tarih_formatted = f"{day}.{month}.{year}"
                except:
                    tarih_formatted = tarih
            else:
                tarih_formatted = tarih
            
            # Fatura benzeri veri formatı
            gider_turu = expense.get('tur', '')
            miktar_value = float(expense.get('miktar', 0) or 0)
            
            row_data = [
                tarih_formatted,                     # TARIH
                gider_turu,                          # GIDER TURU
                "1",                                 # MIKTAR (default 1)
                "Adet",                              # BIRIM
                f"{miktar_value:,.2f} TL"            # TUTAR
            ]
            
            table_data.append(row_data)
        
        # Fatura benzeri sütun genişlikleri
        col_widths = [2.5*cm, 4*cm, 1.5*cm, 1.5*cm, 2.5*cm]
        
        # Ana tablo oluştur
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        main_table.setStyle(TableStyle([
            # Header stili - fatura benzeri
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), turkish_font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            
            # Veri satırları - fatura benzeri
            ('FONTNAME', (0, 1), (-1, -1), turkish_font),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 1), (-1, -1), 3),
            ('RIGHTPADDING', (0, 1), (-1, -1), 3),
            
            # Hizalamalar - fatura benzeri
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),      # Tarih, gider türü - sol
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),    # Miktar, birim, tutar - sağ
            
            # Fatura benzeri alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            
            # Grid lines - fatura benzeri
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(main_table)
        story.append(Spacer(1, 20))
        
        return story

    def _create_summary_section(self, invoice_data):
        """Özet bölümü oluştur"""
        # Toplamları hesapla
        total_count = len(invoice_data)
        total_amount = sum(float(inv.get('toplam_tutar_tl', 0) or 0) for inv in invoice_data)
        total_kdv = sum(float(inv.get('kdv_tutari', 0) or 0) for inv in invoice_data)
        total_matrah = total_amount - total_kdv
        
        # Para birimlerine göre dağılım
        currency_breakdown = {}
        for inv in invoice_data:
            birim = inv.get('birim', 'TL')
            amount = float(inv.get('toplam_tutar_tl', 0) or 0)
            if birim in currency_breakdown:
                currency_breakdown[birim] += amount
            else:
                currency_breakdown[birim] = amount
        
        # Özet tablosu
        summary_data = [
            ['ÖZET BİLGİLER', ''],
            ['Toplam Fatura Sayısı', f"{total_count:,}"],
            ['Toplam Matrah', f"{total_matrah:,.2f} TL"],
            ['Toplam KDV', f"{total_kdv:,.2f} TL"],
            ['Genel Toplam', f"{total_amount:,.2f} TL"],
        ]
        
        # Para birimi dağılımı ekle
        if len(currency_breakdown) > 1:
            summary_data.append(['', ''])
            summary_data.append(['PARA BİRİMİ DAĞILIMI', ''])
            for currency, amount in currency_breakdown.items():
                summary_data.append([f"Toplam {currency}", f"{amount:,.2f} TL"])
        
        summary_table = Table(summary_data, colWidths=[6*cm, 4*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))
        
        return summary_table

    def _add_header_footer(self, canvas, doc):
        """Header ve footer ekle"""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(colors.HexColor('#2c3e50'))
        canvas.drawString(2*cm, A4[1] - 1*cm, "EXCELLENT FİNANS YÖNETİM SİSTEMİ")
        
        # Sayfa numarası
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.HexColor('#7f8c8d'))
        page_num = f"Sayfa {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 2*cm, 1*cm, page_num)
        
        canvas.restoreState()


# Yardımcı fonksiyonlar - Frontend'den kolayca çağırılabilir
def export_outgoing_invoices_to_pdf(invoice_data, file_path):
    """Giden faturaları PDF'e aktar"""
    exporter = InvoicePDFExporter()
    return exporter.export_invoices_to_pdf(invoice_data, 'outgoing', file_path)

def export_incoming_invoices_to_pdf(invoice_data, file_path):
    """Gelen faturaları PDF'e aktar"""
    exporter = InvoicePDFExporter()
    return exporter.export_invoices_to_pdf(invoice_data, 'incoming', file_path)

def export_general_expenses_to_pdf(expense_data, file_path):
    """Genel giderleri PDF'e aktar"""
    exporter = InvoicePDFExporter()
    return exporter.export_general_expenses_to_pdf(expense_data, file_path)

# Test fonksiyonu
def test_pdf_export():
    """PDF export fonksiyonunu test et"""
    # Test verileri
    test_invoices = [
        {
            'fatura_no': 'FAT-001',
            'irsaliye_no': 'IRS-001',
            'tarih': '2025-11-24',
            'firma': 'Test Firma A',
            'malzeme': 'Hizmet Bedeli',
            'miktar': '1',
            'toplam_tutar_tl': 1000,
            'kdv_tutari': 180,
            'kdv_yuzdesi': 18,
            'birim': 'TL'
        },
        {
            'fatura_no': 'FAT-002',
            'irsaliye_no': 'IRS-002',
            'tarih': '2025-11-23',
            'firma': 'Test Firma B',
            'malzeme': 'Ürün Satışı',
            'miktar': '5',
            'toplam_tutar_tl': 2500,
            'kdv_tutari': 450,
            'kdv_yuzdesi': 18,
            'birim': 'TL'
        }
    ]
    
    # Test
    result = export_outgoing_invoices_to_pdf(test_invoices, 'test_faturalar.pdf')
    print(f"Test PDF oluşturma sonucu: {'Başarılı' if result else 'Başarısız'}")

if __name__ == "__main__":
    test_pdf_export()