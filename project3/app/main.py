from fastapi import FastAPI
from app.config import settings
from app.database import engine, SessionLocal
from app import models, crud
from app.routers import redirect, links
from app.tasks import start_scheduler
import atexit

# Создаем таблицы в базе данных
models.Base.metadata.create_all(bind=engine)

# Запускаем планировщик фоновых задач
scheduler = start_scheduler()
# Останавливаем планировщик при завершении приложения
atexit.register(lambda: scheduler.shutdown())

app = FastAPI(
    title="URL Shortener Service",
    description="Сервис для сокращения ссылок",
    version="1.0.0"
)

# Основные эндпоинты
@app.get("/")
def read_root():
    return {
        "message": "URL Shortener Service",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Эндпоинт для ручной очистки старых ссылок
@app.post("/admin/cleanup")
async def manual_cleanup(days: int = 30):
    """
    Ручной запуск очистки старых ссылок
    Удаляет ссылки, которые не использовались больше указанного количества дней
    """
    db = SessionLocal()
    try:
        deleted = crud.delete_old_unused_links(db, days)
        return {
            "message": f"Cleaned up {deleted} old links",
            "days_threshold": days
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

app.include_router(links.router)
app.include_router(redirect.router)
