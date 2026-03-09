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
    clicks = Column(Integer, default=0)  # Количество переходов
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания
    last_accessed = Column(DateTime(timezone=True), nullable=True)  # Дата последнего использования
    
    # Время жизни
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Дата истечения
    
    # Информация о пользователе
    user_id = Column(String(100), nullable=True)  # ID пользователя (для зарегистрированных)
    is_active = Column(Boolean, default=True)  # Активна ли ссылка
    
    def is_expired(self):
        """Проверяет, истекла ли ссылка"""
        if self.expires_at:
            return datetime.datetime.now(datetime.timezone.utc) > self.expires_at
        return False
    
    def click(self):
        """Увеличивает счетчик кликов и обновляет last_accessed"""
        self.clicks += 1
        self.last_accessed = func.now()
