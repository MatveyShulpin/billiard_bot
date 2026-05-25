"""
Обработчики команд администраторов
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import settings
from database.repository import BookingRepository, TableRepository, TournamentRepository
from keyboards.keyboards import (
    get_admin_keyboard, get_main_menu_keyboard,
    get_admin_dates_keyboard, get_admin_bookings_keyboard,
    get_admin_booking_detail_keyboard, get_admin_edit_duration_keyboard,
    get_admin_block_dates_keyboard, get_admin_block_times_keyboard,
    get_admin_block_duration_keyboard, get_admin_block_tables_keyboard
)
from utils.time_utils import (
    format_datetime, format_date, get_available_dates, 
    get_available_times, is_valid_booking_time
)
from states.booking_states import AdminBlockStates

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
async def admin_back_to_panel(callback: CallbackQuery, state: FSMContext):
    """Вернуться в админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    await state.clear()  # Очищаем состояние
    
    await callback.message.edit_text(
        "⚙️ Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


# === РЕДАКТИРОВАНИЕ ДЛИТЕЛЬНОСТИ ===

@router.callback_query(F.data.startswith("admin_edit:"))
async def admin_edit_booking(callback: CallbackQuery):
    """Начало редактирования длительности брони"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    date_str = parts[2] if len(parts) > 2 else None
    
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking or booking.status != 'active':
        await callback.answer("❌ Бронирование не найдено или отменено", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✏️ Редактирование брони #{booking_id}\n\n"
        f"📅 {format_datetime(booking.start_time)}\n"
        f"⏱ Текущая длительность: {booking.duration_hours} ч\n\n"
        f"Выберите новую длительность:",
        reply_markup=get_admin_edit_duration_keyboard(booking_id, booking.duration_hours, date_str)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_duration:"))
async def admin_set_duration(callback: CallbackQuery):
    """Установка новой длительности"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    new_duration = int(parts[2])
    date_str = parts[3] if len(parts) > 3 else None
    
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking:
        await callback.answer("❌ Бронирование не найдено", show_alert=True)
        return
    
    # Проверка, что новая длительность не выходит за часы работы
    if not is_valid_booking_time(booking.start_time, new_duration):
        await callback.answer(
            "⚠️ Новая длительность выходит за часы работы клуба",
            show_alert=True
        )
        return
    
    # Проверка конфликтов с другими бронированиями
    new_end_time = booking.start_time + timedelta(hours=new_duration)
    
    # Проверяем конфликты (исключая текущую бронь)
    with_conflict = False
    all_bookings = BookingRepository.get_bookings_by_date(booking.start_time)
    
    for other_booking in all_bookings:
        if (other_booking.id != booking_id and 
            other_booking.status == 'active' and
            other_booking.table_id == booking.table_id and
            other_booking.start_time < new_end_time and 
            other_booking.end_time > booking.start_time):
            with_conflict = True
            break
    
    if with_conflict:
        await callback.answer(
            "⚠️ Новая длительность конфликтует с другими бронированиями на этом столе",
            show_alert=True
        )
        return
    
    # Обновляем длительность
    if BookingRepository.update_booking_duration(booking_id, new_duration):
        table = TableRepository.get_table_by_id(booking.table_id)
        table_name = table.name if table else f"Стол #{booking.table_id}"
        
        # Уведомление пользователя
        try:
            await callback.bot.send_message(
                booking.user_id,
                f"ℹ️ Длительность вашего бронирования #{booking_id} была изменена администратором\n\n"
                f"📅 {format_datetime(booking.start_time)}\n"
                f"⏱ Старая длительность: {booking.duration_hours} ч\n"
                f"⏱ Новая длительность: {new_duration} ч\n"
                f"🎱 {table_name}"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {booking.user_id}: {e}")
        
        await callback.answer("✅ Длительность успешно изменена", show_alert=True)
        
        # Возвращаемся к деталям брони
        updated_booking = BookingRepository.get_booking_by_id(booking_id)
        
        status_emoji = "✅"
        status_text = "Активно"
        
        text = (
            f"📋 Бронирование #{updated_booking.id}\n\n"
            f"{status_emoji} Статус: {status_text}\n"
            f"📅 Дата и время: {format_datetime(updated_booking.start_time)}\n"
            f"⏱ Длительность: {updated_booking.duration_hours} ч\n"
            f"🕐 Окончание: {format_datetime(updated_booking.end_time)}\n"
            f"🎱 Стол: {table_name}\n"
            f"👤 Пользователь: @{updated_booking.username or 'без username'}\n"
            f"🆔 User ID: {updated_booking.user_id}\n"
            f"📱 Телефон: {updated_booking.phone}\n"
            f"📝 Создано: {format_datetime(updated_booking.created_at)}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_booking_detail_keyboard(booking_id, 'active', date_str)
        )
    else:
        await callback.answer("❌ Не удалось изменить длительность", show_alert=True)


# === БЛОКИРОВКА БРОНЕЙ ===

@router.callback_query(F.data == "admin_block_booking")
async def admin_start_block(callback: CallbackQuery, state: FSMContext):
    """Начало процесса блокировки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    await state.clear()
    dates = get_available_dates()
    
    await callback.message.edit_text(
        "🔒 Блокировка времени для бронирования\n\n"
        "Выберите дату:",
        reply_markup=get_admin_block_dates_keyboard(dates)
    )
    await state.set_state(AdminBlockStates.choosing_date)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_date:"), AdminBlockStates.choosing_date)
async def admin_block_process_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты для блокировки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    await state.update_data(selected_date=selected_date)
    
    times = get_available_times(selected_date)
    
    if not times:
        await callback.answer("На эту дату нет доступных слотов", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🕐 Выберите время начала блокировки:",
        reply_markup=get_admin_block_times_keyboard(times)
    )
    await state.set_state(AdminBlockStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_time:"), AdminBlockStates.choosing_time)
async def admin_block_process_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени для блокировки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    time_str = callback.data.split(":", 1)[1]
    selected_time = datetime.strptime(time_str, "%Y-%m-%d-%H-%M")
    
    await state.update_data(selected_time=selected_time)
    
    await callback.message.edit_text(
        "⏱ Выберите длительность блокировки:",
        reply_markup=get_admin_block_duration_keyboard()
    )
    await state.set_state(AdminBlockStates.choosing_duration)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_duration:"), AdminBlockStates.choosing_duration)
async def admin_block_process_duration(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора длительности блокировки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    duration = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    start_time = data['selected_time']
    end_time = start_time + timedelta(hours=duration)
    
    # Проверка, что блокировка не выходит за часы работы
    if not is_valid_booking_time(start_time, duration):
        await callback.answer(
            "⚠️ Блокировка выходит за часы работы клуба",
            show_alert=True
        )
        return
    
    await state.update_data(duration=duration, end_time=end_time)
    
    tables = TableRepository.get_all_tables()
    
    await callback.message.edit_text(
        "🎱 Выберите стол для блокировки:",
        reply_markup=get_admin_block_tables_keyboard(tables)
    )
    await state.set_state(AdminBlockStates.choosing_table)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_table:"), AdminBlockStates.choosing_table)
async def admin_block_process_table(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора стола и создание блокировки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    table_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    start_time = data['selected_time']
    end_time = data['end_time']
    
    # Проверка доступности
    is_available = BookingRepository.check_availability(
        table_id, start_time, end_time
    )
    
    if not is_available:
        await callback.answer(
            "⚠️ Выбранное время уже занято на этом столе",
            show_alert=True
        )
        return
    
    # Создание блокировки
    booking_id = BookingRepository.create_blocked_booking(
        table_id,
        start_time,
        end_time,
        callback.from_user.username or str(callback.from_user.id)
    )
    
    table = TableRepository.get_table_by_id(table_id)
    table_name = table.name if table else f"Стол #{table_id}"
    
    await callback.message.edit_text(
        f"✅ Время успешно заблокировано!\n\n"
        f"📋 Блокировка #{booking_id}\n"
        f"📅 {format_datetime(start_time)}\n"
        f"⏱ Длительность: {data['duration']} ч\n"
        f"🎱 Стол: {table_name}\n\n"
        f"Это время недоступно для обычных бронирований."
    )
    
    # Уведомление других админов
    admin_text = (
        f"🔒 Администратор @{callback.from_user.username or 'без username'} "
        f"заблокировал время\n\n"
        f"📋 Блокировка #{booking_id}\n"
        f"📅 {format_datetime(start_time)}\n"
        f"⏱ {data['duration']} ч\n"
        f"🎱 {table_name}"
    )
    
    for admin_id in settings.ADMIN_IDS:
        if admin_id != callback.from_user.id:
            try:
                await callback.bot.send_message(admin_id, admin_text)
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    await callback.message.answer(
        "⚙️ Админ-панель",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


# Навигация для блокировки

@router.callback_query(F.data == "admin_block_back_to_time")
async def admin_block_back_to_time(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору времени"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    times = get_available_times(data['selected_date'])
    
    await callback.message.edit_text(
        "🕐 Выберите время начала блокировки:",
        reply_markup=get_admin_block_times_keyboard(times)
    )
    await state.set_state(AdminBlockStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data == "admin_block_back_to_duration")
async def admin_block_back_to_duration(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору длительности"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⏱ Выберите длительность блокировки:",
        reply_markup=get_admin_block_duration_keyboard()
    )
    await state.set_state(AdminBlockStates.choosing_duration)
    await callback.answer()


@router.callback_query(F.data == "admin_tournament")
async def admin_view_tournament(callback: CallbackQuery):
    """Просмотр участников турнира"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У вас нет доступа", show_alert=True)
        return
    
    sections = []
    has_registrations = False
    
    for tournament_type, tournament_name in TournamentRepository.TOURNAMENT_TYPES.items():
        registrations = TournamentRepository.get_all_registrations(tournament_type)
        active_registrations = [r for r in registrations if r.status == 'active']
        cancelled_registrations = [r for r in registrations if r.status == 'cancelled']
        
        if registrations:
            has_registrations = True
        
        section = f"🏆 {tournament_name}\n"
        section += f"📅 {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
        section += f"✅ Активных: {len(active_registrations)}/{TournamentRepository.MAX_PARTICIPANTS}\n"
        section += f"❌ Отменённых: {len(cancelled_registrations)}\n\n"
        
        if active_registrations:
            section += "📋 Активные регистрации:\n\n"
            for i, reg in enumerate(active_registrations, 1):
                section += (
                    f"{i}. {reg.full_name}\n"
                    f"   📱 {reg.phone}\n"
                    f"   💬 @{reg.username or 'без username'}\n"
                    f"   📋 ID: {reg.id}\n\n"
                )
        else:
            section += "Пока нет активных регистраций\n\n"
        
        sections.append(section)
    
    if not has_registrations:
        await callback.message.edit_text(
            f"🏆 Участники турниров\n"
            f"📅 {TournamentRepository.TOURNAMENT_DATE_TEXT}\n\n"
            "Пока нет регистраций",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
        return
    
    text = "🏆 Участники турниров\n\n" + "\n".join(sections)
    
    # Разбиение длинных сообщений
    if len(text) > 4000:
        parts = []
        current_part = "🏆 Участники турниров\n\n"
        
        for section in sections:
            if len(current_part) + len(section) > 4000:
                parts.append(current_part)
                current_part = section
            else:
                current_part += section + "\n"
        
        if current_part:
            parts.append(current_part)
        
        await callback.message.edit_text(parts[0])
        for part in parts[1:]:
            await callback.message.answer(part)
    else:
        await callback.message.edit_text(text)
    
    await callback.message.answer(
        "💡 Для отмены регистрации используйте:\n"
        "/cancel_tournament <ID>\n\n"
        "Например: /cancel_tournament 5",
        reply_markup=get_admin_keyboard()
    )
    
    await callback.answer()


@router.message(Command("cancel_tournament"))
async def cmd_cancel_tournament(message: Message):
    """Команда /cancel_tournament <id> - отмена регистрации на турнир"""
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У вас нет доступа к этой команде")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ Использование: /cancel_tournament <id>\n\n"
            "Пример: /cancel_tournament 5"
        )
        return
    
    try:
        registration_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ ID должен быть числом")
        return
    
    registration = TournamentRepository.get_registration_by_id(registration_id)
    
    if not registration:
        await message.answer(f"⚠️ Регистрация #{registration_id} не найдена")
        return
    
    if registration.status != 'active':
        await message.answer(f"⚠️ Регистрация #{registration_id} уже отменена")
        return

    tournament_name = TournamentRepository.get_tournament_name(registration.tournament_type)
    
    if TournamentRepository.cancel_registration(registration_id):
        await message.answer(
            f"✅ Регистрация #{registration_id} успешно отменена\n\n"
            f"🏆 {tournament_name}\n"
            f"📅 {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
            f"👤 {registration.full_name}\n"
            f"📱 {registration.phone}\n"
            f"💬 @{registration.username or 'без username'}"
        )
        
        # Уведомление пользователя
        try:
            await message.bot.send_message(
                registration.user_id,
                f"❌ Ваша регистрация на {tournament_name} была отменена администратором\n\n"
                f"📅 {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
                f"📋 Регистрация #{registration_id}\n"
                f"👤 {registration.full_name}\n\n"
                f"По вопросам обращайтесь к администрации."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {registration.user_id}: {e}")
        
        # Уведомление других администраторов
        admin_text = (
            f"ℹ️ Администратор @{message.from_user.username or 'без username'} "
            f"отменил регистрацию на турнир #{registration_id}\n\n"
            f"🏆 {tournament_name}\n"
            f"👤 {registration.full_name}\n"
            f"💬 @{registration.username or 'без username'}"
        )
        
        for admin_id in settings.ADMIN_IDS:
            if admin_id != message.from_user.id:
                try:
                    await message.bot.send_message(admin_id, admin_text)
                except Exception as e:
                    logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    else:
        await message.answer(f"⚠️ Не удалось отменить регистрацию #{registration_id}")


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
