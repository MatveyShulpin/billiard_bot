"""
Обработчики команд и сообщений пользователей
"""
import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from config import settings
from database.repository import BookingRepository, HoldRepository, TableRepository
from database.models import Booking, Hold
from states.booking_states import BookingStates, SupportStates
from keyboards.keyboards import (
    get_main_menu_keyboard, get_dates_keyboard, get_times_keyboard,
    get_duration_keyboard, get_tables_keyboard, get_phone_keyboard,
    get_confirmation_keyboard, get_bookings_keyboard, get_booking_actions_keyboard,
    get_cancel_keyboard
)
from utils.time_utils import (
    get_available_dates, get_available_times, is_valid_booking_time,
    format_datetime, format_time
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    is_admin = settings.is_admin(message.from_user.id)
    
    await message.answer(
        f"👋 Добро пожаловать в бот бронирования бильярдных столов!\n\n"
        f"Здесь вы можете:\n"
        f"📅 Забронировать стол на удобное время\n"
        f"📋 Просмотреть свои бронирования\n"
        f"🗑 Отменить бронирование\n\n"
        f"Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin)
    )


@router.message(F.text == "📅 Забронировать стол")
async def start_booking(message: Message, state: FSMContext):
    """Начало процесса бронирования"""
    await state.clear()
    
    dates = get_available_dates()
    await message.answer(
        "📅 Выберите дату:",
        reply_markup=get_dates_keyboard(dates)
    )
    await state.set_state(BookingStates.choosing_date)


@router.callback_query(F.data.startswith("date:"), BookingStates.choosing_date)
async def process_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    await state.update_data(selected_date=selected_date)
    
    times = get_available_times(selected_date)
    
    logger.info(f"Доступные слоты для {selected_date.date()}: {len(times)} шт.")
    if times:
        logger.info(f"Первый слот: {times[0]}, Последний слот: {times[-1]}")
    
    if not times:
        await callback.answer("На эту дату нет доступных слотов", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🕐 Выберите время начала:",
        reply_markup=get_times_keyboard(times)
    )
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data.startswith("time:"), BookingStates.choosing_time)
async def process_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    time_str = callback.data.split(":", 1)[1]
    selected_time = datetime.strptime(time_str, "%Y-%m-%d-%H-%M")
    
    await state.update_data(selected_time=selected_time)
    
    await callback.message.edit_text(
        f"⏱ Выберите длительность:",
        reply_markup=get_duration_keyboard()
    )
    await state.set_state(BookingStates.choosing_duration)
    await callback.answer()


@router.callback_query(F.data.startswith("duration:"), BookingStates.choosing_duration)
async def process_duration(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора длительности"""
    duration = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    start_time = data['selected_time']
    end_time = start_time + timedelta(hours=duration)
    
    # Логирование для отладки
    logger.info(f"Проверка бронирования: start={start_time}, end={end_time}, duration={duration}h")
    
    # Проверка, что бронирование не выходит за часы работы
    if not is_valid_booking_time(start_time, duration):
        open_time, close_time = get_working_hours(start_time)
        
        # Формируем понятное сообщение о времени работы
        if close_time.hour < open_time.hour:
            # Закрытие после полуночи
            close_str = f"{close_time.hour:02d}:{close_time.minute:02d} (следующего дня)"
        else:
            close_str = f"{close_time.hour:02d}:{close_time.minute:02d}"
        
        logger.warning(f"Бронирование выходит за часы работы: {open_time.hour:02d}:{open_time.minute:02d} - {close_str}")
        
        await callback.answer(
            f"⚠️ Бронирование выходит за часы работы!\n"
            f"Работаем: {open_time.hour:02d}:{open_time.minute:02d} - {close_str}\n"
            f"При длительности {duration}ч бронь закончится в {end_time.strftime('%H:%M')}",
            show_alert=True
        )
        return
    
    await state.update_data(duration=duration, end_time=end_time)
    
    tables = TableRepository.get_all_tables()
    
    await callback.message.edit_text(
        f"🎱 Выберите стол:",
        reply_markup=get_tables_keyboard(tables)
    )
    await state.set_state(BookingStates.choosing_table)
    await callback.answer()


@router.callback_query(F.data.startswith("table:"), BookingStates.choosing_table)
async def process_table(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора стола"""
    table_str = callback.data.split(":")[1]
    table_id = int(table_str)
    
    data = await state.get_data()
    start_time = data['selected_time']
    end_time = data['end_time']
    
    # Проверка доступности
    is_available = BookingRepository.check_availability(
        table_id, start_time, end_time, exclude_user=callback.from_user.id
    )
    
    if not is_available:
        await callback.answer(
            "⚠️ К сожалению, выбранный стол уже занят на это время. Выберите другой.",
            show_alert=True
        )
        return
    
    # Создание временного hold
    hold = Hold(
        id=None,
        user_id=callback.from_user.id,
        table_id=table_id,
        start_time=start_time,
        end_time=end_time,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=settings.HOLD_TIMEOUT_MINUTES)
    )
    
    # Удаляем старые holds пользователя и создаём новый
    HoldRepository.delete_user_holds(callback.from_user.id)
    HoldRepository.create_hold(hold)
    
    await state.update_data(table_id=table_id)
    
    await callback.message.edit_text(
        f"📱 Пожалуйста, отправьте ваш контактный телефон.\n\n"
        f"⏰ У вас есть {settings.HOLD_TIMEOUT_MINUTES} минут на завершение бронирования."
    )
    
    await callback.message.answer(
        "Нажмите кнопку ниже или введите номер вручную:",
        reply_markup=get_phone_keyboard()
    )
    
    await state.set_state(BookingStates.entering_phone)
    await callback.answer()


@router.message(BookingStates.entering_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка контакта"""
    phone = message.contact.phone_number
    await process_phone_number(message, state, phone)


@router.message(BookingStates.entering_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Обработка текстового ввода телефона"""
    phone = message.text.strip()
    
    # Простая валидация
    if len(phone) < 10:
        await message.answer("⚠️ Введите корректный номер телефона")
        return
    
    await process_phone_number(message, state, phone)


async def process_phone_number(message: Message, state: FSMContext, phone: str):
    """Общая обработка номера телефона"""
    await state.update_data(phone=phone)
    data = await state.get_data()
    
    # Проверка, что hold ещё не истёк
    is_available = BookingRepository.check_availability(
        data['table_id'], data['selected_time'], data['end_time'],
        exclude_user=message.from_user.id
    )
    
    if not is_available:
        await message.answer(
            "⚠️ К сожалению, время истекло и стол был занят другим пользователем.\n"
            "Начните бронирование заново.",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        await state.clear()
        return
    
    # Формирование подтверждения
    table = TableRepository.get_table_by_id(data['table_id'])
    table_name = table.name if table else "Неизвестный стол"
    
    confirmation_text = (
        f"✅ Подтверждение бронирования:\n\n"
        f"📅 Дата: {format_datetime(data['selected_time'])}\n"
        f"⏱ Длительность: {data['duration']} ч\n"
        f"🎱 Стол: {table_name}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Подтвердите бронирование:"
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(BookingStates.confirming)


@router.callback_query(F.data == "confirm_booking", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и создание бронирования"""
    data = await state.get_data()
    
    # Финальная проверка доступности
    is_available = BookingRepository.check_availability(
        data['table_id'], data['selected_time'], data['end_time'],
        exclude_user=callback.from_user.id
    )
    
    if not is_available:
        await callback.message.edit_text(
            "⚠️ К сожалению, стол уже занят. Попробуйте забронировать другое время."
        )
        await callback.answer()
        await state.clear()
        HoldRepository.delete_user_holds(callback.from_user.id)
        return
    
    # Создание бронирования
    booking = Booking(
        id=None,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        table_id=data['table_id'],
        start_time=data['selected_time'],
        end_time=data['end_time'],
        phone=data['phone'],
        created_at=datetime.now()
    )
    
    booking_id = BookingRepository.create_booking(booking)
    
    # Удаление hold
    HoldRepository.delete_user_holds(callback.from_user.id)
    
    # Уведомление администраторов
    table = TableRepository.get_table_by_id(data['table_id'])
    table_name = table.name if table else "Неизвестный стол"
    
    admin_text = (
        f"📌 Новое бронирование #{booking_id}\n\n"
        f"👤 @{callback.from_user.username or 'без username'}\n"
        f"📅 {format_datetime(data['selected_time'])}\n"
        f"⏱ {data['duration']} ч\n"
        f"🎱 {table_name}\n"
        f"📱 {data['phone']}"
    )
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    await callback.message.edit_text(
        f"✅ Бронирование успешно создано!\n\n"
        f"📋 Номер брони: #{booking_id}\n"
        f"📅 {format_datetime(data['selected_time'])}\n"
        f"⏱ Длительность: {data['duration']} ч\n"
        f"🎱 Стол: {table_name}\n\n"
        f"Ждём вас! 🎱"
    )
    
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
    )
    
    await state.clear()
    await callback.answer()


@router.message(F.text == "📋 Мои бронирования")
async def my_bookings(message: Message):
    """Просмотр бронирований пользователя"""
    bookings = BookingRepository.get_user_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer(
            "У вас пока нет активных бронирований.",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        return
    
    await message.answer(
        "📋 Ваши бронирования:",
        reply_markup=get_bookings_keyboard(bookings)
    )


@router.callback_query(F.data.startswith("show_booking:"))
async def show_booking_details(callback: CallbackQuery):
    """Показать детали бронирования"""
    booking_id = int(callback.data.split(":")[1])
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking or booking.user_id != callback.from_user.id:
        await callback.answer("Бронирование не найдено", show_alert=True)
        return
    
    table = TableRepository.get_table_by_id(booking.table_id)
    table_name = table.name if table else "Неизвестный стол"
    
    text = (
        f"📋 Бронирование #{booking.id}\n\n"
        f"📅 Дата и время: {format_datetime(booking.start_time)}\n"
        f"⏱ Длительность: {booking.duration_hours} ч\n"
        f"🎱 Стол: {table_name}\n"
        f"📱 Телефон: {booking.phone}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_booking_actions_keyboard(booking.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking(callback: CallbackQuery):
    """Отмена бронирования пользователем"""
    booking_id = int(callback.data.split(":")[1])
    booking = BookingRepository.get_booking_by_id(booking_id)
    
    if not booking or booking.user_id != callback.from_user.id:
        await callback.answer("Бронирование не найдено", show_alert=True)
        return
    
    if BookingRepository.cancel_booking(booking_id):
        # Уведомление администраторов
        admin_text = (
            f"❌ Бронирование #{booking_id} отменено пользователем\n\n"
            f"👤 @{callback.from_user.username or 'без username'}\n"
            f"📅 {format_datetime(booking.start_time)}"
        )
        
        for admin_id in settings.ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, admin_text)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        
        await callback.message.edit_text("✅ Бронирование успешно отменено")
        await callback.answer()
    else:
        await callback.answer("Не удалось отменить бронирование", show_alert=True)


# Навигация назад
@router.callback_query(F.data == "back_to_date")
async def back_to_date(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    dates = get_available_dates()
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=get_dates_keyboard(dates)
    )
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()


@router.callback_query(F.data == "back_to_time")
async def back_to_time(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору времени"""
    data = await state.get_data()
    times = get_available_times(data['selected_date'])
    
    await callback.message.edit_text(
        "🕐 Выберите время начала:",
        reply_markup=get_times_keyboard(times)
    )
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data == "back_to_duration")
async def back_to_duration(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору длительности"""
    await callback.message.edit_text(
        "⏱ Выберите длительность:",
        reply_markup=get_duration_keyboard()
    )
    await state.set_state(BookingStates.choosing_duration)
    await callback.answer()


@router.callback_query(F.data == "back_to_table")
async def back_to_table(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору стола"""
    tables = TableRepository.get_all_tables()
    await callback.message.edit_text(
        "🎱 Выберите стол:",
        reply_markup=get_tables_keyboard(tables)
    )
    await state.set_state(BookingStates.choosing_table)
    await callback.answer()


@router.callback_query(F.data == "my_bookings")
async def callback_my_bookings(callback: CallbackQuery):
    """Возврат к списку бронирований"""
    bookings = BookingRepository.get_user_bookings(callback.from_user.id)
    
    if not bookings:
        await callback.message.edit_text("У вас пока нет активных бронирований.")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📋 Ваши бронирования:",
        reply_markup=get_bookings_keyboard(bookings)
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    HoldRepository.delete_user_holds(callback.from_user.id)
    
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса бронирования"""
    await state.clear()
    HoldRepository.delete_user_holds(callback.from_user.id)
    
    await callback.message.edit_text("❌ Бронирование отменено")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.message(F.text == "🆘 Поддержка")
async def support_start(message: Message, state: FSMContext):
    """Начало обращения в поддержку"""
    await state.clear()
    await message.answer(
        "🆘 Поддержка\n\n"
        "Опишите вашу проблему, и мы свяжемся с вами.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SupportStates.waiting_for_message)


@router.message(SupportStates.waiting_for_message, F.text)
async def support_send_message(message: Message, state: FSMContext):
    """Отправка сообщения поддержки администратору"""
    await state.clear()

    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"
    full_name = user.full_name or "Без имени"

    admin_text = (
        f"🆘 Обращение в поддержку\n\n"
        f"👤 {full_name} ({username})\n"
        f"🆔 ID: {user.id}\n\n"
        f"💬 {message.text}"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение поддержки админу {admin_id}: {e}")

    await message.answer(
        "✅ Ваше сообщение отправлено. Мы скоро свяжемся с вами.",
        reply_markup=get_main_menu_keyboard(settings.is_admin(user.id))
    )
