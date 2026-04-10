from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import CriminalSituation, MilitarySituation
from datetime import date
import json
from collections import Counter

router = APIRouter()

def calculate_age(birth_date, crime_date):
    """Расчёт возраста на момент преступления"""
    if not birth_date or not crime_date:
        return None
    try:
        age = crime_date.year - birth_date.year
        if (crime_date.month, crime_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        if age < 0 or age > 120:
            return None
        return age
    except:
        return None

def get_month_name(month_num):
    """Преобразует номер месяца в название на русском"""
    months = {
        '01': 'январь', '02': 'февраль', '03': 'март', '04': 'апрель',
        '05': 'май', '06': 'июнь', '07': 'июль', '08': 'август',
        '09': 'сентябрь', '10': 'октябрь', '11': 'ноябрь', '12': 'декабрь'
    }
    return months.get(month_num, month_num)

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # ========== ОБЩАЯ СТАТИСТИКА ==========
    total_crimes = db.query(func.count(CriminalSituation.id)).scalar() or 0
    total_damage = db.query(func.sum(CriminalSituation.sum_damage)).scalar() or 0
    total_incidents = db.query(func.count(MilitarySituation.id)).scalar() or 0
    total_victims = db.query(func.sum(MilitarySituation.victim_count)).scalar() or 0
    
    # ========== 1. ОСНОВНОЙ ТИП ПРЕСТУПЛЕНИЙ ==========
    top_crime_type = db.query(
        CriminalSituation.crime_category_name,
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.crime_category_name.isnot(None),
        CriminalSituation.crime_category_name != ''
    ).group_by(CriminalSituation.crime_category_name).order_by(
        func.count(CriminalSituation.id).desc()
    ).first()
    
    top_crime_name = top_crime_type[0] if top_crime_type else "Нет данных"
    top_crime_count = top_crime_type[1] if top_crime_type else 0
    top_crime_percent = round((top_crime_count / total_crimes * 100), 1) if total_crimes > 0 else 0
    
    # ========== 2. УЯЗВИМАЯ ВОЗРАСТНАЯ ГРУППА ==========
    victims_data = db.query(
        CriminalSituation.victim_birthday,
        CriminalSituation.crime_date
    ).filter(
        CriminalSituation.victim_birthday.isnot(None),
        CriminalSituation.crime_date.isnot(None)
    ).all()
    
    age_groups = {
        "1. 10-25 лет": 0,
        "2. 26-30 лет": 0,
        "3. 31-45 лет": 0,
        "4. 46-60 лет": 0,
        "5. 61+ лет": 0,
        "Не указано": 0
    }
    
    for birth_date, crime_date in victims_data:
        age = calculate_age(birth_date, crime_date)
        if age is not None:
            if 10 <= age <= 25:
                age_groups["1. 10-25 лет"] += 1
            elif 26 <= age <= 30:
                age_groups["2. 26-30 лет"] += 1
            elif 31 <= age <= 45:
                age_groups["3. 31-45 лет"] += 1
            elif 46 <= age <= 60:
                age_groups["4. 46-60 лет"] += 1
            elif age >= 61:
                age_groups["5. 61+ лет"] += 1
            else:
                age_groups["Не указано"] += 1
        else:
            age_groups["Не указано"] += 1
    
    max_group = max([(k, v) for k, v in age_groups.items() if k != "Не указано" and v > 0], key=lambda x: x[1], default=("Нет данных", 0))
    
    # ========== 3. ОСНОВНОЙ ВИД ИНЦИДЕНТОВ ==========
    incident_names = db.query(
        MilitarySituation.incident_name,
        func.count(MilitarySituation.id).label("count")
    ).filter(
        MilitarySituation.incident_name.isnot(None),
        MilitarySituation.incident_name != ''
    ).group_by(MilitarySituation.incident_name).order_by(
        func.count(MilitarySituation.id).desc()
    ).first()
    
    top_incident_name = incident_names[0] if incident_names else "Нет данных"
    top_incident_count = incident_names[1] if incident_names else 0
    top_incident_percent = round((top_incident_count / total_incidents * 100), 1) if total_incidents > 0 else 0
    
    # ========== 4. ГРАФИКИ ДЛЯ КРИМИНАЛЬНОЙ ОБСТАНОВКИ ==========
    crime_stats = db.query(
        CriminalSituation.crime_category_name,
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.crime_category_name.isnot(None),
        CriminalSituation.crime_category_name != ''
    ).group_by(CriminalSituation.crime_category_name).all()
    
    omvd_stats = db.query(
        CriminalSituation.omvd_name,
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.omvd_name.isnot(None),
        CriminalSituation.omvd_name != ''
    ).group_by(CriminalSituation.omvd_name).order_by(
        func.count(CriminalSituation.id).desc()
    ).limit(5).all()
    
    crime_labels = [c[0] for c in crime_stats]
    crime_values = [c[1] for c in crime_stats]
    omvd_labels = [o[0] for o in omvd_stats]
    omvd_values = [o[1] for o in omvd_stats]
    top3_crimes = crime_stats[:3] if crime_stats else []
    
    # ========== 5. ДИНАМИКА ПРЕСТУПЛЕНИЙ ПО МЕСЯЦАМ ==========
    monthly_crimes = db.query(
        func.strftime('%Y-%m', CriminalSituation.crime_date).label("month"),
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.crime_date.isnot(None)
    ).group_by("month").order_by("month").limit(12).all()
    
    monthly_crime_labels = []
    monthly_crime_values = []
    for m in monthly_crimes:
        month_num = m[0].split('-')[1]
        monthly_crime_labels.append(get_month_name(month_num))
        monthly_crime_values.append(m[1])
    
    # ========== 6. ДИНАМИКА ИНЦИДЕНТОВ ПО МЕСЯЦАМ ==========
    monthly_incidents = db.query(
        func.strftime('%Y-%m', MilitarySituation.incident_date).label("month"),
        func.count(MilitarySituation.id).label("incident_count"),
        func.sum(MilitarySituation.victim_count).label("total_victims"),
        func.sum(MilitarySituation.victim_death).label("total_deaths")
    ).filter(
        MilitarySituation.incident_date.isnot(None)
    ).group_by("month").order_by("month").limit(12).all()
    
    monthly_incident_labels = []
    monthly_incident_counts = []
    monthly_victim_counts = []
    monthly_death_counts = []
    for m in monthly_incidents:
        month_num = m[0].split('-')[1]
        monthly_incident_labels.append(get_month_name(month_num))
        monthly_incident_counts.append(m[1])
        monthly_victim_counts.append(m[2] if m[2] else 0)
        monthly_death_counts.append(m[3] if m[3] else 0)
    
    # ========== 7. РАСПРЕДЕЛЕНИЕ ПО ПОЛУ ==========
    gender_counts = {"Мужской": 0, "Женский": 0, "Не указано": 0}
    gender_stats_raw = db.query(
        CriminalSituation.victim_gender,
        func.count(CriminalSituation.id).label("count")
    ).group_by(CriminalSituation.victim_gender).all()
    
    for gender, count in gender_stats_raw:
        if gender == 0:
            gender_counts["Мужской"] = count
        elif gender == 1:
            gender_counts["Женский"] = count
        else:
            gender_counts["Не указано"] += count
    
    gender_labels = [g for g in gender_counts.keys() if gender_counts[g] > 0]
    gender_values = [gender_counts[g] for g in gender_labels]
    
    # Формируем HTML
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>HersonDashboard - Панель мониторинга</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .sidebar {{
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .sidebar .nav-link {{
            color: white;
            padding: 10px 20px;
            margin: 5px 0;
            border-radius: 5px;
        }}
        .sidebar .nav-link:hover {{ background: rgba(255,255,255,0.2); }}
        .sidebar .nav-link.active {{ background: rgba(255,255,255,0.3); }}
        .content {{ padding: 20px; }}
        .insight-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .insight-number {{
            font-size: 2rem;
            font-weight: bold;
        }}
        .stat-card {{
            transition: transform 0.3s;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar p-0">
                <div class="p-3">
                    <h4 class="text-white mb-4">📊 HersonDashboard</h4>
                    <nav class="nav flex-column">
                        <a class="nav-link active" href="/">📈 Главная</a>
                        <a class="nav-link" href="/criminal">🔍 Криминальная обстановка</a>
                        <a class="nav-link" href="/military">⚔️ Военные инциденты</a>
                        <hr>
                        <a class="nav-link" href="/export-full-report">📄 Полный отчёт</a>
                        <a class="nav-link" href="/export-short-report">📄 Краткий отчёт</a>
                    </nav>
                </div>
            </div>
            
            <div class="col-md-10 content">
                <h1 class="mb-4">Панель мониторинга</h1>
                
                <!-- Верхние карточки статистики -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-white bg-primary stat-card">
                            <div class="card-body">
                                <h5>Всего преступлений</h5>
                                <h2>{total_crimes}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-danger stat-card">
                            <div class="card-body">
                                <h5>Ущерб (млн. руб.)</h5>
                                <h2>{total_damage/1000000:.2f}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-success stat-card">
                            <div class="card-body">
                                <h5>Всего инцидентов</h5>
                                <h2>{total_incidents}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-warning stat-card">
                            <div class="card-body">
                                <h5>Пострадавшие</h5>
                                <h2>{total_victims}</h2>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Аналитические инсайты (4 карточки) -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card insight-card">
                            <div class="card-body">
                                <h5>🎯 Основной тип преступлений</h5>
                                <div class="insight-number">{top_crime_name}</div>
                                <p>{top_crime_count} ({top_crime_percent}%)</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card insight-card">
                            <div class="card-body">
                                <h5>⚠️ Уязвимая возрастная группа</h5>
                                <div class="insight-number">{max_group[0]}</div>
                                <p>{max_group[1]} пострадавших</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card insight-card">
                            <div class="card-body">
                                <h5>⚔️ Основной вид инцидентов</h5>
                                <div class="insight-number">{top_incident_name}</div>
                                <p>{top_incident_count} ({top_incident_percent}%)</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-secondary stat-card">
                            <div class="card-body">
                                <h5>📋 Общее количество военных инцидентов</h5>
                                <h2>{total_incidents}</h2>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- График динамики преступлений -->
                <div class="row mb-4">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header bg-success text-white">
                                <h5>📈 Динамика преступлений по месяцам</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="crimeMonthlyChart" height="150"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-8 mb-4">
                        <div class="card">
                            <div class="card-header bg-warning">
                                <h5>📊 Уязвимые группы по возрасту (на момент преступления)</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="ageChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-info text-white">
                                <h5>🏆 Топ-3 категории преступлений</h5>
                            </div>
                            <div class="card-body">
                                <ol class="list-group list-group-numbered">
                                    {''.join([f'<li class="list-group-item d-flex justify-content-between"><span>{c[0]}</span><span class="badge bg-primary rounded-pill">{c[1]}</span></li>' for c in top3_crimes]) if top3_crimes else '<li class="list-group-item">Нет данных</li>'}
                                </ol>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h5>🥧 Преступления по категориям</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="crimeChart" height="250"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header bg-secondary text-white">
                                <h5>👥 Распределение по полу</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="genderChart" height="250"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12 mb-4">
                        <div class="card">
                            <div class="card-header bg-danger text-white">
                                <h5>🗺️ Территориальное распределение преступлений (Топ-5)</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="omvdChart" height="250"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Динамика военных инцидентов (в самом низу) -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header bg-info text-white">
                                <h5>📊 Динамика военных инцидентов по месяцам</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="incidentMonthlyChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Данные для графиков
        const crimeLabels = {json.dumps(crime_labels)};
        const crimeValues = {json.dumps(crime_values)};
        const omvdLabels = {json.dumps(omvd_labels)};
        const omvdValues = {json.dumps(omvd_values)};
        const ageLabels = {json.dumps([k for k in age_groups.keys() if k != "Не указано" and age_groups[k] > 0])};
        const ageValues = {json.dumps([age_groups[k] for k in age_groups.keys() if k != "Не указано" and age_groups[k] > 0])};
        const genderLabels = {json.dumps(gender_labels)};
        const genderValues = {json.dumps(gender_values)};
        
        // Динамика преступлений
        const monthlyCrimeLabels = {json.dumps(monthly_crime_labels)};
        const monthlyCrimeValues = {json.dumps(monthly_crime_values)};
        
        // Динамика инцидентов
        const monthlyIncidentLabels = {json.dumps(monthly_incident_labels)};
        const monthlyIncidentCounts = {json.dumps(monthly_incident_counts)};
        const monthlyVictimCounts = {json.dumps(monthly_victim_counts)};
        const monthlyDeathCounts = {json.dumps(monthly_death_counts)};

        // График преступлений по категориям
        new Chart(document.getElementById('crimeChart'), {{
            type: 'bar',
            data: {{ labels: crimeLabels, datasets: [{{ label: 'Количество', data: crimeValues, backgroundColor: 'rgba(54, 162, 235, 0.5)' }}] }},
            options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        // График по ОМВД
        new Chart(document.getElementById('omvdChart'), {{
            type: 'pie',
            data: {{ labels: omvdLabels, datasets: [{{ data: omvdValues, backgroundColor: ['#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF'] }}] }}
        }});

        // График возрастных групп
        new Chart(document.getElementById('ageChart'), {{
            type: 'bar',
            data: {{ labels: ageLabels, datasets: [{{ label: 'Пострадавшие', data: ageValues, backgroundColor: 'rgba(255, 159, 64, 0.5)' }}] }},
            options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        // График распределения по полу
        new Chart(document.getElementById('genderChart'), {{
            type: 'pie',
            data: {{ labels: genderLabels, datasets: [{{ data: genderValues, backgroundColor: ['#36A2EB','#FF6384','#CED4DA'] }}] }}
        }});

        // График динамики преступлений по месяцам
        new Chart(document.getElementById('crimeMonthlyChart'), {{
            type: 'line',
            data: {{
                labels: monthlyCrimeLabels,
                datasets: [{{
                    label: 'Количество преступлений',
                    data: monthlyCrimeValues,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
            }}
        }});

        // График динамики инцидентов по месяцам
        new Chart(document.getElementById('incidentMonthlyChart'), {{
            type: 'bar',
            data: {{
                labels: monthlyIncidentLabels,
                datasets: [
                    {{
                        label: 'Количество инцидентов',
                        data: monthlyIncidentCounts,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Пострадавшие',
                        data: monthlyVictimCounts,
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }},
                    {{
                        label: 'Погибшие',
                        data: monthlyDeathCounts,
                        backgroundColor: 'rgba(255, 159, 64, 0.5)',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{ display: true, text: 'Количество инцидентов' }}
                    }},
                    y1: {{
                        position: 'right',
                        beginAtZero: true,
                        title: {{ display: true, text: 'Количество человек' }},
                        grid: {{ drawOnChartArea: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


# ========== НОВЫЕ МАРШРУТЫ ДЛЯ ЭКСПОРТА ОТЧЁТОВ ==========

@router.get("/export-full-report")
async def export_full_report(request: Request, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    import os
    import time
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
    from pypdf import PdfMerger
    
    STATIC_DIR = "static"
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Регистрируем шрифт для кириллицы
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        default_font = 'DejaVuSans'
    except:
        default_font = 'Helvetica'
    
    def get_month_name(month_num):
        months = {
            '01': 'январь', '02': 'февраль', '03': 'март', '04': 'апрель',
            '05': 'май', '06': 'июнь', '07': 'июль', '08': 'август',
            '09': 'сентябрь', '10': 'октябрь', '11': 'ноябрь', '12': 'декабрь'
        }
        return months.get(month_num, month_num)
    
    def calculate_age(birth_date, crime_date):
        if not birth_date or not crime_date:
            return None
        try:
            age = crime_date.year - birth_date.year
            if (crime_date.month, crime_date.day) < (birth_date.month, birth_date.day):
                age -= 1
            return age if 0 <= age <= 120 else None
        except:
            return None
    
    def create_bar_chart(labels, values, title, xlabel, ylabel, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(12, 7))
        plt.bar(labels, values, color='steelblue')
        plt.title(title, fontsize=14, pad=20)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_pie_chart(labels, values, title, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(10, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(title, fontsize=14, pad=20)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_line_chart(labels, values, title, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(14, 7))
        plt.plot(labels, values, marker='o', linewidth=2, markersize=6)
        plt.title(title, fontsize=14, pad=20)
        plt.xlabel('Месяц')
        plt.ylabel('Количество')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_multi_bar_chart(labels, incident_counts, victim_counts, death_counts, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(14, 7))
        x = range(len(labels))
        width = 0.25
        plt.bar([i - width for i in x], incident_counts, width, label='Инциденты', color='steelblue')
        plt.bar(x, victim_counts, width, label='Пострадавшие', color='salmon')
        plt.bar([i + width for i in x], death_counts, width, label='Погибшие', color='darkred')
        plt.xlabel('Месяц')
        plt.ylabel('Количество')
        plt.title('Динамика военных инцидентов по месяцам')
        plt.xticks(x, labels, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    try:
        # Собираем данные
        total_crimes = db.query(func.count(CriminalSituation.id)).scalar() or 0
        total_damage = db.query(func.sum(CriminalSituation.sum_damage)).scalar() or 0
        total_incidents = db.query(func.count(MilitarySituation.id)).scalar() or 0
        total_victims = db.query(func.sum(MilitarySituation.victim_count)).scalar() or 0
        
        top_crime = db.query(
            CriminalSituation.crime_category_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_category_name.isnot(None),
            CriminalSituation.crime_category_name != ''
        ).group_by(CriminalSituation.crime_category_name).order_by(
            func.count(CriminalSituation.id).desc()
        ).first()
        
        top_crime_name = top_crime[0] if top_crime else "Нет данных"
        top_crime_count = top_crime[1] if top_crime else 0
        
        top_incident = db.query(
            MilitarySituation.incident_name,
            func.count(MilitarySituation.id).label("count")
        ).filter(
            MilitarySituation.incident_name.isnot(None),
            MilitarySituation.incident_name != ''
        ).group_by(MilitarySituation.incident_name).order_by(
            func.count(MilitarySituation.id).desc()
        ).first()
        
        top_incident_name = top_incident[0] if top_incident else "Нет данных"
        top_incident_count = top_incident[1] if top_incident else 0
        
        victims_data = db.query(
            CriminalSituation.victim_birthday,
            CriminalSituation.crime_date
        ).filter(
            CriminalSituation.victim_birthday.isnot(None),
            CriminalSituation.crime_date.isnot(None)
        ).all()
        
        age_groups = {"10-25 лет": 0, "26-30 лет": 0, "31-45 лет": 0, "46-60 лет": 0, "61+ лет": 0}
        for birth_date, crime_date in victims_data:
            age = calculate_age(birth_date, crime_date)
            if age:
                if 10 <= age <= 25:
                    age_groups["10-25 лет"] += 1
                elif 26 <= age <= 30:
                    age_groups["26-30 лет"] += 1
                elif 31 <= age <= 45:
                    age_groups["31-45 лет"] += 1
                elif 46 <= age <= 60:
                    age_groups["46-60 лет"] += 1
                elif age >= 61:
                    age_groups["61+ лет"] += 1
        
        crime_stats = db.query(
            CriminalSituation.crime_category_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_category_name.isnot(None),
            CriminalSituation.crime_category_name != ''
        ).group_by(CriminalSituation.crime_category_name).all()
        
        omvd_stats = db.query(
            CriminalSituation.omvd_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.omvd_name.isnot(None),
            CriminalSituation.omvd_name != ''
        ).group_by(CriminalSituation.omvd_name).order_by(
            func.count(CriminalSituation.id).desc()
        ).limit(5).all()
        
        monthly_crimes = db.query(
            func.strftime('%Y-%m', CriminalSituation.crime_date).label("month"),
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_date.isnot(None)
        ).group_by("month").order_by("month").limit(12).all()
        
        monthly_crime_labels = [get_month_name(m[0].split('-')[1]) for m in monthly_crimes]
        monthly_crime_values = [m[1] for m in monthly_crimes]
        
        monthly_incidents = db.query(
            func.strftime('%Y-%m', MilitarySituation.incident_date).label("month"),
            func.count(MilitarySituation.id).label("incident_count"),
            func.sum(MilitarySituation.victim_count).label("total_victims"),
            func.sum(MilitarySituation.victim_death).label("total_deaths")
        ).filter(
            MilitarySituation.incident_date.isnot(None)
        ).group_by("month").order_by("month").limit(12).all()
        
        monthly_incident_labels = [get_month_name(m[0].split('-')[1]) for m in monthly_incidents]
        monthly_incident_counts = [m[1] for m in monthly_incidents]
        monthly_victim_counts = [m[2] if m[2] else 0 for m in monthly_incidents]
        monthly_death_counts = [m[3] if m[3] else 0 for m in monthly_incidents]
        
        gender_counts = {"Мужской": 0, "Женский": 0}
        gender_stats_raw = db.query(
            CriminalSituation.victim_gender,
            func.count(CriminalSituation.id).label("count")
        ).group_by(CriminalSituation.victim_gender).all()
        
        for gender, count in gender_stats_raw:
            if gender == 0:
                gender_counts["Мужской"] = count
            elif gender == 1:
                gender_counts["Женский"] = count
        
        temp_charts = []
        
        if crime_stats:
            chart1_path = os.path.join(STATIC_DIR, "temp_chart1.png")
            create_bar_chart([c[0] for c in crime_stats], [c[1] for c in crime_stats], 
                            "Преступления по категориям", "Категория", "Количество", chart1_path)
            temp_charts.append(chart1_path)
        
        if any(age_groups.values()):
            chart2_path = os.path.join(STATIC_DIR, "temp_chart2.png")
            create_bar_chart(list(age_groups.keys()), list(age_groups.values()), 
                            "Уязвимые группы по возрасту", "Возрастная группа", "Количество пострадавших", chart2_path)
            temp_charts.append(chart2_path)
        
        if omvd_stats:
            chart3_path = os.path.join(STATIC_DIR, "temp_chart3.png")
            create_pie_chart([o[0] for o in omvd_stats], [o[1] for o in omvd_stats], 
                            "Территориальное распределение (Топ-5)", chart3_path)
            temp_charts.append(chart3_path)
        
        if monthly_crime_labels:
            chart4_path = os.path.join(STATIC_DIR, "temp_chart4.png")
            create_line_chart(monthly_crime_labels, monthly_crime_values, 
                             "Динамика преступлений по месяцам", chart4_path)
            temp_charts.append(chart4_path)
        
        if monthly_incident_labels:
            chart5_path = os.path.join(STATIC_DIR, "temp_chart5.png")
            create_multi_bar_chart(monthly_incident_labels, monthly_incident_counts, 
                                  monthly_victim_counts, monthly_death_counts, chart5_path)
            temp_charts.append(chart5_path)
        
        # Создаём PDF
        foot_path = os.path.join(STATIC_DIR, "report_foot.pdf")
        doc = SimpleDocTemplate(foot_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=22, alignment=1, spaceAfter=30, fontName=default_font)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, spaceAfter=12, spaceBefore=20, fontName=default_font)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=11, spaceAfter=8, fontName=default_font)
        
        story.append(Paragraph("Сводка по криминальной обстановке", title_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(f"Всего преступлений: {total_crimes}", normal_style))
        story.append(Paragraph(f"Общий ущерб: {total_damage/1000000:.2f} млн. руб.", normal_style))
        story.append(Paragraph(f"Всего военных инцидентов: {total_incidents}", normal_style))
        story.append(Paragraph(f"Всего пострадавших: {total_victims}", normal_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph(f"Основной тип преступлений: {top_crime_name} ({top_crime_count})", normal_style))
        story.append(Paragraph(f"Основной вид инцидентов: {top_incident_name} ({top_incident_count})", normal_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("Распределение по полу:", heading_style))
        gender_text = f"Мужчины: {gender_counts['Мужской']}, Женщины: {gender_counts['Женский']}"
        story.append(Paragraph(gender_text, normal_style))
        story.append(Spacer(1, 15))
        
        for i, chart_path in enumerate(temp_charts):
            if os.path.exists(chart_path):
                story.append(PageBreak())
                img = ReportLabImage(chart_path, width=17*cm, height=12*cm)
                story.append(img)
        
        doc.build(story)
        
        for chart_path in temp_charts:
            if os.path.exists(chart_path):
                os.remove(chart_path)
        
        head_path = os.path.join(STATIC_DIR, "report_head.pdf")
        if not os.path.exists(head_path):
            return Response(
                content="Файл report_head.pdf не найден в папке static",
                status_code=404,
                media_type="text/plain"
            )
        
        full_path = os.path.join(STATIC_DIR, "report_full.pdf")
        merger = PdfMerger()
        merger.append(head_path)
        merger.append(foot_path)
        merger.write(full_path)
        merger.close()
        
        # Отдаём файл на скачивание
        with open(full_path, "rb") as f:
            content = f.read()
        
        # Отправляем HTML с сообщением и автоматическим скачиванием
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Формирование отчёта</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .message {{
                    text-align: center;
                    padding: 40px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }}
                .success {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .download-link {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 30px;
                    background: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 30px;
                    font-size: 18px;
                    transition: transform 0.3s;
                }}
                .download-link:hover {{
                    transform: scale(1.05);
                    background: #218838;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="message">
                <div class="success">✅ Отчёт успешно сформирован!</div>
                <p>Файл report_full.pdf готов к скачиванию</p>
                <a href="/static/report_full.pdf" class="download-link">📥 Скачать отчёт (PDF)</a>
                <p style="margin-top: 20px; font-size: 12px; opacity: 0.8;">Файл также сохранён в папке static сервера</p>
                <p><a href="/" style="color: white;">← Вернуться на главную</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response)
        
    except Exception as e:
        return Response(content=f"Ошибка: {str(e)}", status_code=500, media_type="text/plain")


@router.get("/export-short-report")
async def export_short_report(db: Session = Depends(get_db)):
    from fastapi.responses import Response, HTMLResponse
    import os
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
    
    STATIC_DIR = "static"
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        default_font = 'DejaVuSans'
    except:
        default_font = 'Helvetica'
    
    def get_month_name(month_num):
        months = {
            '01': 'январь', '02': 'февраль', '03': 'март', '04': 'апрель',
            '05': 'май', '06': 'июнь', '07': 'июль', '08': 'август',
            '09': 'сентябрь', '10': 'октябрь', '11': 'ноябрь', '12': 'декабрь'
        }
        return months.get(month_num, month_num)
    
    def calculate_age(birth_date, crime_date):
        if not birth_date or not crime_date:
            return None
        try:
            age = crime_date.year - birth_date.year
            if (crime_date.month, crime_date.day) < (birth_date.month, birth_date.day):
                age -= 1
            return age if 0 <= age <= 120 else None
        except:
            return None
    
    def create_bar_chart(labels, values, title, xlabel, ylabel, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(12, 7))
        plt.bar(labels, values, color='steelblue')
        plt.title(title, fontsize=14, pad=20)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_pie_chart(labels, values, title, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(10, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(title, fontsize=14, pad=20)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_line_chart(labels, values, title, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(14, 7))
        plt.plot(labels, values, marker='o', linewidth=2, markersize=6)
        plt.title(title, fontsize=14, pad=20)
        plt.xlabel('Месяц')
        plt.ylabel('Количество')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_multi_bar_chart(labels, incident_counts, victim_counts, death_counts, filename):
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.figure(figsize=(14, 7))
        x = range(len(labels))
        width = 0.25
        plt.bar([i - width for i in x], incident_counts, width, label='Инциденты', color='steelblue')
        plt.bar(x, victim_counts, width, label='Пострадавшие', color='salmon')
        plt.bar([i + width for i in x], death_counts, width, label='Погибшие', color='darkred')
        plt.xlabel('Месяц')
        plt.ylabel('Количество')
        plt.title('Динамика военных инцидентов по месяцам')
        plt.xticks(x, labels, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    try:
        # Собираем данные (как в export_full_report)
        total_crimes = db.query(func.count(CriminalSituation.id)).scalar() or 0
        total_damage = db.query(func.sum(CriminalSituation.sum_damage)).scalar() or 0
        total_incidents = db.query(func.count(MilitarySituation.id)).scalar() or 0
        total_victims = db.query(func.sum(MilitarySituation.victim_count)).scalar() or 0
        
        top_crime = db.query(
            CriminalSituation.crime_category_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_category_name.isnot(None),
            CriminalSituation.crime_category_name != ''
        ).group_by(CriminalSituation.crime_category_name).order_by(
            func.count(CriminalSituation.id).desc()
        ).first()
        
        top_crime_name = top_crime[0] if top_crime else "Нет данных"
        top_crime_count = top_crime[1] if top_crime else 0
        
        top_incident = db.query(
            MilitarySituation.incident_name,
            func.count(MilitarySituation.id).label("count")
        ).filter(
            MilitarySituation.incident_name.isnot(None),
            MilitarySituation.incident_name != ''
        ).group_by(MilitarySituation.incident_name).order_by(
            func.count(MilitarySituation.id).desc()
        ).first()
        
        top_incident_name = top_incident[0] if top_incident else "Нет данных"
        top_incident_count = top_incident[1] if top_incident else 0
        
        victims_data = db.query(
            CriminalSituation.victim_birthday,
            CriminalSituation.crime_date
        ).filter(
            CriminalSituation.victim_birthday.isnot(None),
            CriminalSituation.crime_date.isnot(None)
        ).all()
        
        age_groups = {"10-25 лет": 0, "26-30 лет": 0, "31-45 лет": 0, "46-60 лет": 0, "61+ лет": 0}
        for birth_date, crime_date in victims_data:
            age = calculate_age(birth_date, crime_date)
            if age:
                if 10 <= age <= 25:
                    age_groups["10-25 лет"] += 1
                elif 26 <= age <= 30:
                    age_groups["26-30 лет"] += 1
                elif 31 <= age <= 45:
                    age_groups["31-45 лет"] += 1
                elif 46 <= age <= 60:
                    age_groups["46-60 лет"] += 1
                elif age >= 61:
                    age_groups["61+ лет"] += 1
        
        crime_stats = db.query(
            CriminalSituation.crime_category_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_category_name.isnot(None),
            CriminalSituation.crime_category_name != ''
        ).group_by(CriminalSituation.crime_category_name).all()
        
        omvd_stats = db.query(
            CriminalSituation.omvd_name,
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.omvd_name.isnot(None),
            CriminalSituation.omvd_name != ''
        ).group_by(CriminalSituation.omvd_name).order_by(
            func.count(CriminalSituation.id).desc()
        ).limit(5).all()
        
        monthly_crimes = db.query(
            func.strftime('%Y-%m', CriminalSituation.crime_date).label("month"),
            func.count(CriminalSituation.id).label("count")
        ).filter(
            CriminalSituation.crime_date.isnot(None)
        ).group_by("month").order_by("month").limit(12).all()
        
        monthly_crime_labels = [get_month_name(m[0].split('-')[1]) for m in monthly_crimes]
        monthly_crime_values = [m[1] for m in monthly_crimes]
        
        monthly_incidents = db.query(
            func.strftime('%Y-%m', MilitarySituation.incident_date).label("month"),
            func.count(MilitarySituation.id).label("incident_count"),
            func.sum(MilitarySituation.victim_count).label("total_victims"),
            func.sum(MilitarySituation.victim_death).label("total_deaths")
        ).filter(
            MilitarySituation.incident_date.isnot(None)
        ).group_by("month").order_by("month").limit(12).all()
        
        monthly_incident_labels = [get_month_name(m[0].split('-')[1]) for m in monthly_incidents]
        monthly_incident_counts = [m[1] for m in monthly_incidents]
        monthly_victim_counts = [m[2] if m[2] else 0 for m in monthly_incidents]
        monthly_death_counts = [m[3] if m[3] else 0 for m in monthly_incidents]
        
        gender_counts = {"Мужской": 0, "Женский": 0}
        gender_stats_raw = db.query(
            CriminalSituation.victim_gender,
            func.count(CriminalSituation.id).label("count")
        ).group_by(CriminalSituation.victim_gender).all()
        
        for gender, count in gender_stats_raw:
            if gender == 0:
                gender_counts["Мужской"] = count
            elif gender == 1:
                gender_counts["Женский"] = count
        
        temp_charts = []
        
        if crime_stats:
            chart1_path = os.path.join(STATIC_DIR, "temp_chart1.png")
            create_bar_chart([c[0] for c in crime_stats], [c[1] for c in crime_stats], 
                            "Преступления по категориям", "Категория", "Количество", chart1_path)
            temp_charts.append(chart1_path)
        
        if any(age_groups.values()):
            chart2_path = os.path.join(STATIC_DIR, "temp_chart2.png")
            create_bar_chart(list(age_groups.keys()), list(age_groups.values()), 
                            "Уязвимые группы по возрасту", "Возрастная группа", "Количество пострадавших", chart2_path)
            temp_charts.append(chart2_path)
        
        if omvd_stats:
            chart3_path = os.path.join(STATIC_DIR, "temp_chart3.png")
            create_pie_chart([o[0] for o in omvd_stats], [o[1] for o in omvd_stats], 
                            "Территориальное распределение (Топ-5)", chart3_path)
            temp_charts.append(chart3_path)
        
        if monthly_crime_labels:
            chart4_path = os.path.join(STATIC_DIR, "temp_chart4.png")
            create_line_chart(monthly_crime_labels, monthly_crime_values, 
                             "Динамика преступлений по месяцам", chart4_path)
            temp_charts.append(chart4_path)
        
        if monthly_incident_labels:
            chart5_path = os.path.join(STATIC_DIR, "temp_chart5.png")
            create_multi_bar_chart(monthly_incident_labels, monthly_incident_counts, 
                                  monthly_victim_counts, monthly_death_counts, chart5_path)
            temp_charts.append(chart5_path)
        
        # Создаём PDF
        short_path = os.path.join(STATIC_DIR, "report_short.pdf")
        doc = SimpleDocTemplate(short_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=22, alignment=1, spaceAfter=30, fontName=default_font)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, spaceAfter=12, spaceBefore=20, fontName=default_font)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=11, spaceAfter=8, fontName=default_font)
        
        story.append(Paragraph("Сводка по криминальной обстановке", title_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(f"Всего преступлений: {total_crimes}", normal_style))
        story.append(Paragraph(f"Общий ущерб: {total_damage/1000000:.2f} млн. руб.", normal_style))
        story.append(Paragraph(f"Всего военных инцидентов: {total_incidents}", normal_style))
        story.append(Paragraph(f"Всего пострадавших: {total_victims}", normal_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph(f"Основной тип преступлений: {top_crime_name} ({top_crime_count})", normal_style))
        story.append(Paragraph(f"Основной вид инцидентов: {top_incident_name} ({top_incident_count})", normal_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("Распределение по полу:", heading_style))
        gender_text = f"Мужчины: {gender_counts['Мужской']}, Женщины: {gender_counts['Женский']}"
        story.append(Paragraph(gender_text, normal_style))
        story.append(Spacer(1, 15))
        
        for i, chart_path in enumerate(temp_charts):
            if os.path.exists(chart_path):
                story.append(PageBreak())
                img = ReportLabImage(chart_path, width=17*cm, height=12*cm)
                story.append(img)
        
        doc.build(story)
        
        for chart_path in temp_charts:
            if os.path.exists(chart_path):
                os.remove(chart_path)
        
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Формирование отчёта</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .message {{
                    text-align: center;
                    padding: 40px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }}
                .success {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .download-link {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 30px;
                    background: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 30px;
                    font-size: 18px;
                    transition: transform 0.3s;
                }}
                .download-link:hover {{
                    transform: scale(1.05);
                    background: #218838;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="message">
                <div class="success">✅ Краткий отчёт успешно сформирован!</div>
                <p>Файл report_short.pdf готов к скачиванию</p>
                <a href="/static/report_short.pdf" class="download-link">📥 Скачать отчёт (PDF)</a>
                <p style="margin-top: 20px; font-size: 12px; opacity: 0.8;">Файл также сохранён в папке static сервера</p>
                <p><a href="/" style="color: white;">← Вернуться на главную</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response)
        
    except Exception as e:
        return Response(content=f"Ошибка: {str(e)}", status_code=500, media_type="text/plain")