"""
Обработчики команд администраторов
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import settings
from database.repository import BookingRepository, TableRepository
from keyboards.keyboards import (
    get_admin_keyboard, get_main_menu_keyboard,
    get_admin_dates_keyboard, get_admin_bookings_keyboard,
    get_admin_booking_detail_keyboard
)
from utils.time_utils import format_datetime, format_date, get_available_dates

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return settings.is_admin(user_id)


@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    """Открытие админ-панели"""
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "⚙️ Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin_bookings")
async def admin_view_bookings(callback: CallbackQuery):
    """Просмотр броней по датам"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    dates = get_available_dates()
    # Добавляем еще несколько дней для просмотра истории
    for i in range(7, 14):
        dates.append(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=i))
    
    await callback.message.edit_text(
        "📅 Выберите дату для просмотра бронирований:",
        reply_markup=get_admin_dates_keyboard(dates)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_date:"))
async def admin_show_date_bookings(callback: CallbackQuery):
    """Показать брони на выбранную дату"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    bookings = BookingRepository.get_bookings_by_date(selected_date)
    
    if not bookings:
        await callback.message.edit_text(
            f"📋 На {format_date(selected_date)} нет бронирований",
            reply_markup=get_admin_dates_keyboard(get_available_dates())
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📋 Бронирования на {format_date(selected_date)}:\n\n"
        f"Всего броней: {len(bookings)}",
        reply_markup=get_admin_bookings_keyboard(bookings, selected_date)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_booking:"))
async def admin_show_booking_detail(callback: CallbackQuery):
    """Показать детали бронирования админу"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    date_str = parts[2] if len(parts) > 2 else None
    
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking:
        await callback.answer("❌ Бронирование не найдено", show_alert=True)
        return
    
    table = TableRepository.get_table_by_id(booking.table_id)
    table_name = table.name if table else f"Стол #{booking.table_id}"
    
    status_emoji = "✅" if booking.status == "active" else "❌"
    status_text = "Активно" if booking.status == "active" else "Отменено"
    
    text = (
        f"📋 Бронирование #{booking.id}\n\n"
        f"{status_emoji} Статус: {status_text}\n"
        f"📅 Дата и время: {format_datetime(booking.start_time)}\n"
        f"⏱ Длительность: {booking.duration_hours} ч\n"
        f"🕐 Окончание: {format_datetime(booking.end_time)}\n"
        f"🎱 Стол: {table_name}\n"
        f"👤 Пользователь: @{booking.username or 'без username'}\n"
        f"🆔 User ID: {booking.user_id}\n"
        f"📱 Телефон: {booking.phone}\n"
        f"📝 Создано: {format_datetime(booking.created_at)}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_booking_detail_keyboard(booking.id, booking.status, date_str)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel_booking(callback: CallbackQuery):
    """Отмена бронирования администратором через callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    date_str = parts[2] if len(parts) > 2 else None
    
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking:
        await callback.answer("❌ Бронирование не найдено", show_alert=True)
        return
    
    if booking.status != 'active':
        await callback.answer("⚠️ Бронирование уже отменено", show_alert=True)
        return
    
    # Отмена брони
    if BookingRepository.cancel_booking(booking_id):
        table = TableRepository.get_table_by_id(booking.table_id)
        table_name = table.name if table else f"Стол #{booking.table_id}"
        
        # Уведомление пользователя
        try:
            await callback.bot.send_message(
                booking.user_id,
                f"❌ Ваше бронирование #{booking_id} было отменено администратором\n\n"
                f"📅 {format_datetime(booking.start_time)}\n"
                f"⏱ {booking.duration_hours} ч\n"
                f"🎱 {table_name}\n\n"
                f"По вопросам обращайтесь к администрации."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {booking.user_id}: {e}")
        
        # Уведомление других администраторов
        admin_text = (
            f"ℹ️ Администратор @{callback.from_user.username or 'без username'} "
            f"отменил бронирование #{booking_id}\n\n"
            f"📅 {format_datetime(booking.start_time)}\n"
            f"🎱 {table_name}\n"
            f"👤 Пользователь: @{booking.username or 'без username'}"
        )
        
        for admin_id in settings.ADMIN_IDS:
            if admin_id != callback.from_user.id:
                try:
                    await callback.bot.send_message(admin_id, admin_text)
                except Exception as e:
                    logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        await callback.answer("✅ Бронирование отменено", show_alert=True)
        
        # Обновление сообщения
        await admin_show_booking_detail(callback)
    else:
        await callback.answer("❌ Не удалось отменить бронирование", show_alert=True)


@router.callback_query(F.data.startswith("admin_back_to_date:"))
async def admin_back_to_date(callback: CallbackQuery):
    """Вернуться к списку броней на дату"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    bookings = BookingRepository.get_bookings_by_date(selected_date)
    
    await callback.message.edit_text(
        f"📋 Бронирования на {format_date(selected_date)}:\n\n"
        f"Всего броней: {len(bookings)}",
        reply_markup=get_admin_bookings_keyboard(bookings, selected_date)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back_to_dates")
async def admin_back_to_dates(callback: CallbackQuery):
    """Вернуться к выбору дат"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    dates = get_available_dates()
    for i in range(7, 14):
        dates.append(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=i))
    
    await callback.message.edit_text(
        "📅 Выберите дату для просмотра бронирований:",
        reply_markup=get_admin_dates_keyboard(dates)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back_to_panel")
async def admin_back_to_panel(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.message(Command("today"))
async def cmd_today(message: Message):
    """Команда /today - список броней на сегодня"""
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У вас нет доступа к этой команде")
        return
    
    await show_today_bookings(message)


@router.callback_query(F.data == "admin_today")
async def callback_today(callback: CallbackQuery):
    """Callback для броней на сегодня"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    await show_today_bookings(callback.message)
    await callback.answer()


async def show_today_bookings(message: Message):
    """Показать брони на сегодня"""
    bookings = BookingRepository.get_today_bookings()
    
    if not bookings:
        await message.answer("📋 На сегодня нет бронирований")
        return
    
    text = "📋 Бронирования на сегодня:\n\n"
    
    for booking in bookings:
        table = TableRepository.get_table_by_id(booking.table_id)
        table_name = table.name if table else f"Стол #{booking.table_id}"
        
        text += (
            f"🔹 Бронь #{booking.id}\n"
            f"   🕐 {format_datetime(booking.start_time)}\n"
            f"   ⏱ {booking.duration_hours} ч\n"
            f"   🎱 {table_name}\n"
            f"   👤 @{booking.username or 'без username'}\n"
            f"   📱 {booking.phone}\n\n"
        )
    
    text += f"Всего броней: {len(bookings)}"
    
    # Разбиение длинного сообщения
    if len(text) > 4000:
        parts = []
        current_part = "📋 Бронирования на сегодня:\n\n"
        
        for booking in bookings:
            table = TableRepository.get_table_by_id(booking.table_id)
            table_name = table.name if table else f"Стол #{booking.table_id}"
            
            booking_text = (
                f"🔹 Бронь #{booking.id}\n"
                f"   🕐 {format_datetime(booking.start_time)}\n"
                f"   ⏱ {booking.duration_hours} ч\n"
                f"   🎱 {table_name}\n"
                f"   👤 @{booking.username or 'без username'}\n"
                f"   📱 {booking.phone}\n\n"
            )
            
            if len(current_part) + len(booking_text) > 4000:
                parts.append(current_part)
                current_part = booking_text
            else:
                current_part += booking_text
        
        if current_part:
            parts.append(current_part + f"\nВсего броней: {len(bookings)}")
        
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Команда /cancel <id> - отмена брони администратором"""
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У вас нет доступа к этой команде")
        return
    
    # Парсинг ID брони
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ Использование: /cancel <id>\n\n"
            "Пример: /cancel 123"
        )
        return
    
    try:
        booking_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ ID брони должен быть числом")
        return
    
    # Получение информации о брони
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking:
        await message.answer(f"⚠️ Бронирование #{booking_id} не найдено")
        return
    
    if booking.status != 'active':
        await message.answer(f"⚠️ Бронирование #{booking_id} уже отменено")
        return
    
    # Отмена брони
    if BookingRepository.cancel_booking(booking_id):
        table = TableRepository.get_table_by_id(booking.table_id)
        table_name = table.name if table else f"Стол #{booking.table_id}"
        
        await message.answer(
            f"✅ Бронирование #{booking_id} успешно отменено\n\n"
            f"📅 {format_datetime(booking.start_time)}\n"
            f"⏱ {booking.duration_hours} ч\n"
            f"🎱 {table_name}\n"
            f"👤 @{booking.username or 'без username'}"
        )
        
        # Уведомление пользователя
        try:
            await message.bot.send_message(
                booking.user_id,
                f"❌ Ваше бронирование #{booking_id} было отменено администратором\n\n"
                f"📅 {format_datetime(booking.start_time)}\n"
                f"⏱ {booking.duration_hours} ч\n"
                f"🎱 {table_name}\n\n"
                f"По вопросам обращайтесь к администрации."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {booking.user_id}: {e}")
        
        # Уведомление других администраторов
        admin_text = (
            f"ℹ️ Администратор @{message.from_user.username or 'без username'} "
            f"отменил бронирование #{booking_id}\n\n"
            f"📅 {format_datetime(booking.start_time)}\n"
            f"👤 Пользователь: @{booking.username or 'без username'}"
        )
        
        for admin_id in settings.ADMIN_IDS:
            if admin_id != message.from_user.id:
                try:
                    await message.bot.send_message(admin_id, admin_text)
                except Exception as e:
                    logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    else:
        await message.answer(f"⚠️ Не удалось отменить бронирование #{booking_id}")
