from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MilitarySituation
from app.schemas import MilitarySituationCreate
from app.services.excel_importer import ExcelImporter
from app.services.pdf_generator import generate_military_report
import json

router = APIRouter()

@router.post("/import-excel")
async def import_military_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Импорт военных инцидентов из Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате Excel")
    try:
        content = await file.read()
        importer = ExcelImporter(db)
        result = importer.import_military_situations(content)
        if result['success']:
            return {
                "status": "success",
                "imported": result.get('imported', 0),
                "message": f"Импортировано {result.get('imported', 0)} записей",
                "errors": result.get('errors', [])
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Ошибка импорта'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")

@router.get("/download-template")
async def download_military_template():
    """Скачать шаблон Excel для военных инцидентов"""
    importer = ExcelImporter(None)
    content = importer.download_template_military()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=military_template.xlsx"}
    )

@router.post("/add")
async def add_military_situation(
    incident: MilitarySituationCreate,
    db: Session = Depends(get_db)
):
    db_incident = MilitarySituation(**incident.dict())
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return {"status": "success", "id": db_incident.id}

@router.get("/export-pdf")
async def export_military_pdf(db: Session = Depends(get_db)):
    """Экспорт военных инцидентов в PDF"""
    incidents = db.query(MilitarySituation).all()
    data = {
        'incidents': [
            {
                'id': i.id,
                'incident_date': i.incident_date,
                'incident_name': i.incident_name or '-',
                'victim_count': i.victim_count or 0,
                'victim_death': i.victim_death or 0,
                'drone_count': i.drone_count or 0
            }
            for i in incidents
        ]
    }
    return generate_military_report(data)

@router.post("/clear-all")
async def clear_all_incidents(db: Session = Depends(get_db)):
    """Полная очистка таблицы военных инцидентов"""
    try:
        count = db.query(MilitarySituation).count()
        db.query(MilitarySituation).delete()
        db.commit()
        return {"status": "success", "message": f"Удалено {count} записей"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_class=HTMLResponse)
async def military_list(request: Request, db: Session = Depends(get_db)):
    incidents = db.query(MilitarySituation).all()
    
    # Преобразуем данные в JSON для JavaScript
    incidents_data = []
    for inc in incidents:
        incidents_data.append({
            'id': inc.id,
            'incident_date': str(inc.incident_date) if inc.incident_date else '',
            'incident_time': str(inc.incident_time) if inc.incident_time else '',
            'incident_name': inc.incident_name or '',
            'employe_action': inc.employe_action or '',
            'time_cancel_incident': str(inc.time_cancel_incident) if inc.time_cancel_incident else '',
            'incident_effect': inc.incident_effect or '',
            'victim_count': inc.victim_count or 0,
            'victim_death': inc.victim_death or 0,
            'drone_count': inc.drone_count or 0,
            'initiator_name': inc.initiator_name or ''
        })
    
    incidents_json = json.dumps(incidents_data, ensure_ascii=False)
    
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Военные инциденты - HersonDashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
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
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar p-0">
                <div class="p-3">
                    <h4 class="text-white mb-4">📊 HersonDashboard</h4>
                    <nav class="nav flex-column">
                        <a class="nav-link" href="/">📈 Главная</a>
                        <a class="nav-link" href="/criminal">🔍 Криминальная обстановка</a>
                        <a class="nav-link active" href="/military">⚔️ Военные инциденты</a>
                    </nav>
                </div>
            </div>
            
            <div class="col-md-10 content">
                <h1 class="mb-4">⚔️ Военные инциденты</h1>
                
                <div class="card mb-4">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">📥 Импорт данных из Excel</h5>
                    </div>
                    <div class="card-body">
                        <form id="importForm" enctype="multipart/form-data">
                            <div class="row">
                                <div class="col-md-6">
                                    <input type="file" name="file" class="form-control" accept=".xlsx,.xls" required>
                                </div>
                                <div class="col-md-6">
                                    <button type="submit" class="btn btn-success">📥 Импортировать</button>
                                    <a href="/military/download-template" class="btn btn-info">📄 Скачать шаблон</a>
                                    <a href="/military/export-pdf" class="btn btn-danger">📄 Экспорт PDF</a>
                                    <button type="button" class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#clearModal">🗑️ Очистить</button>
                                </div>
                            </div>
                            <div id="importResult" class="mt-2" style="display: none;"></div>
                        </form>
                    </div>
                </div>
                
                <!-- Кнопка для открытия модального окна добавления -->
                <div class="mb-3">
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addIncidentModal">
                        ➕ Добавить новый инцидент
                    </button>
                </div>

                <!-- Модальное окно добавления инцидента -->
                <div class="modal fade" id="addIncidentModal" tabindex="-1" aria-labelledby="addIncidentModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title" id="addIncidentModalLabel">➕ Добавление нового инцидента</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                            </div>
                            <div class="modal-body">
                                <form id="incidentFormModal">
                                    <div class="row">
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Дата инцидента *</label>
                                            <input type="date" name="incident_date" class="form-control" required>
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Время</label>
                                            <input type="time" name="incident_time" class="form-control">
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Название инцидента</label>
                                            <input type="text" name="incident_name" class="form-control">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Действия сотрудников</label>
                                            <input type="text" name="employe_action" class="form-control">
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Время отмены</label>
                                            <input type="time" name="time_cancel_incident" class="form-control">
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Инициатор</label>
                                            <input type="text" name="initiator_name" class="form-control" placeholder="Кто инициировал">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Последствия инцидента</label>
                                            <input type="text" name="incident_effect" class="form-control">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Количество пострадавших</label>
                                            <input type="number" name="victim_count" class="form-control" value="0">
                                        </div>
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Количество погибших</label>
                                            <input type="number" name="victim_death" class="form-control" value="0">
                                        </div>
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Количество дронов</label>
                                            <input type="number" name="drone_count" class="form-control" value="0">
                                        </div>
                                    </div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" data-bs-dismiss="modal">Отменить</button>
                                <button type="button" class="btn btn-success" id="saveIncidentBtn">Сохранить</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h5>Список инцидентов</h5>
                    </div>
                    <div class="card-body">
                        <table id="incidentsTable" class="table table-striped">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Дата</th>
                                    <th>Время</th>
                                    <th>Название</th>
                                    <th>Действия сотрудников</th>
                                    <th>Время отмены</th>
                                    <th>Последствия</th>
                                    <th>Пострадавшие</th>
                                    <th>Погибшие</th>
                                    <th>Дроны</th>
                                    <th>Инициатор</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal fade" id="clearModal" tabindex="-1">
        <div class="modal-dialog"><div class="modal-content">
            <div class="modal-header bg-danger text-white"><h5>Подтверждение</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">Удалить все записи? Это необратимо.</div>
            <div class="modal-footer"><button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button><button id="confirmClear" class="btn btn-danger">Да, удалить</button></div>
        </div></div>
    </div>
    
    <script>
        let incidentsData = {incidents_json};
        
        function renderTable() {{
            const tbody = document.querySelector('#incidentsTable tbody');
            tbody.innerHTML = '';
            incidentsData.forEach(i => {{
                const row = tbody.insertRow();
                row.insertCell(0).innerText = i.id;
                row.insertCell(1).innerText = i.incident_date;
                row.insertCell(2).innerText = i.incident_time;
                row.insertCell(3).innerText = i.incident_name;
                row.insertCell(4).innerText = i.employe_action;
                row.insertCell(5).innerText = i.time_cancel_incident;
                row.insertCell(6).innerText = i.incident_effect;
                row.insertCell(7).innerText = i.victim_count;
                row.insertCell(8).innerText = i.victim_death;
                row.insertCell(9).innerText = i.drone_count;
                row.insertCell(10).innerText = i.initiator_name;
            }});
        }}
        
        function showResult(msg, type) {{
            const div = document.getElementById('importResult');
            div.className = `alert alert-${{type}}`;
            div.innerHTML = msg;
            div.style.display = 'block';
            setTimeout(() => div.style.display = 'none', 5000);
        }}
        
        document.getElementById('importForm').onsubmit = async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const res = await fetch('/military/import-excel', {{ method: 'POST', body: formData }});
            const result = await res.json();
            if (res.ok) showResult(`✅ Импортировано: ${{result.imported}}`, 'success');
            else showResult(`❌ ${{result.detail}}`, 'danger');
            setTimeout(() => location.reload(), 2000);
        }};
        
        document.getElementById('confirmClear').onclick = async () => {{
            const res = await fetch('/military/clear-all', {{ method: 'POST' }});
            if (res.ok) location.reload();
        }};
        
        document.getElementById('saveIncidentBtn').onclick = async () => {{
            const formData = {{}};
            $('#incidentFormModal').serializeArray().forEach(item => {{
                formData[item.name] = item.value;
            }});
            if (!formData.incident_date) {{
                showResult('Пожалуйста, заполните обязательное поле: дата инцидента', 'danger');
                return;
            }}
            // Преобразуем числовые поля
            formData.victim_count = parseInt(formData.victim_count) || 0;
            formData.victim_death = parseInt(formData.victim_death) || 0;
            formData.drone_count = parseInt(formData.drone_count) || 0;
            
            const res = await fetch('/military/add', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(formData)
            }});
            if (res.ok) {{
                $('#addIncidentModal').modal('hide');
                showResult('✅ Запись успешно добавлена', 'success');
                setTimeout(() => location.reload(), 1000);
            }} else {{
                const err = await res.json();
                showResult(`❌ ${{err.detail || 'Ошибка при добавлении'}}`, 'danger');
            }}
        }};
        
        renderTable();
        $(document).ready(function() {{
            $('#incidentsTable').DataTable({{
                language: {{ url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/ru.json' }},
                pageLength: 25,
                order: [[0, 'desc']]
            }});
        }});
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)