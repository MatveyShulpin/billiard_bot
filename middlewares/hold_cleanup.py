"""
Middleware для автоматической очистки истёкших holds
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.repository import HoldRepository


class HoldCleanupMiddleware(BaseMiddleware):
    """Middleware для очистки истёкших holds перед обработкой"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Очистка истёкших holds
        HoldRepository.cleanup_expired()
        
        # Продолжение обработки
        return await handler(event, data)
