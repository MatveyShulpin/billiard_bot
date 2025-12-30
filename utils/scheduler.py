"""
Планировщик периодических задач
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database.repository import HoldRepository

logger = logging.getLogger(__name__)


async def cleanup_holds_job():
    """Задача очистки истёкших holds"""
    try:
        deleted_count = HoldRepository.cleanup_expired()
        if deleted_count > 0:
            logger.info(f"Очищено {deleted_count} истёкших holds")
    except Exception as e:
        logger.error(f"Ошибка при очистке holds: {e}", exc_info=True)


async def start_scheduler() -> AsyncIOScheduler:
    """Запуск планировщика задач"""
    scheduler = AsyncIOScheduler()
    
    # Очистка holds каждые 2 минуты
    scheduler.add_job(
        cleanup_holds_job,
        trigger=IntervalTrigger(minutes=2),
        id='cleanup_holds',
        name='Очистка истёкших holds',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Планировщик задач запущен")
    
    return scheduler
