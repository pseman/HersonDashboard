from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import CriminalSituation, MilitarySituation
from datetime import date
import json

router = APIRouter()


def calculate_age(birth_date, crime_date):
    """Расчёт возраста на момент преступления"""
    if not birth_date or not crime_date:
        return None
    try:
        age = crime_date.year - birth_date.year
        # Корректировка, если день рождения ещё не наступил
        if (crime_date.month, crime_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        if age < 0 or age > 120:
            return None
        return age
    except:
        return None




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
    
    # ========== 2. УЯЗВИМЫЕ ГРУППЫ ПО ВОЗРАСТУ ==========
    # Получаем все записи с датами
    # В блоке возрастных групп используем crime_date и victim_birthday
    victims_data = db.query(
        CriminalSituation.victim_birthday,
        CriminalSituation.crime_date  # используем crime_date
    ).filter(
        CriminalSituation.victim_birthday.isnot(None),
        CriminalSituation.crime_date.isnot(None)
    ).all()
    
    # Считаем возрастные группы
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
    
    # Для отображения на графике (исключаем "Не указано")
    chart_age_labels = [k for k, v in age_groups.items() if k != "Не указано" and v > 0]
    chart_age_values = [age_groups[k] for k in chart_age_labels]
    
    # Находим самую уязвимую группу (с максимальным значением, исключая "Не указано")
    max_group = max([(k, v) for k, v in age_groups.items() if k != "Не указано"], key=lambda x: x[1], default=("Нет данных", 0))
    
    # ========== 3. РАСПРЕДЕЛЕНИЕ ПО ПОЛУ ==========
    # victim_gender: 0 - мужской, 1 - женский
    gender_counts = {
        "Мужской": 0,
        "Женский": 0,
        "Не указано": 0
    }
    
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
    
    # ========== 4. ОСТАЛЬНЫЕ ГРАФИКИ ==========
    # Преступления по категориям
    crime_stats = db.query(
        CriminalSituation.crime_category_name,
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.crime_category_name.isnot(None),
        CriminalSituation.crime_category_name != ''
    ).group_by(CriminalSituation.crime_category_name).all()
    
    # Территориальное распределение (Топ-5)
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
    
    # Динамика по месяцам
    monthly_stats = db.query(
        func.strftime('%Y-%m', CriminalSituation.registration_date).label("month"),
        func.count(CriminalSituation.id).label("count")
    ).filter(
        CriminalSituation.registration_date.isnot(None)
    ).group_by("month").order_by("month").limit(12).all()
    
    monthly_labels = [m[0] for m in monthly_stats]
    monthly_values = [m[1] for m in monthly_stats]
    
    # Топ-3 категории
    top3_crimes = crime_stats[:3] if crime_stats else []
    
    # ========== ОТЛАДОЧНАЯ ИНФОРМАЦИЯ (в лог) ==========
    print(f"\n📊 ОТЛАДКА ВОЗРАСТНЫХ ГРУПП:")
    print(f"   Всего записей с датами: {len(victims_data)}")
    for k, v in age_groups.items():
        print(f"   {k}: {v}")
    print(f"   Самая уязвимая группа: {max_group[0]} ({max_group[1]})")
    
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
                    </nav>
                </div>
            </div>
            
            <div class="col-md-10 content">
                <h1 class="mb-4">Панель мониторинга</h1>
                
                <!-- Карточки статистики -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-white bg-primary">
                            <div class="card-body">
                                <h5>Всего преступлений</h5>
                                <h2>{total_crimes}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-danger">
                            <div class="card-body">
                                <h5>Ущерб (млн. руб.)</h5>
                                <h2>{total_damage/1000000:.2f}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-success">
                            <div class="card-body">
                                <h5>Всего инцидентов</h5>
                                <h2>{total_incidents}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-warning">
                            <div class="card-body">
                                <h5>Пострадавшие</h5>
                                <h2>{total_victims}</h2>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Аналитические инсайты -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card insight-card">
                            <div class="card-body">
                                <h5>🎯 Основной тип преступлений</h5>
                                <div class="insight-number">{top_crime_name}</div>
                                <p>{top_crime_count} преступлений ({top_crime_percent}%)</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card insight-card">
                            <div class="card-body">
                                <h5>⚠️ Самая уязвимая возрастная группа</h5>
                                <div class="insight-number">{max_group[0]}</div>
                                <p>{max_group[1]} пострадавших</p>
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
                                <h5>🏆 Топ-3 категории</h5>
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
                            <div class="card-header bg-success text-white">
                                <h5>📈 Динамика по месяцам</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="monthlyChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12 mb-4">
                        <div class="card">
                            <div class="card-header bg-danger text-white">
                                <h5>🗺️ Территориальное распределение (Топ-5)</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="omvdChart" height="250"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const crimeLabels = {json.dumps(crime_labels)};
        const crimeValues = {json.dumps(crime_values)};
        const omvdLabels = {json.dumps(omvd_labels)};
        const omvdValues = {json.dumps(omvd_values)};
        const ageLabels = {json.dumps(chart_age_labels)};
        const ageValues = {json.dumps(chart_age_values)};
        const monthlyLabels = {json.dumps(monthly_labels)};
        const monthlyValues = {json.dumps(monthly_values)};
        const genderLabels = {json.dumps(gender_labels)};
        const genderValues = {json.dumps(gender_values)};

        new Chart(document.getElementById('crimeChart'), {{
            type: 'bar',
            data: {{ labels: crimeLabels, datasets: [{{ label: 'Количество', data: crimeValues, backgroundColor: 'rgba(54, 162, 235, 0.5)' }}] }},
            options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        new Chart(document.getElementById('omvdChart'), {{
            type: 'pie',
            data: {{ labels: omvdLabels, datasets: [{{ data: omvdValues, backgroundColor: ['#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF'] }}] }}
        }});

        new Chart(document.getElementById('ageChart'), {{
            type: 'bar',
            data: {{ labels: ageLabels, datasets: [{{ label: 'Пострадавшие', data: ageValues, backgroundColor: 'rgba(255, 159, 64, 0.5)' }}] }},
            options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        new Chart(document.getElementById('monthlyChart'), {{
            type: 'line',
            data: {{ labels: monthlyLabels, datasets: [{{ label: 'Преступления', data: monthlyValues, borderColor: '#28a745', fill: true }}] }}
        }});

        new Chart(document.getElementById('genderChart'), {{
            type: 'pie',
            data: {{ labels: genderLabels, datasets: [{{ data: genderValues, backgroundColor: ['#36A2EB','#FF6384','#CED4DA'] }}] }}
        }});
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)