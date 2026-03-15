import pytest
from app.database import get_db, engine

def test_get_db():
    """Тест получения сессии БД"""
    db_gen = get_db()
    db = next(db_gen)
    
    assert db is not None
    assert db.bind == engine
    
    # Закрываем сессию
    try:
        next(db_gen)
    except StopIteration:
        pass  # Ожидаемо

def test_engine_creation():
    """Тест создания engine"""
    assert engine is not None
    assert engine.url.database.endswith('test.db')  # Для тестовой БД
