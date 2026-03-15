from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional

# Базовые схемы
class LinkBase(BaseModel):
    original_url: str

# Схема для создания ссылки
class LinkCreate(LinkBase):
    original_url: HttpUrl
    custom_alias: Optional[str] = Field(None, min_length=2, max_length=50)
    expires_at: Optional[datetime] = Field(None)

# Схема для ответа при создании
class LinkResponse(LinkBase):
    short_code: str
    short_url: str = Field(..., description="Полная короткая ссылка")
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Схема для статистики
class LinkStats(LinkBase):
    short_code: str
    clicks: int
    created_at: datetime
    last_accessed: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    
    class Config:
        from_attributes = True

# Схема для обновления ссылки
class LinkUpdate(BaseModel):
    original_url: str

# Схема для поиска
class LinkSearch(BaseModel):
    original_url: str
    short_code: str
    clicks: int
    created_at: datetime
    
    class Config:
        from_attributes = True
