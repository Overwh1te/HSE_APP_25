from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base
import datetime

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(Text, nullable=False)  # Оригинальная длинная ссылка
    short_code = Column(String(50), unique=True, index=True, nullable=False)  # Короткий код
    custom_alias = Column(String(50), unique=True, nullable=True)  # Кастомный alias (если есть)
    
    # Статистика
    clicks = Column(Integer, default=0, nullable=False)  # Количество переходов
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания
    last_accessed = Column(DateTime(timezone=True), nullable=True)  # Дата последнего использования
    
    # Время жизни
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Дата истечения
    
    # Информация о пользователе
    user_id = Column(String(100), nullable=True)  # ID пользователя (для зарегистрированных)
    is_active = Column(Boolean, default=True, nullable=False)  # Активна ли ссылка
    
    def __init__(self, **kwargs):
        """Инициализатор для установки значений по умолчанию"""
        super(Link, self).__init__(**kwargs)
        if self.clicks is None:
            self.clicks = 0
        if self.is_active is None:
            self.is_active = True
    
    def is_expired(self):
        """Проверяет, истекла ли ссылка"""
        if self.expires_at:
            # Если expires_at без часового пояса, делаем его aware
            if self.expires_at.tzinfo is None:
                from datetime import timezone
                expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at_aware = self.expires_at
            
            now = datetime.datetime.now(datetime.timezone.utc)
            return now > expires_at_aware
        return False
    
    def click(self):
        """Увеличивает счетчик кликов и обновляет last_accessed"""
        if self.clicks is None:
            self.clicks = 0
        self.clicks += 1
        self.last_accessed = datetime.datetime.now(datetime.timezone.utc)
