from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import criminal, military, dashboard
import os

app = FastAPI(title="HersonDashboard", description="Оперативная сводка Херсонской области")

# Подключаем статические файлы
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Подключаем маршруты
app.include_router(dashboard.router, prefix="", tags=["Dashboard"])
app.include_router(criminal.router, prefix="/criminal", tags=["Criminal"])
app.include_router(military.router, prefix="/military", tags=["Military"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": "HersonDashboard"}