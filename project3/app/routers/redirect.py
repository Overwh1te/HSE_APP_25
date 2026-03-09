from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from app import crud
from app.database import get_db
from app.redis_client import get_cached_link, cache_link

router = APIRouter(tags=["redirect"])

@router.get("/{short_code}")
async def root_redirect(
    short_code: str,
    db: Session = Depends(get_db)
):
    # Сначала проверяем кэш
    cached_url = get_cached_link(short_code)
    if cached_url:
        # Обновляем статистику в фоне (упрощенно)
        link = crud.get_link_by_short_code(db, short_code)
        if link:
            crud.increment_clicks(db, link)
        return RedirectResponse(url=cached_url)
    
    # Если нет в кэше - ищем в БД
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.is_expired():
        raise HTTPException(status_code=410, detail="Link has expired")
    
    # Сохраняем в кэш
    cache_link(short_code, link.original_url)
    
    crud.increment_clicks(db, link)
    return RedirectResponse(url=link.original_url)
