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
    get_cancel_keyboard
)
from states.booking_states import TournamentStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🏆 Записаться на турнир 23.02")
async def start_tournament_registration(message: Message, state: FSMContext):
    """Начало регистрации на турнир"""
    await state.clear()
    
    # Проверка, не зарегистрирован ли уже
    existing = TournamentRepository.get_user_registration(message.from_user.id)
    if existing:
        await message.answer(
            f"✅ Вы уже зарегистрированы на турнир!\n\n"
            f"👤 Имя: {existing.full_name}\n"
            f"📱 Телефон: {existing.phone}\n"
            f"📝 Регистрация #{existing.id}\n\n"
            f"📅 Дата турнира: 23 февраля 2026\n\n"
            f"Если хотите отменить регистрацию, нажмите кнопку ниже:",
            reply_markup=get_tournament_registered_keyboard()
        )
        return
    
    # Проверка наличия свободных мест
    if not TournamentRepository.is_slots_available():
        active_count = TournamentRepository.get_active_registrations_count()
        await message.answer(
            f"❌ К сожалению, все места на турнир заняты!\n\n"
            f"Зарегистрировано: {active_count}/{TournamentRepository.MAX_PARTICIPANTS}",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        return
    
    # Информация о турнире
    active_count = TournamentRepository.get_active_registrations_count()
    remaining = TournamentRepository.MAX_PARTICIPANTS - active_count
    
    await message.answer(
        f"🏆 Регистрация на турнир\n\n"
        f"📅 Дата: 23 февраля 2026\n"
        f"👥 Свободных мест: {remaining}/{TournamentRepository.MAX_PARTICIPANTS}\n\n"
        f"Для регистрации введите ваше полное имя:",
        reply_markup=get_cancel_keyboard()
    )
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
    # Финальная проверка наличия мест
    if not TournamentRepository.is_slots_available():
        await message.answer(
            "❌ К сожалению, пока вы заполняли форму, все места были заняты!",
            reply_markup=get_main_menu_keyboard(settings.is_admin(message.from_user.id))
        )
        await state.clear()
        return
    
    await state.update_data(phone=phone)
    data = await state.get_data()
    
    active_count = TournamentRepository.get_active_registrations_count()
    
    confirmation_text = (
        f"✅ Подтверждение регистрации на турнир\n\n"
        f"🏆 Турнир: 23 февраля 2026\n"
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
    
    # Финальная проверка наличия мест
    if not TournamentRepository.is_slots_available():
        await callback.message.edit_text(
            "❌ К сожалению, все места уже заняты!"
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
        created_at=datetime.now()
    )
    
    registration_id = TournamentRepository.create_registration(registration)
    active_count = TournamentRepository.get_active_registrations_count()
    
    # Уведомление администраторов
    admin_text = (
        f"🏆 Новая регистрация на турнир #{registration_id}\n\n"
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
        f"🏆 Турнир: 23 февраля 2026\n"
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


@router.callback_query(F.data == "tournament_user_cancel")
async def cancel_user_tournament_registration(callback: CallbackQuery):
    """Отмена регистрации пользователем"""
    registration = TournamentRepository.get_user_registration(callback.from_user.id)
    
    if not registration:
        await callback.answer("Регистрация не найдена", show_alert=True)
        return
    
    if TournamentRepository.cancel_registration(registration.id):
        # Уведомление администраторов
        admin_text = (
            f"❌ Отмена регистрации на турнир #{registration.id}\n\n"
            f"👤 {registration.full_name}\n"
            f"💬 @{callback.from_user.username or 'без username'}\n"
            f"Причина: отменено пользователем"
        )
        
        for admin_id in settings.ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, admin_text)
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        await callback.message.edit_text("✅ Регистрация на турнир успешно отменена")
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(settings.is_admin(callback.from_user.id))
        )
        await callback.answer()
    else:
        await callback.answer("Не удалось отменить регистрацию", show_alert=True)
