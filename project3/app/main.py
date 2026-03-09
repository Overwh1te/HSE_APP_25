from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title="URL Shortener Service",
    description="Сервис для сокращения ссылок",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "URL Shortener Service",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/config-test")
def test_config():
    return {
        "database_url": settings.DATABASE_URL,
        "redis_url": settings.REDIS_URL,
        "base_url": settings.BASE_URL
    }
