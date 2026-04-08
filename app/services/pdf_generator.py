from fastapi import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
from datetime import datetime
import os

# Настраиваем matplotlib для поддержки кириллицы
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'FreeSans', 'Liberation Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def create_pie_chart(labels, values, title):
    """Создает круговую диаграмму и возвращает изображение"""
    plt.figure(figsize=(8, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.title(title, fontsize=14, pad=20)
    plt.axis('equal')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

def create_bar_chart(labels, values, title, xlabel, ylabel):
    """Создает столбчатую диаграмму и возвращает изображение"""
    plt.figure(figsize=(8, 6))
    colors_bar = plt.cm.Set3(np.linspace(0, 1, len(labels)))
    plt.bar(labels, values, color=colors_bar)
    plt.title(title, fontsize=14, pad=20)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

def generate_pdf_report(data):
    """Генерирует PDF с графиками и таблицами"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Создаем стили
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#333333'),
        alignment=1,
        spaceAfter=30
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        alignment=1,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#000000'),
        spaceAfter=10
    )
    
    story = []
    
    # Заголовок
    story.append(Paragraph("Аналитический отчет по продажам", title_style))
    
    # Дата
    story.append(Paragraph(f"Дата формирования: {data['generated_date']}", date_style))
    story.append(Spacer(1, 20))
    
    # 1. Круговая диаграмма - продажи по категориям
    if data.get('sales_by_category') and data['sales_by_category']:
        story.append(Paragraph("Продажи по категориям", heading_style))
        story.append(Spacer(1, 10))
        
        categories = [item['category'] for item in data['sales_by_category']]
        revenues = [item['revenue'] for item in data['sales_by_category']]
        chart_buf = create_pie_chart(categories, revenues, "Распределение продаж по категориям")
        img = Image(chart_buf, width=14*cm, height=10*cm)
        story.append(img)
        story.append(Spacer(1, 20))
    
    # 2. Столбчатая диаграмма - продажи по регионам
    if data.get('sales_by_region') and data['sales_by_region']:
        story.append(Paragraph("Продажи по регионам", heading_style))
        story.append(Spacer(1, 10))
        
        regions = [item['region'] for item in data['sales_by_region']]
        revenues = [item['revenue'] for item in data['sales_by_region']]
        chart_buf = create_bar_chart(regions, revenues, "Выручка по регионам", "Регион", "Выручка (руб.)")
        img = Image(chart_buf, width=14*cm, height=10*cm)
        story.append(img)
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"}
    )

def generate_criminal_report(data):
    """Генерирует PDF отчет по криминальной обстановке"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#333333'),
        alignment=1,
        spaceAfter=30
    )
    
    story = []
    
    # Заголовок
    story.append(Paragraph("Отчет по криминальной обстановке", title_style))
    story.append(Spacer(1, 20))
    
    # Таблица с данными
    if data.get('crimes') and data['crimes']:
        table_data = [["ID", "Дата", "Территориальный орган", "Категория", "Ущерб (руб.)"]]
        for crime in data['crimes']:
            table_data.append([
                str(crime.get('id', '')),
                str(crime.get('crime_date', '')),
                crime.get('omvd_name', ''),
                crime.get('crime_category', ''),
                f"{crime.get('sum_damage', 0):,.2f}"
            ])
        
        table = Table(table_data, colWidths=[2*cm, 3*cm, 6*cm, 5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=criminal_report.pdf"}
    )

def generate_military_report(data):
    """Генерирует PDF отчет по военным инцидентам"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#333333'),
        alignment=1,
        spaceAfter=30
    )
    
    story = []
    
    # Заголовок
    story.append(Paragraph("Отчет по военным инцидентам", title_style))
    story.append(Spacer(1, 20))
    
    # Таблица с данными
    if data.get('incidents') and data['incidents']:
        table_data = [["ID", "Дата", "Название", "Пострадавшие", "Погибшие", "Дроны"]]
        for incident in data['incidents']:
            table_data.append([
                str(incident.get('id', '')),
                str(incident.get('incident_date', '')),
                incident.get('incident_name', ''),
                str(incident.get('victim_count', 0)),
                str(incident.get('victim_death', 0)),
                str(incident.get('drone_count', 0))
            ])
        
        table = Table(table_data, colWidths=[2*cm, 3*cm, 5*cm, 3*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=military_report.pdf"}
    )