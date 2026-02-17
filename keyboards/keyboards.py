"""
Клавиатуры для Telegram бота
"""
from datetime import datetime
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Table, Booking
from utils.time_utils import format_date, format_time
from config import settings


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [KeyboardButton(text="📅 Забронировать стол")],
        [KeyboardButton(text="🏆 Записаться на турнир 23.02")],
        [KeyboardButton(text="📋 Мои бронирования")],
        [KeyboardButton(text="🆘 Поддержка")],
    ]
    
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_dates_keyboard(dates: List[datetime]) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты"""
    builder = InlineKeyboardBuilder()
    
    for date in dates:
        builder.button(
            text=format_date(date),
            callback_data=f"date:{date.strftime('%Y-%m-%d')}"
        )
    
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    
    return builder.as_markup()


def get_times_keyboard(times: List[datetime]) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    builder = InlineKeyboardBuilder()
    
    for time in times:
        builder.button(
            text=format_time(time),
            callback_data=f"time:{time.strftime('%Y-%m-%d-%H-%M')}"
        )
    
    builder.button(text="◀️ Назад", callback_data="back_to_date")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(3, 3, 3, 2)
    
    return builder.as_markup()


def get_duration_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора длительности"""
    builder = InlineKeyboardBuilder()
    
    for hours in range(settings.MIN_BOOKING_HOURS, settings.MAX_BOOKING_HOURS + 1):
        if hours == 1:
            text = f"{hours} час"
        elif hours in [2, 3, 4]:
            text = f"{hours} часа"
        else:
            text = f"{hours} часов"
        builder.button(text=text, callback_data=f"duration:{hours}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_time")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 2, 2)
    
    return builder.as_markup()


def get_tables_keyboard(tables: List[Table]) -> InlineKeyboardMarkup:
    """Клавиатура выбора стола"""
    builder = InlineKeyboardBuilder()
    
    for table in tables:
        builder.button(text=table.name, callback_data=f"table:{table.id}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_duration")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 2)
    
    return builder.as_markup()


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отправки телефона"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить телефон", request_contact=True)]],
        resize_keyboard=True
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения бронирования"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="◀️ Изменить", callback_data="back_to_table")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    
    return builder.as_markup()


def get_bookings_keyboard(bookings: List[Booking]) -> InlineKeyboardMarkup:
    """Клавиатура списка бронирований пользователя"""
    builder = InlineKeyboardBuilder()
    
    for booking in bookings:
        text = f"🗓 {format_date(booking.start_time)} {format_time(booking.start_time)}"
        builder.button(text=text, callback_data=f"show_booking:{booking.id}")
    
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()


def get_booking_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с бронированием"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🗑 Отменить бронь", callback_data=f"cancel_booking:{booking_id}")
    builder.button(text="◀️ Назад", callback_data="my_bookings")
    builder.adjust(1)
    
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 Брони на сегодня", callback_data="admin_today")
    builder.button(text="📅 Просмотр броней по датам", callback_data="admin_bookings")
    builder.button(text="🔒 Закрыть бронь", callback_data="admin_block_booking")
    builder.button(text="🏆 Участники турнира", callback_data="admin_tournament")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()


def get_admin_dates_keyboard(dates: List[datetime]) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты для админа"""
    builder = InlineKeyboardBuilder()
    
    for date in dates:
        builder.button(
            text=format_date(date),
            callback_data=f"admin_date:{date.strftime('%Y-%m-%d')}"
        )
    
    builder.button(text="◀️ Назад в админ-панель", callback_data="admin_back_to_panel")
    builder.adjust(2)
    
    return builder.as_markup()


def get_admin_bookings_keyboard(bookings: List[Booking], date: datetime) -> InlineKeyboardMarkup:
    """Клавиатура списка бронирований для админа"""
    builder = InlineKeyboardBuilder()
    
    for booking in bookings:
        status_emoji = "✅" if booking.status == "active" else "❌"
        text = f"{status_emoji} {format_time(booking.start_time)} - {booking.duration_hours}ч"
        builder.button(
            text=text,
            callback_data=f"admin_booking:{booking.id}:{date.strftime('%Y-%m-%d')}"
        )
    
    builder.button(text="◀️ Назад к датам", callback_data="admin_back_to_dates")
    builder.adjust(1)
    
    return builder.as_markup()


def get_admin_booking_detail_keyboard(booking_id: int, status: str, date_str: str = None) -> InlineKeyboardMarkup:
    """Клавиатура действий с бронированием для админа"""
    builder = InlineKeyboardBuilder()
    
    if status == "active":
        callback_data = f"admin_cancel:{booking_id}"
        if date_str:
            callback_data += f":{date_str}"
        builder.button(text="🗑 Отменить бронь", callback_data=callback_data)
        
        # Кнопка редактирования длительности
        edit_callback = f"admin_edit:{booking_id}"
        if date_str:
            edit_callback += f":{date_str}"
        builder.button(text="✏️ Изменить длительность", callback_data=edit_callback)
    
    if date_str:
        builder.button(text="◀️ Назад к списку", callback_data=f"admin_back_to_date:{date_str}")
    else:
        builder.button(text="◀️ Назад в админ-панель", callback_data="admin_back_to_panel")
    
    builder.adjust(1)
    
    return builder.as_markup()


def get_admin_edit_duration_keyboard(booking_id: int, current_duration: int, date_str: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора новой длительности для редактирования"""
    builder = InlineKeyboardBuilder()
    
    for hours in range(settings.MIN_BOOKING_HOURS, settings.MAX_BOOKING_HOURS + 1):
        if hours == current_duration:
            continue  # Пропускаем текущую длительность
        
        if hours == 1:
            text = f"{hours} час"
        elif hours in [2, 3, 4]:
            text = f"{hours} часа"
        else:
            text = f"{hours} часов"
        
        callback_data = f"admin_set_duration:{booking_id}:{hours}"
        if date_str:
            callback_data += f":{date_str}"
        builder.button(text=text, callback_data=callback_data)
    
    # Кнопка назад к деталям брони
    back_callback = f"admin_booking:{booking_id}"
    if date_str:
        back_callback += f":{date_str}"
    builder.button(text="◀️ Назад", callback_data=back_callback)
    
    builder.adjust(2)
    
    return builder.as_markup()


def get_admin_block_dates_keyboard(dates: List[datetime]) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты для блокировки"""
    builder = InlineKeyboardBuilder()
    
    for date in dates:
        builder.button(
            text=format_date(date),
            callback_data=f"admin_block_date:{date.strftime('%Y-%m-%d')}"
        )
    
    builder.button(text="◀️ Назад в админ-панель", callback_data="admin_back_to_panel")
    builder.adjust(2)
    
    return builder.as_markup()


def get_admin_block_times_keyboard(times: List[datetime]) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени для блокировки"""
    builder = InlineKeyboardBuilder()
    
    for time in times:
        builder.button(
            text=format_time(time),
            callback_data=f"admin_block_time:{time.strftime('%Y-%m-%d-%H-%M')}"
        )
    
    builder.button(text="◀️ Назад", callback_data="admin_block_booking")
    builder.adjust(3)
    
    return builder.as_markup()


def get_admin_block_duration_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора длительности блокировки"""
    builder = InlineKeyboardBuilder()
    
    for hours in range(settings.MIN_BOOKING_HOURS, settings.MAX_BOOKING_HOURS + 1):
        if hours == 1:
            text = f"{hours} час"
        elif hours in [2, 3, 4]:
            text = f"{hours} часа"
        else:
            text = f"{hours} часов"
        builder.button(text=text, callback_data=f"admin_block_duration:{hours}")
    
    builder.button(text="◀️ Назад", callback_data="admin_block_back_to_time")
    builder.adjust(2)
    
    return builder.as_markup()


def get_admin_block_tables_keyboard(tables: List[Table]) -> InlineKeyboardMarkup:
    """Клавиатура выбора стола для блокировки"""
    builder = InlineKeyboardBuilder()
    
    for table in tables:
        builder.button(text=table.name, callback_data=f"admin_block_table:{table.id}")
    
    builder.button(text="◀️ Назад", callback_data="admin_block_back_to_duration")
    builder.adjust(2)
    
    return builder.as_markup()


def get_tournament_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи на турнир"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Подтвердить запись", callback_data="tournament_confirm")
    builder.button(text="❌ Отмена", callback_data="tournament_cancel")
    builder.adjust(1)
    
    return builder.as_markup()


def get_tournament_registered_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для зарегистрированного участника"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🗑 Отменить регистрацию", callback_data="tournament_user_cancel")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()
