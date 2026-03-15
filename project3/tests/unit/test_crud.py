import pytest
from datetime import datetime, timedelta, timezone
from app import crud, models, schemas
from sqlalchemy.orm import Session

def test_generate_short_code():
    """Тест генерации короткого кода"""
    code1 = crud.generate_short_code()
    code2 = crud.generate_short_code()
    
    # Проверяем длину (по умолчанию 6)
    assert len(code1) == 6
    assert len(code2) == 6
    
    # Проверяем уникальность
    assert code1 != code2
    
    # Проверяем, что код состоит только из допустимых символов
    import string
    allowed_chars = string.ascii_letters + string.digits
    assert all(c in allowed_chars for c in code1)

def test_generate_short_code_custom_length():
    """Тест генерации кода с произвольной длиной"""
    code = crud.generate_short_code(length=8)
    assert len(code) == 8
    
    code = crud.generate_short_code(length=4)
    assert len(code) == 4

def test_create_short_link(test_db: Session, mock_redis):
    """Тест создания короткой ссылки"""
    link_data = schemas.LinkCreate(
        original_url="https://example.com"
    )

    link = crud.create_short_link(test_db, link_data)

    assert link is not None
    assert link.original_url in ["https://example.com", "https://example.com/"]
    assert link.short_code is not None
    assert len(link.short_code) == 6
    assert link.clicks == 0
    assert link.custom_alias is None

def test_create_short_link_with_custom_alias(test_db: Session, mock_redis):
    """Тест создания ссылки с кастомным alias"""
    link_data = schemas.LinkCreate(
        original_url="https://example.com",
        custom_alias="test123"
    )

    link = crud.create_short_link(test_db, link_data)

    assert link is not None
    assert link.original_url in ["https://example.com", "https://example.com/"]
    assert link.short_code == "test123"
    assert link.custom_alias == "test123"

def test_create_short_link_duplicate_alias(test_db: Session, mock_redis):
    """Тест на уникальность кастомного alias"""
    # Создаем первую ссылку
    link_data1 = schemas.LinkCreate(
        original_url="https://example1.com",
        custom_alias="unique"
    )
    crud.create_short_link(test_db, link_data1)
    
    # Пытаемся создать вторую с тем же alias
    link_data2 = schemas.LinkCreate(
        original_url="https://example2.com",
        custom_alias="unique"
    )
    link2 = crud.create_short_link(test_db, link_data2)
    
    assert link2 is None  # Должно вернуть None при дубликате

def test_get_link_by_short_code(test_db: Session, mock_redis):
    """Тест получения ссылки по короткому коду"""
    # Создаем ссылку
    link_data = schemas.LinkCreate(original_url="https://example.com")
    created = crud.create_short_link(test_db, link_data)

    # Ищем по коду
    found = crud.get_link_by_short_code(test_db, created.short_code)

    assert found is not None
    assert found.id == created.id
    assert found.original_url in ["https://example.com", "https://example.com/"]
    
    # Ищем несуществующий код
    not_found = crud.get_link_by_short_code(test_db, "nonexistent")
    assert not_found is None
    
    # Ищем несуществующий код
    not_found = crud.get_link_by_short_code(test_db, "nonexistent")
    assert not_found is None

def test_increment_clicks(test_db: Session, mock_redis):
    """Тест увеличения счетчика кликов"""
    # Создаем ссылку
    link_data = schemas.LinkCreate(original_url="https://example.com")
    link = crud.create_short_link(test_db, link_data)
    
    assert link.clicks == 0
    assert link.last_accessed is None
    
    # Увеличиваем счетчик
    updated = crud.increment_clicks(test_db, link)
    
    assert updated.clicks == 1
    assert updated.last_accessed is not None

def test_update_link(test_db: Session, mock_redis):
    """Тест обновления ссылки"""
    # Создаем ссылку
    link_data = schemas.LinkCreate(original_url="https://example.com")
    link = crud.create_short_link(test_db, link_data)
    
    # Обновляем URL
    updated = crud.update_link(test_db, link.short_code, "https://newexample.com")
    
    assert updated is not None
    assert updated.original_url == "https://newexample.com"
    
    # Пытаемся обновить несуществующую ссылку
    not_updated = crud.update_link(test_db, "nonexistent", "https://test.com")
    assert not_updated is None

def test_delete_link(test_db: Session, mock_redis):
    """Тест удаления ссылки"""
    # Создаем ссылку
    link_data = schemas.LinkCreate(original_url="https://example.com")
    link = crud.create_short_link(test_db, link_data)
    
    # Удаляем
    deleted = crud.delete_link(test_db, link.short_code)
    assert deleted is True
    
    # Проверяем, что ссылки больше нет
    found = crud.get_link_by_short_code(test_db, link.short_code)
    assert found is None
    
    # Пытаемся удалить несуществующую
    not_deleted = crud.delete_link(test_db, "nonexistent")
    assert not_deleted is False

def test_search_links_by_original_url(test_db: Session, mock_redis):
    """Тест поиска ссылок по оригинальному URL"""
    # Создаем несколько ссылок
    crud.create_short_link(test_db, schemas.LinkCreate(original_url="https://github.com"))
    crud.create_short_link(test_db, schemas.LinkCreate(original_url="https://github.com/features"))
    crud.create_short_link(test_db, schemas.LinkCreate(original_url="https://google.com"))
    
    # Ищем все ссылки с github
    results = crud.search_links_by_original_url(test_db, "github")
    assert len(results) == 2
    
    # Ищем google
    results = crud.search_links_by_original_url(test_db, "google")
    assert len(results) == 1
    
    # Ищем несуществующее
    results = crud.search_links_by_original_url(test_db, "nonexistent")
    assert len(results) == 0

def test_link_expired(test_db: Session, mock_redis):
    """Тест проверки истечения срока ссылки"""
    from datetime import datetime, timedelta, timezone
    
    # Создаем ссылку с истечением через 1 секунду
    expires = datetime.now(timezone.utc) + timedelta(seconds=1)
    link_data = schemas.LinkCreate(
        original_url="https://example.com",
        expires_at=expires
    )
    link = crud.create_short_link(test_db, link_data)
    
    # Сразу не истекла
    assert link.is_expired() is False
    
    # "Ждем" 2 секунды (в тесте просто создаем новую дату)
    import time
    time.sleep(2)
    
    # Проверяем снова (нужно перезапросить из БД)
    link = crud.get_link_by_short_code(test_db, link.short_code)
    assert link.is_expired() is True
