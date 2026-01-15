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


def get_work_day_for_time(dt: datetime) -> datetime:
    """
    Определяет, к какому рабочему дню относится данное время.
    Если время после полуночи (00:00-05:59), это может быть продолжение предыдущего дня.
    """
    # Если время между 00:00 и 05:59, проверяем, не продолжение ли это предыдущего дня
    if dt.hour < 6:
        # Получаем часы работы для предыдущего дня
        prev_day = dt - timedelta(days=1)
        prev_open, prev_close = get_working_hours(prev_day)
        
        # Если предыдущий день работал после полуночи и текущее время в пределах работы
        if prev_close.hour < prev_open.hour and dt.hour < prev_close.hour:
            return prev_day
    
    return dt


def get_available_dates() -> List[datetime]:
    """Получение списка доступных дат для бронирования"""
    dates = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tournament_date = datetime(2025, 1, 25).date()  # Дата турнира
    
    for i in range(settings.MAX_BOOKING_DAYS):
        date = today + timedelta(days=i)
        # Пропускаем дату турнира
        if date.date() != tournament_date:
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
    
    # Если закрытие после полуночи - работаем через полночь
    if close_time.hour < open_time.hour:
        # === ЧАСТЬ 1: Слоты от открытия до полуночи ===
        midnight = (date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current < midnight:
            if current > now:
                times.append(current)
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
        
        # === ЧАСТЬ 2: Слоты после полуночи ===
        # Начинаем с 00:00 следующего дня
        current = midnight
        
        # Конец - время закрытия (например, 02:00 или 04:00)
        close_datetime = midnight.replace(
            hour=close_time.hour,
            minute=close_time.minute
        )
        
        # Оставляем возможность забронировать минимум 1 час
        end_for_booking = close_datetime - timedelta(hours=settings.MIN_BOOKING_HOURS)
        
        while current <= end_for_booking:
            if current > now:
                times.append(current)
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
    else:
        # === Закрытие в тот же день (не используется в нашем случае) ===
        end = date.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
        
        end_for_booking = end - timedelta(hours=settings.MIN_BOOKING_HOURS)
        
        while current <= end_for_booking:
            if current > now:
                times.append(current)
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
    
    return times


def is_valid_booking_time(start_time: datetime, duration_hours: int) -> bool:
    """
    Проверка, что бронирование не выходит за часы работы
    """
    end_time = start_time + timedelta(hours=duration_hours)
    
    # Определяем день работы (тот, в который открылись)
    # Если текущее время после полуночи и до времени открытия - это продолжение предыдущего дня
    open_time, close_time = get_working_hours(start_time)
    
    # Если слот после полуночи (00:00-06:00) и закрытие тоже после полуночи
    if start_time.hour < 6 and close_time.hour < open_time.hour:
        # Это слот следующего дня после открытия
        # Проверяем относительно времени закрытия
        close_datetime = start_time.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
        
        # Если время закрытия меньше времени начала слота, 
        # значит мы уже за пределами работы
        if close_datetime < start_time:
            return False
        
        return end_time <= close_datetime
    
    # Время открытия в формате datetime для сравнения
    open_datetime = start_time.replace(
        hour=open_time.hour,
        minute=open_time.minute,
        second=0,
        microsecond=0
    )
    
    # Время закрытия в формате datetime
    if close_time.hour < open_time.hour:
        # Закрытие после полуночи следующего дня
        close_datetime = (start_time + timedelta(days=1)).replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    else:
        # Закрытие в тот же день
        close_datetime = start_time.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
    
    # Проверяем, что:
    # 1. Начало брони не раньше открытия (или это слот после полуночи)
    # 2. Конец брони не позже закрытия
    is_after_midnight = start_time.hour < 6  # Считаем что слоты после полуночи это 00:00-05:59
    
    if is_after_midnight and close_time.hour < open_time.hour:
        # Слот после полуночи в режиме работы через полночь - всегда валидный по времени начала
        return end_time <= close_datetime
    
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
