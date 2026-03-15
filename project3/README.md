# URL Shortener Service

Сервис для сокращения ссылок. Позволяет создавать короткие ссылки, отслеживать статистику переходов, устанавливать время жизни ссылок и многое другое.

## Технологии

- **FastAPI** - веб-фреймворк
- **PostgreSQL** - основная база данных
- **Redis** - кэширование популярных ссылок
- **Docker** + **docker-compose** - контейнеризация
- **SQLAlchemy** - ORM для работы с БД
- **APScheduler** - фоновые задачи

## Функционал

### Обязательные функции:
- ✅ Создание короткой ссылки
- ✅ Редирект по короткой ссылке
- ✅ Удаление ссылки
- ✅ Обновление ссылки (изменение оригинального URL)
- ✅ Статистика по ссылке (количество переходов, дата создания, последнее использование)
- ✅ Кастомные alias (свои варианты коротких ссылок)
- ✅ Поиск ссылок по оригинальному URL
- ✅ Время жизни ссылки (автоматическое удаление после истечения)

### Дополнительные функции:
- ✅ Просмотр всех истекших ссылок
- ✅ Автоматическая очистка старых неиспользуемых ссылок (каждый день в 3:00)
- ✅ Ручной запуск очистки через `/admin/cleanup`
- ✅ Кэширование популярных ссылок в Redis

## Запуск проекта

### Запуск без Docker

```
# Клонировать репозиторий
git clone https://github.com/Overwh1te/HSE_APP_25.git
cd HSE_APP_25/project3
```
```
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```
```
# Установить зависимости
pip install -r requirements.txt
```
```
# Настроить переменные окружения (создать .env файл)
echo "DATABASE_URL=postgresql://user:password@localhost:5432/urlshortener" > .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env
echo "BASE_URL=http://localhost:8000" >> .env
```
```
# Запустить сервер
python run.py
```

### Запуск через Docker
```
# Запустить все контейнеры
docker-compose up -d --build
```
```
# Посмотреть логи
docker-compose logs -f app
```
```
# Остановить контейнеры
docker-compose down
```
После запуска сервис будет доступен по адресу: http://localhost:8000 <br>
Документация Swagger: http://localhost:8000/docs

## API Эндпоинты

### 1. Создание короткой ссылки
```
POST /links/shorten
Content-Type: application/json

{
    "original_url": "https://example.com/very/long/url",
    "custom_alias": "myalias",        # опционально
    "expires_at": "2025-12-31T23:59:59"  # опционально
}
```
Ответ:
```
{
    "original_url": "https://example.com/very/long/url",
    "short_code": "abc123",
    "short_url": "http://localhost:8000/abc123",
    "custom_alias": "myalias",
    "expires_at": "2025-12-31T23:59:59",
    "created_at": "2024-01-01T12:00:00"
}
```

### 2. Редирект по короткой ссылке
```
GET /{short_code}
# Перенаправляет на оригинальный URL
```

### 3. Получение статистики
```
GET /links/{short_code}/stats
```
Ответ:
```
{
    "original_url": "https://example.com/very/long/url",
    "short_code": "abc123",
    "clicks": 42,
    "created_at": "2024-01-01T12:00:00",
    "last_accessed": "2024-01-02T15:30:00",
    "expires_at": null,
    "is_active": true
}
```

### 4. Обновление ссылки
```
PUT /links/{short_code}
Content-Type: application/json

{
    "original_url": "https://newexample.com"
}
```

### 5. Удаление ссылки
```
DELETE /links/{short_code}
```

### 6. Поиск ссылок по оригинальному URL
```
GET /links/search?original_url=example
```
Ответ:
```
[
    {
        "original_url": "https://example.com/page1",
        "short_code": "abc123",
        "clicks": 10,
        "created_at": "2024-01-01T12:00:00"
    },
    {
        "original_url": "https://example.com/page2",
        "short_code": "def456",
        "clicks": 5,
        "created_at": "2024-01-02T12:00:00"
    }
]
```

### 7. Просмотр истекших ссылок
```
GET /links/expired
```

### 8. Ручная очистка старых ссылок
```
POST /admin/cleanup?days=30
# Удаляет ссылки, не использовавшиеся более 30 дней
```

## Структура базы данных

### Таблица `links`

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Первичный ключ |
| original_url | Text | Оригинальная длинная ссылка |
| short_code | String(50) | Уникальный короткий код |
| custom_alias | String(50) | Кастомный alias (если есть) |
| clicks | Integer | Количество переходов |
| created_at | DateTime | Дата создания |
| last_accessed | DateTime | Дата последнего использования |
| expires_at | DateTime | Дата истечения |
| user_id | String(100) | ID пользователя (для будущей регистрации) |
| is_active | Boolean | Активна ли ссылка |

## Кэширование Redis

- **Ключ:** `link:{short_code}`
- **Значение:** JSON с оригинальным URL
- **Время жизни:** 1 час
- **Очистка кэша:** при обновлении или удалении ссылки

## Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| DATABASE_URL | Подключение к PostgreSQL | postgresql://user:password@db:5432/urlshortener |
| REDIS_URL | Подключение к Redis | redis://redis:6379/0 |
| BASE_URL | Базовый URL сервиса | http://localhost:8000 |

## Примеры использования

### Создание ссылки с кастомным alias
```
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://google.com", "custom_alias": "google"}'
```

### Переход по короткой ссылке
```
curl -v http://localhost:8000/google
```

### Поиск всех ссылок на GitHub
```
curl "http://localhost:8000/links/search?original_url=github"
```

### Запуск очистки старых ссылок
```
curl -X POST "http://localhost:8000/admin/cleanup?days=30"
```

## Зависимости
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
python-dotenv==1.0.0
pydantic-settings==2.1.0
apscheduler==3.10.4

pytest==8.0.0
httpx==0.27.0
pytest-cov==5.0.0
locust==2.24.0
pytest-mock==3.12.0
```

# Тестирование

## Запуск всех тестов
```bash
python -m pytest tests/ -v
```

## Проверка покрытия кода
```
python -m pytest tests/ --cov=app --cov-report=term --cov-report=html
```

## Покрытие кода тестами

**Текущее покрытие: 93%**

### Детали по файлам:
| Файл | Покрытие |
|------|----------|
| app/crud.py | 98% |
| app/main.py | 93% |
| app/models.py | 97% |
| app/routers/links.py | 82% |
| app/routers/redirect.py | 74% |
| **Общее** | **93%** |
