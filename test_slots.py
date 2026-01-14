"""
Скрипт для тестирования генерации временных слотов
Запустите: python test_slots.py
"""
from datetime import datetime, timedelta, time

# Имитация настроек
class Settings:
    BOOKING_STEP_MINUTES = 60
    MIN_BOOKING_HOURS = 1
    WEEKDAY_OPEN = time(16, 0)
    WEEKDAY_CLOSE = time(2, 0)
    WEEKEND_OPEN = time(16, 0)
    WEEKEND_CLOSE = time(4, 0)

settings = Settings()

def get_working_hours(date):
    """Получение часов работы"""
    if date.weekday() in [4, 5]:  # Пт-Сб
        return settings.WEEKEND_OPEN, settings.WEEKEND_CLOSE
    else:  # Пн-Чт, Вс
        return settings.WEEKDAY_OPEN, settings.WEEKDAY_CLOSE

def get_available_times(date):
    """Получение доступных временных слотов"""
    open_time, close_time = get_working_hours(date)
    times = []
    now = datetime.now()
    
    print(f"\n=== Генерация слотов для {date.date()} ({['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][date.weekday()]}) ===")
    print(f"Часы работы: {open_time.hour:02d}:{open_time.minute:02d} - {close_time.hour:02d}:{close_time.minute:02d}")
    
    # Начало работы
    current = date.replace(
        hour=open_time.hour,
        minute=open_time.minute,
        second=0,
        microsecond=0
    )
    
    # Если закрытие после полуночи
    if close_time.hour < open_time.hour:
        print("Режим работы: через полночь")
        
        # Слоты до полуночи
        midnight = (date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"\nСлоты от {current} до {midnight}:")
        while current < midnight:
            if current > now:
                times.append(current)
                print(f"  ✓ {current.strftime('%Y-%m-%d %H:%M')}")
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
        
        # Слоты после полуночи
        next_day_start = midnight
        next_day_end = next_day_start.replace(
            hour=close_time.hour,
            minute=close_time.minute
        )
        next_day_end_for_booking = next_day_end - timedelta(hours=settings.MIN_BOOKING_HOURS)
        
        print(f"\nСлоты от {next_day_start} до {next_day_end_for_booking}:")
        current = next_day_start
        while current <= next_day_end_for_booking:
            if current > now:
                times.append(current)
                print(f"  ✓ {current.strftime('%Y-%m-%d %H:%M')}")
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
    else:
        print("Режим работы: в пределах дня")
        end = date.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)
        end_for_booking = end - timedelta(hours=settings.MIN_BOOKING_HOURS)
        
        while current <= end_for_booking:
            if current > now:
                times.append(current)
                print(f"  ✓ {current.strftime('%Y-%m-%d %H:%M')}")
            current += timedelta(minutes=settings.BOOKING_STEP_MINUTES)
    
    print(f"\nВсего сгенерировано слотов: {len(times)}")
    return times

def is_valid_booking_time(start_time, duration_hours):
    """Проверка валидности времени бронирования"""
    end_time = start_time + timedelta(hours=duration_hours)
    open_time, close_time = get_working_hours(start_time)
    
    print(f"\n=== Проверка бронирования ===")
    print(f"Начало: {start_time}")
    print(f"Конец: {end_time}")
    print(f"Длительность: {duration_hours}ч")
    print(f"Часы работы: {open_time} - {close_time}")
    
    # Если слот после полуночи и закрытие после полуночи
    if start_time.hour < 6 and close_time.hour < open_time.hour:
        print("Слот после полуночи")
        close_datetime = start_time.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
            microsecond=0
        )
        
        if close_datetime < start_time:
            print(f"❌ Закрытие {close_datetime} < начало {start_time}")
            return False
        
        result = end_time <= close_datetime
        print(f"{'✓' if result else '❌'} Конец {end_time} <= закрытие {close_datetime}")
        return result
    
    open_datetime = start_time.replace(hour=open_time.hour, minute=open_time.minute, second=0, microsecond=0)
    
    if close_time.hour < open_time.hour:
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
    
    is_after_midnight = start_time.hour < 6
    
    if is_after_midnight and close_time.hour < open_time.hour:
        result = end_time <= close_datetime
        print(f"{'✓' if result else '❌'} После полуночи: конец <= закрытие")
        return result
    
    result = start_time >= open_datetime and end_time <= close_datetime
    print(f"{'✓' if result else '❌'} Обычная проверка")
    return result

# Тесты
if __name__ == "__main__":
    print("="*60)
    print("ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ СЛОТОВ")
    print("="*60)
    
    # Тест 1: Будний день (сегодня или завтра)
    test_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Ищем ближайший будний день
    while test_date.weekday() in [4, 5]:
        test_date += timedelta(days=1)
    
    slots = get_available_times(test_date)
    
    # Тест 2: Проверка бронирования в 01:00 на 1 час
    test_time = test_date.replace(hour=1, minute=0) + timedelta(days=1)
    print("\n" + "="*60)
    is_valid_booking_time(test_time, 1)
    
    # Тест 3: Проверка бронирования в 01:00 на 2 часа (должна быть ошибка)
    print("\n" + "="*60)
    is_valid_booking_time(test_time, 2)
    
    print("\n" + "="*60)
    print("ТЕСТЫ ЗАВЕРШЕНЫ")
    print("="*60)
