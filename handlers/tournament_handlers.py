"""
Обработчики регистрации на турнир
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import settings
from database.repository import TournamentRepository
from database.models import TournamentRegistration
from keyboards.keyboards import (
    get_main_menu_keyboard, get_phone_keyboard,
    get_tournament_confirmation_keyboard, get_tournament_registered_keyboard,
    get_tournament_type_keyboard,
    get_cancel_keyboard
)
from states.booking_states import TournamentStates

logger = logging.getLogger(__name__)
router = Router()

TOURNAMENT_MENU_BUTTONS = {"🏆 Турнир 07.06", "Турнир 07.06"}


@router.message(F.text.in_(TOURNAMENT_MENU_BUTTONS))
async def show_tournament_selection(message: Message, state: FSMContext):
    """Выбор турнира для регистрации"""
    await state.clear()
    
    await message.answer(
        f"🏆 Турнир 07.06\n\n"
        f"📅 Дата и время: {TournamentRepository.TOURNAMENT_DATE_TEXT}\n\n"
        f"Выберите дисциплину:",
        reply_markup=get_tournament_type_keyboard()
    )


@router.callback_query(F.data.startswith("tournament_select:"))
async def start_tournament_registration(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации на выбранный турнир"""
    await state.clear()
    
    tournament_type = callback.data.split(":", 1)[1]
    if tournament_type not in TournamentRepository.TOURNAMENT_TYPES:
        await callback.answer("Турнир не найден", show_alert=True)
        return
    
    await send_tournament_registration_start(
        callback.message,
        state,
        callback.from_user.id,
        tournament_type
    )
    await callback.answer()


async def send_tournament_registration_start(
    message: Message,
    state: FSMContext,
    user_id: int,
    tournament_type: str
):
    """Отправка первого шага регистрации на выбранный турнир"""
    tournament_name = TournamentRepository.get_tournament_name(tournament_type)
    
    # Проверка, не зарегистрирован ли уже
    existing = TournamentRepository.get_user_registration(user_id, tournament_type)
    if existing:
        await message.answer(
            f"✅ Вы уже зарегистрированы на {tournament_name}!\n\n"
            f"📅 Дата и время: {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
            f"👤 Имя: {existing.full_name}\n"
            f"📱 Телефон: {existing.phone}\n"
            f"📝 Регистрация #{existing.id}\n\n"
            f"Если хотите отменить регистрацию, нажмите кнопку ниже:",
            reply_markup=get_tournament_registered_keyboard(tournament_type)
        )
        return
    
    # Проверка наличия свободных мест
    if not TournamentRepository.is_slots_available(tournament_type):
        active_count = TournamentRepository.get_active_registrations_count(tournament_type)
        await message.answer(
            f"❌ К сожалению, все места на {tournament_name} заняты!\n\n"
            f"Зарегистрировано: {active_count}/{TournamentRepository.MAX_PARTICIPANTS}",
            reply_markup=get_main_menu_keyboard(settings.is_admin(user_id))
        )
        return
    
    # Информация о турнире
    active_count = TournamentRepository.get_active_registrations_count(tournament_type)
    remaining = TournamentRepository.MAX_PARTICIPANTS - active_count
    
    await message.answer(
        f"🏆 Регистрация на {tournament_name}\n\n"
        f"📅 Дата и время: {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
        f"👥 Свободных мест: {remaining}/{TournamentRepository.MAX_PARTICIPANTS}\n\n"
        f"Для регистрации введите ваше полное имя:",
        reply_markup=get_cancel_keyboard()
    )
    await state.update_data(tournament_type=tournament_type)
    await state.set_state(TournamentStates.entering_name)


@router.message(TournamentStates.entering_name, F.text)
async def process_tournament_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    full_name = message.text.strip()
    
    if len(full_name) < 2:
        await message.answer("⚠️ Пожалуйста, введите корректное имя")
        return
    
    await state.update_data(full_name=full_name)
    
    await message.answer(
        f"📱 Отлично, {full_name}!\n\n"
        f"Теперь отправьте ваш контактный телефон:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(TournamentStates.entering_phone)


@router.message(TournamentStates.entering_phone, F.contact)
async def process_tournament_contact(message: Message, state: FSMContext):
    """Обработка контакта"""
    phone = message.contact.phone_number
    await process_tournament_phone(message, state, phone)


@router.message(TournamentStates.entering_phone, F.text)
async def process_tournament_phone_text(message: Message, state: FSMContext):
    """Обработка текстового ввода телефона"""
    phone = message.text.strip()
    
    if len(phone) < 10:
        await message.answer("⚠️ Введите корректный номер телефона")
        return
    
    await process_tournament_phone(message, state, phone)


async def process_tournament_phone(message: Message, state: FSMContext, phone: str):
    """Общая обработка номера телефона для турнира"""
    data = await state.get_data()
    tournament_type = data.get('tournament_type')
    if tournament_type not in TournamentRepository.TOURNAMENT_TYPES:
        await message.answer(
            "❌ Не удалось определить турнир. Пожалуйста, выберите турнир заново.",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        await state.clear()
        return

    tournament_name = TournamentRepository.get_tournament_name(tournament_type)
    
    # Финальная проверка наличия мест
    if not TournamentRepository.is_slots_available(tournament_type):
        await message.answer(
            f"❌ К сожалению, пока вы заполняли форму, все места на {tournament_name} были заняты!",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        await state.clear()
        return
    
    await state.update_data(phone=phone)
    
    active_count = TournamentRepository.get_active_registrations_count(tournament_type)
    
    confirmation_text = (
        f"✅ Подтверждение регистрации\n\n"
        f"🏆 Турнир: {tournament_name}\n"
        f"📅 Дата и время: {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
        f"👤 Имя: {data['full_name']}\n"
        f"📱 Телефон: {phone}\n\n"
        f"📊 Вы будете участником #{active_count + 1}\n\n"
        f"Подтвердите регистрацию:"
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=get_tournament_confirmation_keyboard()
    )
    await state.set_state(TournamentStates.confirming)


@router.callback_query(F.data == "tournament_confirm", TournamentStates.confirming)
async def confirm_tournament_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации на турнир"""
    data = await state.get_data()
    tournament_type = data.get('tournament_type')
    if tournament_type not in TournamentRepository.TOURNAMENT_TYPES:
        await callback.message.edit_text("❌ Не удалось определить турнир. Пожалуйста, выберите турнир заново.")
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
        )
        await callback.answer()
        await state.clear()
        return

    tournament_name = TournamentRepository.get_tournament_name(tournament_type)
    
    # Финальная проверка наличия мест
    if not TournamentRepository.is_slots_available(tournament_type):
        await callback.message.edit_text(
            f"❌ К сожалению, все места на {tournament_name} уже заняты!"
        )
        await callback.answer()
        await state.clear()
        return
    
    # Создание регистрации
    registration = TournamentRegistration(
        id=None,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=data['full_name'],
        phone=data['phone'],
        created_at=datetime.now(),
        tournament_type=tournament_type
    )
    
    registration_id = TournamentRepository.create_registration(registration)
    active_count = TournamentRepository.get_active_registrations_count(tournament_type)
    
    # Уведомление администраторов
    admin_text = (
        f"🏆 Новая регистрация на турнир #{registration_id}\n\n"
        f"🎱 {tournament_name}\n"
        f"📅 {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
        f"👤 {data['full_name']}\n"
        f"📱 {data['phone']}\n"
        f"💬 @{callback.from_user.username or 'без username'}\n\n"
        f"📊 Всего зарегистрировано: {active_count}/{TournamentRepository.MAX_PARTICIPANTS}"
    )
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    await callback.message.edit_text(
        f"✅ Регистрация успешно завершена!\n\n"
        f"🏆 Турнир: {tournament_name}\n"
        f"📅 Дата и время: {TournamentRepository.TOURNAMENT_DATE_TEXT}\n"
        f"📋 Номер регистрации: #{registration_id}\n"
        f"👤 Имя: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n\n"
        f"📊 Вы участник #{active_count}\n\n"
        f"Ждём вас на турнире! 🎱"
    )
    
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "tournament_cancel")
async def cancel_tournament_registration_process(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса регистрации"""
    await state.clear()
    
    await callback.message.edit_text("❌ Регистрация отменена")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_user_cancel"))
async def cancel_user_tournament_registration(callback: CallbackQuery):
    """Отмена регистрации пользователем"""
    parts = callback.data.split(":")
    tournament_type = parts[1] if len(parts) > 1 else None
    registration = TournamentRepository.get_user_registration(callback.from_user.id, tournament_type)
    
    if not registration:
        await callback.answer("Регистрация не найдена", show_alert=True)
        return

    tournament_name = TournamentRepository.get_tournament_name(registration.tournament_type)
    
    if TournamentRepository.cancel_registration(registration.id):
        # Уведомление администраторов
        admin_text = (
            f"❌ Отмена регистрации на турнир #{registration.id}\n\n"
            f"🎱 {tournament_name}\n"
            f"👤 {registration.full_name}\n"
            f"💬 @{callback.from_user.username or 'без username'}\n"
            f"Причина: отменено пользователем"
        )
        
        for admin_id in settings.ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, admin_text)
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        await callback.message.edit_text(f"✅ Регистрация на {tournament_name} успешно отменена")
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
        )
        await callback.answer()
    else:
        await callback.answer("Не удалось отменить регистрацию", show_alert=True)
