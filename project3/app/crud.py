from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models, schemas
import random
import string
from datetime import datetime, timezone, timedelta

def generate_short_code(length: int = 6) -> str:
    """Генерирует случайный короткий код"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_short_link(db: Session, link: schemas.LinkCreate, user_id: str = None):
    """
    Создает новую короткую ссылку
    """
    # Генерируем уникальный код
    while True:
        short_code = link.custom_alias if link.custom_alias else generate_short_code()
        # Проверяем, не занят ли код
        db_link = get_link_by_short_code(db, short_code)
        if not db_link:
            break
        if link.custom_alias:
            # Если кастомный alias уже занят - возвращаем ошибку
            return None
    
    # Создаем объект ссылки
    db_link = models.Link(
        original_url=str(link.original_url),  # Преобразуем HttpUrl в строку
        short_code=short_code,
        custom_alias=link.custom_alias,
        user_id=user_id,
        expires_at=link.expires_at
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def get_link_by_short_code(db: Session, short_code: str):
    """Получает ссылку по короткому коду"""
    return db.query(models.Link).filter(
        models.Link.short_code == short_code
    ).first()

def increment_clicks(db: Session, link: models.Link):
    """Увеличивает счетчик кликов и обновляет last_accessed"""
    link.clicks += 1
    link.last_accessed = datetime.now(timezone.utc)
    db.commit()
    db.refresh(link)
    return link

def get_link_stats(db: Session, short_code: str):
    """Получает статистику по ссылке"""
    return db.query(models.Link).filter(
        models.Link.short_code == short_code
    ).first()

def delete_link(db: Session, short_code: str):
    """Удаляет ссылку"""
    link = get_link_by_short_code(db, short_code)
    if link:
        db.delete(link)
        db.commit()
        return True
    return False

def update_link(db: Session, short_code: str, new_url: str):
    """Обновляет оригинальный URL ссылки"""
    link = get_link_by_short_code(db, short_code)
    if link:
        link.original_url = new_url
        db.commit()
        db.refresh(link)
        return link
    return None

def search_links_by_original_url(db: Session, original_url: str):
    """
    Ищет ссылки по оригинальному URL (частичное совпадение)
    """
    return db.query(models.Link).filter(
        models.Link.original_url.ilike(f"%{original_url}%")  # ilike для регистронезависимого поиска
    ).all()

def get_expired_links(db: Session):
    """Возвращает все истекшие ссылки"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return db.query(models.Link).filter(
        models.Link.expires_at.isnot(None),
        models.Link.expires_at < now
    ).all()

def delete_old_unused_links(db: Session, days: int = 30):
    """
    Удаляет ссылки, которые не использовались больше N дней
    и у которых нет кастомного alias (для простоты)
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Находим ссылки для удаления
    old_links = db.query(models.Link).filter(
        models.Link.last_accessed.isnot(None),
        models.Link.last_accessed < cutoff_date,
        models.Link.custom_alias.is_(None)  # Не удаляем кастомные
    ).all()
    
    deleted_count = len(old_links)
    for link in old_links:
        db.delete(link)
    
    db.commit()
    return deleted_count
