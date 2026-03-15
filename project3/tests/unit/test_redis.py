import pytest
from unittest.mock import MagicMock, patch
from app.redis_client import (
    redis_client, cache_link, get_cached_link,
    delete_cached_link, cache_stats, get_cached_stats
)

def test_cache_link(mocker):
    """Тест кэширования ссылки"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    
    cache_link("test123", "https://example.com", ttl=60)
    
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "link:test123"
    assert args[1] == 60

def test_get_cached_link_found(mocker):
    """Тест получения ссылки из кэша (найдено)"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    mock_redis.get.return_value = '{"original_url": "https://example.com"}'
    
    result = get_cached_link("test123")
    
    assert result == "https://example.com"
    mock_redis.get.assert_called_once_with("link:test123")

def test_get_cached_link_not_found(mocker):
    """Тест получения ссылки из кэша (не найдено)"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    mock_redis.get.return_value = None
    
    result = get_cached_link("test123")
    
    assert result is None

def test_delete_cached_link(mocker):
    """Тест удаления из кэша"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    
    delete_cached_link("test123")
    
    mock_redis.delete.assert_called_once_with("link:test123")

def test_cache_stats(mocker):
    """Тест кэширования статистики"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    stats = {"clicks": 5, "original_url": "https://example.com"}
    
    cache_stats("test123", stats, ttl=300)
    
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "stats:test123"
    assert args[1] == 300

def test_get_cached_stats_found(mocker):
    """Тест получения статистики из кэша"""
    mock_redis = mocker.patch('app.redis_client.redis_client')
    mock_redis.get.return_value = '{"clicks": 5, "original_url": "https://example.com"}'
    
    result = get_cached_stats("test123")
    
    assert result["clicks"] == 5
    assert result["original_url"] == "https://example.com"
