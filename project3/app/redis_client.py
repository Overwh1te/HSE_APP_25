import redis
import json
from app.config import settings

# Подключаемся к Redis
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def cache_link(short_code: str, original_url: str, ttl: int = 3600):
    """Сохраняет ссылку в кэше на 1 час"""
    redis_client.setex(
        f"link:{short_code}", 
        ttl, 
        json.dumps({"original_url": original_url})
    )

def get_cached_link(short_code: str):
    """Получает ссылку из кэша"""
    data = redis_client.get(f"link:{short_code}")
    if data:
        return json.loads(data)["original_url"]
    return None

def delete_cached_link(short_code: str):
    """Удаляет ссылку из кэша"""
    redis_client.delete(f"link:{short_code}")

def cache_stats(short_code: str, stats: dict, ttl: int = 300):
    """Кэширует статистику на 5 минут"""
    redis_client.setex(
        f"stats:{short_code}", 
        ttl, 
        json.dumps(stats)
    )

def get_cached_stats(short_code: str):
    """Получает статистику из кэша"""
    data = redis_client.get(f"stats:{short_code}")
    if data:
        return json.loads(data)
    return None
