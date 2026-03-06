from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.app.settings import load_settings
from bot.application.services.subscription_service import SubscriptionService
from bot.gateways.telegram.router import build_router
from bot.infrastructure.db.postgres import PostgresDatabase
from bot.infrastructure.db.repositories import PostgresSubscriptionRepository


async def run() -> None:
    settings = load_settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    database = PostgresDatabase(settings.postgres_dsn)
    await database.connect()

    repository = PostgresSubscriptionRepository(database.engine)
    service = SubscriptionService(repository=repository, settings=settings)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(service))

    logging.info("Бот запущен")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await database.close()
        await bot.session.close()


def main() -> None:
    asyncio.run(run())
