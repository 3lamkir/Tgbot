"""
Главный файл запуска бота.
Запуск: python main.py
"""

import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import Database
from handlers import start, price, cart, orders, admin, support

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан! Используй /addapibot в консоли.")

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация БД
    db = Database()
    db.init()

    # Передаём db в роутеры через workflow_data
    dp["db"] = db

    # Регистрируем роутеры
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(price.router)
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(support.router)

    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())