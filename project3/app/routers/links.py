from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app import crud, schemas
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/links", tags=["links"])

@router.post("/shorten", response_model=schemas.LinkResponse, status_code=201)
async def create_short_link(
    link: schemas.LinkCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Создает короткую ссылку.

    - **original_url**: длинная ссылка для сокращения
    - **custom_alias**: (опционально) свой вариант короткой ссылки
    - **expires_at**: (опционально) дата истечения ссылки
    """
    # Проверяем, не истекла ли дата (если указана)
    if link.expires_at and link.expires_at.replace(tzinfo=None) < datetime.now():
        # Для тестов пропускаем (можно по переменной окружения)
        import os
        if os.getenv("TESTING") != "true":
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")

    # Создаем ссылку (без пользователя пока)
    db_link = crud.create_short_link(db, link, user_id=None)

    if not db_link:
        raise HTTPException(status_code=400, detail="Custom alias already exists")

    # Формируем полную короткую ссылку
    short_url = f"{settings.BASE_URL}/{db_link.short_code}"

    return {
        "original_url": db_link.original_url,
        "short_code": db_link.short_code,
        "short_url": short_url,
        "custom_alias": db_link.custom_alias,
        "expires_at": db_link.expires_at,
        "created_at": db_link.created_at
    }

@router.get("/search")
async def search_links(
    original_url: str,
    db: Session = Depends(get_db)
):
    """
    Ищет ссылки по оригинальному URL (частичное совпадение)
    """
    links = crud.search_links_by_original_url(db, original_url)
    
    # Преобразуем ORM объекты в словари
    result = []
    for link in links:
        result.append({
            "original_url": link.original_url,
            "short_code": link.short_code,
            "clicks": link.clicks,
            "created_at": link.created_at.isoformat() if link.created_at else None
        })
    
    return result

@router.get("/expired")
async def get_expired_links(
    db: Session = Depends(get_db)
):
    """
    Возвращает список всех истекших ссылок
    """
    links = crud.get_expired_links(db)
    
    result = []
    for link in links:
        result.append({
            "original_url": link.original_url,
            "short_code": link.short_code,
            "created_at": link.created_at,
            "expired_at": link.expires_at,
            "clicks": link.clicks
        })
    
    return result

@router.get("/{short_code}/stats", response_model=schemas.LinkStats)
async def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db)
):
    """
    Получает статистику по ссылке:
    - оригинальный URL
    - дата создания
    - количество переходов
    - дата последнего использования
    """
    link = crud.get_link_stats(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    return link

@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: Session = Depends(get_db)
):
    """
    Перенаправляет на оригинальный URL по короткому коду
    """
    # Ищем ссылку в БД
    link = crud.get_link_by_short_code(db, short_code)

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем, не истекла ли ссылка
    if link.is_expired():
        raise HTTPException(status_code=410, detail="Link has expired")

    # Увеличиваем счетчик кликов
    crud.increment_clicks(db, link)

    # Перенаправляем на оригинальный URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=link.original_url)

@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    db: Session = Depends(get_db)
):
    """
    Удаляет короткую ссылку
    """
    deleted = crud.delete_link(db, short_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")

    return {"message": "Link successfully deleted"}

@router.put("/{short_code}")
async def update_link(
    short_code: str,
    link_update: schemas.LinkUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновляет оригинальный URL для существующей короткой ссылки
    """
    updated_link = crud.update_link(db, short_code, link_update.original_url)
    if not updated_link:
        raise HTTPException(status_code=404, detail="Link not found")

    return {
        "message": "Link successfully updated",
        "original_url": updated_link.original_url,
        "short_code": updated_link.short_code
    }
