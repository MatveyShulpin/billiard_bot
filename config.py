"""
Конфигурация проекта
"""
import os
from dataclasses import dataclass
from typing import List
from datetime import time


@dataclass
class Settings:
    """Настройки приложения"""
    # Telegram
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_IDS: List[int] = None
    SUPPORT_ADMIN_IDS: List[int] = None
    
    # База данных
    DB_PATH: str = os.getenv('DB_PATH', 'data/billiard_bot.db')
    
    # Бизнес-правила
    TABLES_COUNT: int = 3
    BOOKING_STEP_MINUTES: int = 60
    MAX_BOOKING_DAYS: int = 7
    MIN_BOOKING_HOURS: int = 1
    MAX_BOOKING_HOURS: int = 4
    HOLD_TIMEOUT_MINUTES: int = 10
    
    # Режим работы (часы)
    WEEKDAY_OPEN: time = time(16, 0)   # Пн-Чт
    WEEKDAY_CLOSE: time = time(2, 0)   # следующего дня
    FRIDAY_OPEN: time = time(16, 0)    # Пт
    FRIDAY_CLOSE: time = time(4, 0)    # следующего дня
    WEEKEND_OPEN: time = time(15, 0)   # Сб
    WEEKEND_CLOSE: time = time(4, 0)   # следующего дня
    SUNDAY_OPEN: time = time(15, 0)    # Вс
    SUNDAY_CLOSE: time = time(2, 0)    # следующего дня
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")
        
        # Парсинг ADMIN_IDS из переменной окружения
        if self.ADMIN_IDS is None:
            admin_ids_str = os.getenv('ADMIN_IDS', '')
            if admin_ids_str:
                self.ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',')]
            else:
                self.ADMIN_IDS = []
        
        # Парсинг SUPPORT_ADMIN_IDS из переменной окружения
        if self.SUPPORT_ADMIN_IDS is None:
            support_admin_ids_str = os.getenv('SUPPORT_ADMIN_IDS', '')
            if support_admin_ids_str:
                self.SUPPORT_ADMIN_IDS = [int(id.strip()) for id in support_admin_ids_str.split(',')]
            else:
                self.SUPPORT_ADMIN_IDS = []
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.ADMIN_IDS


# Глобальный экземпляр настроек
settings = Settings()
