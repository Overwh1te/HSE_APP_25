import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["TESTING"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.config import settings
import redis
from unittest.mock import patch

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_REDIS_URL = "redis://localhost:6379/1"

def override_get_db():
    """Переопределяем зависимость get_db для тестов"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    """Клиент для тестирования API"""
    # таблицы в тестовой БД
    Base.metadata.create_all(bind=engine)
    
    # переопределение зависимости
    app.dependency_overrides[get_db] = override_get_db
    
    # тестовый клиент
    with TestClient(app) as test_client:
        yield test_client
    
        Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture
def test_db():
    """Фикстура для прямой работы с БД в тестах"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_redis(mocker):
    """Мокаем Redis для юнит-тестов"""
    mock = mocker.patch('app.redis_client.redis_client')
    mock.get.return_value = None
    return mock

@pytest.fixture(autouse=True)
def mock_redis_for_all_tests():
    """Автоматически мокает Redis для всех тестов"""
    with patch('app.redis_client.redis_client') as mock:
        mock.get.return_value = None
        yield mock

@pytest.fixture(autouse=True)
def clean_db_between_tests():
    """Очищает БД перед каждым тестом"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
