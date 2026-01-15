"""
Модели данных для работы с БД
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Table:
    """Модель стола"""
    id: int
    name: str
    is_active: bool = True


@dataclass
class Booking:
    """Модель бронирования"""
    id: Optional[int]
    user_id: int
    username: Optional[str]
    table_id: int  # Теперь обязательный (всегда конкретный стол)
    start_time: datetime
    end_time: datetime
    phone: str
    created_at: datetime
    status: str = 'active'  # active, cancelled
    
    @property
    def duration_hours(self) -> int:
        """Длительность брони в часах"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 3600)


@dataclass
class Hold:
    """Модель временного удержания слота"""
    id: Optional[int]
    user_id: int
    table_id: int  # Теперь обязательный (всегда конкретный стол)
    start_time: datetime
    end_time: datetime
    created_at: datetime
    expires_at: datetime


@dataclass
class TournamentRegistration:
    """Модель регистрации на турнир"""
    id: Optional[int]
    user_id: int
    username: Optional[str]
    full_name: str
    phone: str
    created_at: datetime
    status: str = 'active'  # active, cancelled
