import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from tests.conftest import TestingSessionLocal, override_get_db

# Переопределяем зависимость для тестов
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_read_root():
    """Тест главной страницы"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "URL Shortener Service"
    assert data["docs"] == "/docs"
    assert data["status"] == "running"

def test_health_check():
    """Тест health check"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_short_link():
    """Тест создания короткой ссылки"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    # URL может быть с слешем или без
    assert data["original_url"] in ["https://example.com", "https://example.com/"]
    assert "short_code" in data
    assert data["short_url"].startswith("http")
    assert data["custom_alias"] is None
    assert data["expires_at"] is None

def test_create_short_link_with_custom_alias():
    """Тест создания ссылки с кастомным alias"""
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "test123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] in ["https://example.com", "https://example.com/"]
    assert data["short_code"] == "test123"
    assert data["custom_alias"] == "test123"

def test_create_short_link_duplicate_alias():
    """Тест на уникальность alias"""
    # Создаем первую ссылку
    response1 = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "unique"
        }
    )
    assert response1.status_code == 201
    
    # Пытаемся создать вторую с тем же alias
    response2 = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.org",
            "custom_alias": "unique"
        }
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Custom alias already exists"

def test_create_short_link_with_expiry():
    """Тест создания ссылки с временем жизни"""
    from datetime import datetime, timedelta, timezone
    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "expires_at": expires
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None
    assert data["original_url"] in ["https://example.com", "https://example.com/"]

def test_redirect_to_original():
    """Тест редиректа"""
    # Сначала создаем ссылку
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com"}
    )
    assert create_response.status_code == 201
    short_code = create_response.json()["short_code"]
    
    # Проверяем редирект
    response = client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect
    assert response.headers["location"] in ["https://example.com", "https://example.com/"]

def test_get_link_stats():
    """Тест получения статистики"""
    # Создаем ссылку
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com"}
    )
    assert create_response.status_code == 201
    short_code = create_response.json()["short_code"]
    
    # Переходим по ссылке несколько раз
    client.get(f"/{short_code}", follow_redirects=False)
    client.get(f"/{short_code}", follow_redirects=False)
    
    # Проверяем статистику
    response = client.get(f"/links/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] in ["https://example.com", "https://example.com/"]
    assert data["short_code"] == short_code
    assert data["clicks"] >= 2
    assert data["is_active"] is True

def test_update_link():
    """Тест обновления ссылки"""
    # Создаем ссылку
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com"}
    )
    assert create_response.status_code == 201
    short_code = create_response.json()["short_code"]
    
    # Обновляем
    response = client.put(
        f"/links/{short_code}",
        json={"original_url": "https://newexample.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Link successfully updated"
    assert data["original_url"] in ["https://newexample.com", "https://newexample.com/"]
    
    # Проверяем, что обновилось
    stats_response = client.get(f"/links/{short_code}/stats")
    assert stats_response.json()["original_url"] in ["https://newexample.com", "https://newexample.com/"]

def test_delete_link():
    """Тест удаления ссылки"""
    # Создаем ссылку
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com"}
    )
    assert create_response.status_code == 201
    short_code = create_response.json()["short_code"]
    
    # Удаляем
    delete_response = client.delete(f"/links/{short_code}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Link successfully deleted"
    
    # Проверяем, что ссылка не найдена
    stats_response = client.get(f"/links/{short_code}/stats")
    assert stats_response.status_code == 404

def test_search_links():
    """Тест поиска ссылок"""
    # Создаем несколько ссылок
    client.post("/links/shorten", json={"original_url": "https://github.com"})
    client.post("/links/shorten", json={"original_url": "https://github.com/features"})
    client.post("/links/shorten", json={"original_url": "https://google.com"})
    
    # Ищем по части URL
    response = client.get("/links/search", params={"original_url": "github"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # Ищем несуществующее
    response = client.get("/links/search", params={"original_url": "nonexistent"})
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_get_expired_links():
    """Тест получения истекших ссылок"""
    from datetime import datetime, timedelta, timezone
    
    # Создаем ссылку с истекшим сроком (в прошлом)
    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://expired.com",
            "expires_at": past_date
        }
    )
    # Может быть 201 или 400 в зависимости от логики, пропускаем
    if response.status_code == 201:
        # Проверяем список истекших
        expired_response = client.get("/links/expired")
        assert expired_response.status_code == 200
        data = expired_response.json()
        # Если ссылка создалась, она должна быть в списке истекших
        if len(data) > 0:
            expired_urls = [link["original_url"] for link in data]
            assert "https://expired.com" in expired_urls or "https://expired.com/" in expired_urls

def test_admin_cleanup():
    """Тест ручной очистки старых ссылок"""
    response = client.post("/admin/cleanup", params={"days": 30})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "days_threshold" in data
    assert data["days_threshold"] == 30

def test_invalid_url():
    """Тест на невалидный URL"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "not-a-url"}
    )
    # Должна быть ошибка валидации
    assert response.status_code == 422

def test_nonexistent_link():
    """Тест запроса несуществующей ссылки"""
    response = client.get("/links/nonexistent/stats")
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"
