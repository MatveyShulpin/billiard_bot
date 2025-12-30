"""
Утилиты для работы со временем и расписанием
"""
from datetime import datetime, time, timedelta
from typing import List, Tuple
from config import settings


def get_working_hours(date: datetime) -> Tuple[time, time]:
    """
    Получение часов работы для конкретной даты
    Возвращает (время открытия, время закрытия)
    """
    # Пятница (4) и Суббота (5)
    if date.weekday() in [4, 5]:
        return settings.WEEKEND_OPEN, settings.WEEKEND_CLOSE
    else:
        return settings.WEEKDAY_OPEN, settings.WEEKDAY_CLOSE


def get_available_dates() -> List[datetime]:
    """Получение списка доступных дат для бронирования"""
    dates = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(settings.MAX_BOOKING_DAYS):
        date = today + timedelta(days=i)
        dates.append(date)
    
    return dates


def get_available_times(date: datetime) -> List[datetime]:
    """
    Получение списка доступных временных слотов для даты
    """
    open_time, close_time = get_working_hours(date)
    times = []
    now = datetime.now()
    
    # Начало работы в выбранную дату
    current = date.replace(
        hour=open_time.hour,
        minute=open_time.minute,
        second=0,
        microsecond=0
    )
    
    # Конец работы (может быть на следующий день)
    if close_time.hour < open_time.hour:
        # Закрытие после полуночи
        end = (date + timedelta(days=1)).replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    else:
        end = date.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    
    # Резервируем минимум 1 час до закрытия для возможности бронирования
    # Вычитаем MIN_BOOKING_HOURS, чтобы нельзя было начать бронь слишком близко к закрытию
    end_for_booking = end - timedelta(hours=settings.MIN_BOOKING_HOURS)
    
    # Генерация слотов
    while current <= end_for_booking:
        # Добавляем только будущие слоты
        if current > now:
            times.append(current)
        current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
    
    return times


def is_valid_booking_time(start_time: datetime, duration_hours: int) -> bool:
    """
    Проверка, что бронирование не выходит за часы работы
    """
    end_time = start_time + timedelta(hours=duration_hours)
    open_time, close_time = get_working_hours(start_time)
    
    # Время открытия в формате datetime для сравнения
    open_datetime = start_time.replace(
        hour=open_time.hour,
        minute=open_time.minute,
        second=0,
        microsecond=0
    )
    
    # Время закрытия в формате datetime
    if close_time.hour < open_time.hour:
        # Закрытие после полуночи
        close_datetime = (start_time + timedelta(days=1)).replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    else:
        close_datetime = start_time.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    
    # Проверяем, что:
    # 1. Начало брони не раньше открытия
    # 2. Конец брони не позже закрытия
    return start_time >= open_datetime and end_time <= close_datetime


def format_datetime(dt: datetime) -> str:
    """Форматирование datetime для отображения"""
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """Форматирование даты"""
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    weekday = weekdays[dt.weekday()]
    
    today = datetime.now().date()
    if dt.date() == today:
        return f"Сегодня ({weekday})"
    elif dt.date() == today + timedelta(days=1):
        return f"Завтра ({weekday})"
    else:
        return f"{dt.strftime('%d.%m')} ({weekday})"


def format_time(dt: datetime) -> str:
    """Форматирование времени"""
    return dt.strftime("%H:%M")
