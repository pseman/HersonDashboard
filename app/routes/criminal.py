from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CriminalSituation, OMVD, CrimeCategory
from app.schemas import CriminalSituationCreate
from app.services.excel_importer import ExcelImporter
from app.services.pdf_generator import generate_criminal_report
import json

router = APIRouter()

@router.post("/import-excel")
async def import_criminal_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Импорт криминальных ситуаций из Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате Excel")
    
    try:
        content = await file.read()
        importer = ExcelImporter(db)
        result = importer.import_criminal_situations(content)
        
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
async def download_criminal_template():
    """Скачать шаблон Excel для криминальных ситуаций"""
    importer = ExcelImporter(None)
    content = importer.download_template_criminal()
    
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=criminal_template.xlsx"}
    )


@router.post("/add")
async def add_criminal_situation(
    crime: CriminalSituationCreate,
    db: Session = Depends(get_db)
):
    db_crime = CriminalSituation(**crime.dict())
    db.add(db_crime)
    db.commit()
    db.refresh(db_crime)
    return {"status": "success", "id": db_crime.id}


@router.get("/export-pdf")
async def export_criminal_pdf(db: Session = Depends(get_db)):
    """Экспорт криминальных ситуаций в PDF"""
    crimes = db.query(CriminalSituation).all()
    data = {
        'crimes': [
            {
                'id': c.id,
                'crime_date': c.crime_date,
                'omvd_name': c.omvd_name,
                'crime_category': c.crime_category_name,
                'sum_damage': c.sum_damage or 0
            }
            for c in crimes
        ]
    }
    return generate_criminal_report(data)


@router.post("/clear-all")
async def clear_all_crimes(db: Session = Depends(get_db)):
    """Полная очистка таблицы криминальных ситуаций"""
    try:
        count = db.query(CriminalSituation).count()
        db.query(CriminalSituation).delete()
        db.commit()
        return {
            "status": "success",
            "message": f"Удалено {count} записей"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_class=HTMLResponse)
async def criminal_list(request: Request, db: Session = Depends(get_db)):
    crimes = db.query(CriminalSituation).all()
    omvd_list = db.query(OMVD).all()
    categories = db.query(CrimeCategory).all()
    
    # Преобразуем данные в JSON для JavaScript
    crimes_data = []
    for crime in crimes:
        crimes_data.append({
            'id': crime.id,
            'crime_date': str(crime.crime_date) if crime.crime_date else '',
            'omvd_name': crime.omvd_name or '',
            'crime_category_name': crime.crime_category_name or '',
            'sum_damage': float(crime.sum_damage) if crime.sum_damage else 0
        })
    
    omvd_options = [{'id': o.id, 'name': o.omvd_name} for o in omvd_list]
    category_options = [{'id': c.id, 'name': c.crime_name} for c in categories]
    
    crimes_json = json.dumps(crimes_data, ensure_ascii=False)
    omvd_json = json.dumps(omvd_options, ensure_ascii=False)
    category_json = json.dumps(category_options, ensure_ascii=False)
    
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Криминальная обстановка - HersonDashboard</title>
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
                        <a class="nav-link active" href="/criminal">🔍 Криминальная обстановка</a>
                        <a class="nav-link" href="/military">⚔️ Военные инциденты</a>                        
                    </nav>
                </div>
            </div>
            
            <div class="col-md-10 content">
                <h1 class="mb-4">🔍 Криминальная обстановка</h1>
                
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
                                    <a href="/criminal/download-template" class="btn btn-info">📄 Скачать шаблон</a>
                                    <a href="/criminal/export-pdf" class="btn btn-danger">📄 Экспорт PDF</a>
                                    <button type="button" class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#clearModal">🗑️ Очистить</button>
                                </div>
                            </div>
                            <div id="importResult" class="mt-2" style="display: none;"></div>
                        </form>
                    </div>
                </div>
                
                <!-- Кнопка для открытия модального окна добавления -->
                <div class="mb-3">
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addCrimeModal">
                        ➕ Добавить новое преступление
                    </button>
                </div>

                <!-- Модальное окно добавления преступления -->
                <div class="modal fade" id="addCrimeModal" tabindex="-1" aria-labelledby="addCrimeModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title" id="addCrimeModalLabel">➕ Добавление нового преступления</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                            </div>
                            <div class="modal-body">
                                <form id="crimeFormModal">
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Территориальный орган (ОМВД) *</label>
                                            <input type="text" name="omvd_name" class="form-control" required placeholder="например, ОМВД России «Генический»">
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Категория преступления *</label>
                                            <input type="text" name="crime_category_name" class="form-control" required placeholder="например, Кража с карты/счёта">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Дата преступления *</label>
                                            <input type="date" name="crime_date" class="form-control" required>
                                        </div>
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Пол потерпевшего *</label>
                                            <select name="victim_gender" class="form-select" required>
                                                <option value="">Выберите...</option>
                                                <option value="0">Мужской</option>
                                                <option value="1">Женский</option>
                                            </select>
                                        </div>
                                        <div class="col-md-4 mb-3">
                                            <label class="form-label">Сумма ущерба (руб.)</label>
                                            <input type="number" step="0.01" name="sum_damage" class="form-control" placeholder="0.00">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Место регистрации</label>
                                            <input type="text" name="registration_place" class="form-control">
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Номер регистрации</label>
                                            <input type="number" name="registration_number" class="form-control">
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Дата регистрации</label>
                                            <input type="date" name="registration_date" class="form-control">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Статья УК</label>
                                            <input type="text" name="crime_article" class="form-control" placeholder="ст. 159">
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Тип мошенничества</label>
                                            <input type="text" name="fraud_type" class="form-control">
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Дата рождения потерпевшего</label>
                                            <input type="date" name="victim_birthday" class="form-control">
                                        </div>
                                    </div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" data-bs-dismiss="modal">Отменить</button>
                                <button type="button" class="btn btn-success" id="saveCrimeBtn">Сохранить</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h5>Список преступлений</h5>
                    </div>
                    <div class="card-body">
                        <table id="crimesTable" class="table table-striped">
                            <thead>
                                <tr><th>ID</th><th>Дата</th><th>ОМВД</th><th>Категория</th><th>Ущерб (руб.)</th></tr>
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
        const omvdList = {omvd_json};
        const categoryList = {category_json};
        let crimesData = {crimes_json};
        
        function renderTable() {{
            const tbody = document.querySelector('#crimesTable tbody');
            tbody.innerHTML = '';
            crimesData.forEach(c => {{
                const row = tbody.insertRow();
                row.insertCell(0).innerText = c.id;
                row.insertCell(1).innerText = c.crime_date;
                row.insertCell(2).innerText = c.omvd_name;
                row.insertCell(3).innerText = c.crime_category_name;
                row.insertCell(4).innerText = c.sum_damage.toLocaleString();
            }});
        }}
        
        function loadOmvdSelect() {{
            const select = document.getElementById('omvdModalSelect');
            if (select) {{
                select.innerHTML = '<option value="">Выберите ОМВД...</option>';
                omvdList.forEach(o => {{
                    select.innerHTML += `<option value="${{o.name}}">${{o.name}}</option>`;
                }});
            }}
        }}
        
        function loadCategorySelect() {{
            const select = document.getElementById('categoryModalSelect');
            if (select) {{
                select.innerHTML = '<option value="">Выберите категорию...</option>';
                categoryList.forEach(c => {{
                    select.innerHTML += `<option value="${{c.name}}">${{c.name}}</option>`;
                }});
            }}
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
            const res = await fetch('/criminal/import-excel', {{ method: 'POST', body: formData }});
            const result = await res.json();
            if (res.ok) showResult(`✅ Импортировано: ${{result.imported}}`, 'success');
            else showResult(`❌ ${{result.detail}}`, 'danger');
            setTimeout(() => location.reload(), 2000);
        }};
        
        document.getElementById('confirmClear').onclick = async () => {{
            const res = await fetch('/criminal/clear-all', {{ method: 'POST' }});
            if (res.ok) location.reload();
        }};
        
        document.getElementById('saveCrimeBtn').onclick = async () => {{
            const formData = {{}};
            $('#crimeFormModal').serializeArray().forEach(item => {{
                formData[item.name] = item.value;
            }});
            if (!formData.omvd_name || !formData.crime_category_name || !formData.crime_date || formData.victim_gender === '') {{
                showResult('Пожалуйста, заполните обязательные поля: ОМВД, категория, дата преступления, пол потерпевшего', 'danger');
                return;
            }}
            const res = await fetch('/criminal/add', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(formData)
            }});
            if (res.ok) {{
                $('#addCrimeModal').modal('hide');
                showResult('✅ Запись успешно добавлена', 'success');
                setTimeout(() => location.reload(), 1000);
            }} else {{
                const err = await res.json();
                showResult(`❌ ${{err.detail || 'Ошибка при добавлении'}}`, 'danger');
            }}
        }};
        
        loadOmvdSelect();
        loadCategorySelect();
        renderTable();
        $(document).ready(function() {{
            $('#crimesTable').DataTable({{
                language: {{ url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/ru.json' }}
            }});
        }});
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)