"""
Middleware для незаметного обновления клавиатуры после перезапуска бота.

При первом сообщении от пользователя после рестарта добавляет актуальную
клавиатуру к ответу хендлера — пользователь ничего не замечает.
"""
from typing import Callable, Dict, Any, Awaitable, Set

from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import settings
from keyboards.keyboards import get_main_menu_keyboard


# Множество user_id, которые уже получили обновлённую клавиатуру.
# Хранится в памяти процесса — при перезапуске Docker-контейнера
# сбрасывается автоматически, что нам и нужно.
_refreshed_users: Set[int] = set()


class KeyboardRefreshMiddleware(BaseMiddleware):
    """
    После перезапуска бота незаметно обновляет Reply-клавиатуру
    при первом же сообщении от пользователя.
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Работаем только с обычными сообщениями
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id

        # Если пользователь уже получил свежую клавиатуру — пропускаем
        if user_id in _refreshed_users:
            return await handler(event, data)

        # Помечаем пользователя как обновлённого до вызова хендлера,
        # чтобы избежать повторной отправки при параллельных запросах
        _refreshed_users.add(user_id)

        # Проверяем FSM-состояние: если пользователь в середине какого-то
        # флоу (бронирование, турнир и т.д.) — не вмешиваемся, иначе сломаем UX
        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state is not None:
                return await handler(event, data)

        # Пользователь в главном меню — тихо шлём клавиатуру
        is_admin = settings.is_admin(user_id)
        await event.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(is_admin)
        )

        return await handler(event, data)
