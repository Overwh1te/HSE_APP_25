import pytest
from datetime import datetime, timedelta, timezone
from app import models

def test_link_model_creation():
    """Тест создания модели Link"""
    link = models.Link(
        original_url="https://example.com",
        short_code="abc123"
    )

    assert link.original_url == "https://example.com"
    assert link.short_code == "abc123"
    assert link.clicks is None or link.clicks == 0
    assert link.custom_alias is None
    assert link.is_active is True

def test_link_is_expired_method():
    """Тест метода is_expired()"""
    # Ссылка без срока действия
    link = models.Link(
        original_url="https://example.com",
        short_code="abc123",
        expires_at=None
    )
    assert link.is_expired() is False
    
    # Ссылка с истекшим сроком
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    link = models.Link(
        original_url="https://example.com",
        short_code="abc123",
        expires_at=past_date
    )
    assert link.is_expired() is True
    
    # Ссылка с будущим сроком
    future_date = datetime.now(timezone.utc) + timedelta(days=1)
    link = models.Link(
        original_url="https://example.com",
        short_code="abc123",
        expires_at=future_date
    )
    assert link.is_expired() is False

def test_link_click_method():
    """Тест метода click()"""
    link = models.Link(
        original_url="https://example.com",
        short_code="abc123"
    )
    
    initial_clicks = link.clicks if link.clicks is not None else 0
    
    link.click()
    
    # После click() clicks должно увеличиться на 1
    assert link.clicks == initial_clicks + 1
    assert link.last_accessed is not None
