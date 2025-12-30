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
        [KeyboardButton(text="📋 Мои бронирования")],
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
        text = f"{hours} час" if hours == 1 else f"{hours} часа"
        builder.button(text=text, callback_data=f"duration:{hours}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_time")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 2, 2)
    
    return builder.as_markup()


def get_tables_keyboard(tables: List[Table]) -> InlineKeyboardMarkup:
    """Клавиатура выбора стола"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🎱 Любой стол", callback_data="table:any")
    
    for table in tables:
        builder.button(text=table.name, callback_data=f"table:{table.id}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_duration")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1, 2, 2)
    
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
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()
