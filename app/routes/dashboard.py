from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import CriminalSituation, MilitarySituation

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # Общая статистика
    total_crimes = db.query(func.count(CriminalSituation.id)).scalar() or 0
    total_damage = db.query(func.sum(CriminalSituation.sum_damage)).scalar() or 0
    total_incidents = db.query(func.count(MilitarySituation.id)).scalar() or 0
    total_victims = db.query(func.sum(MilitarySituation.victim_count)).scalar() or 0
    
    # Данные для графиков
    crime_stats = db.query(
        CriminalSituation.crime_category_name,
        func.count(CriminalSituation.id).label("count")
    ).group_by(CriminalSituation.crime_category_name).all()
    
    omvd_stats = db.query(
        CriminalSituation.omvd_name,
        func.count(CriminalSituation.id).label("count")
    ).group_by(CriminalSituation.omvd_name).order_by(
        func.count(CriminalSituation.id).desc()
    ).limit(5).all()
    
    # Преобразуем в JSON для JavaScript
    import json
    crime_labels = json.dumps([str(row[0]) if row[0] else "Не указано" for row in crime_stats])
    crime_values = json.dumps([row[1] for row in crime_stats])
    omvd_labels = json.dumps([str(row[0]) if row[0] else "Не указано" for row in omvd_stats])
    omvd_values = json.dumps([row[1] for row in omvd_stats])
    
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HersonDashboard - Панель мониторинга</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .navbar-brand {{ font-weight: bold; }}
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
        .stat-card {{
            transition: transform 0.3s;
            cursor: pointer;
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
                    </nav>
                </div>
            </div>
            
            <div class="col-md-10 content">
                <h1 class="mb-4">Панель мониторинга</h1>
                
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-white bg-primary stat-card">
                            <div class="card-body">
                                <h5 class="card-title">Всего преступлений</h5>
                                <h2>{total_crimes}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-danger stat-card">
                            <div class="card-body">
                                <h5 class="card-title">Ущерб (млн. руб.)</h5>
                                <h2>{total_damage/1000000:.2f}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-success stat-card">
                            <div class="card-body">
                                <h5 class="card-title">Всего инцидентов</h5>
                                <h2>{total_incidents}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-white bg-warning stat-card">
                            <div class="card-body">
                                <h5 class="card-title">Пострадавшие</h5>
                                <h2>{total_victims}</h2>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Преступления по категориям</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="crimeChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Территориальное распределение (Топ-5)</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="omvdChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const crimeLabels = {crime_labels};
        const crimeValues = {crime_values};
        const omvdLabels = {omvd_labels};
        const omvdValues = {omvd_values};

        new Chart(document.getElementById('crimeChart'), {{
            type: 'bar',
            data: {{
                labels: crimeLabels,
                datasets: [{{
                    label: 'Количество преступлений',
                    data: crimeValues,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
            }}
        }});

        new Chart(document.getElementById('omvdChart'), {{
            type: 'pie',
            data: {{
                labels: omvdLabels,
                datasets: [{{
                    data: omvdValues,
                    backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ position: 'bottom' }} }}
            }}
        }});
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)