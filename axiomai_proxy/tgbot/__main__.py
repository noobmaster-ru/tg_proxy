from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from axiomai_proxy.infrastructure.di import build_container, close_container
from axiomai_proxy.infrastructure.logging import setup_logging
from axiomai_proxy.tgbot.bot_commands import set_bot_commands
from axiomai_proxy.tgbot.handlers import build_router


async def run() -> None:
    setup_logging()

    container = await build_container()
    bot = Bot(token=container.config.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(container))

    await set_bot_commands(bot)

    logging.info("Бот запущен")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await close_container(container)
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
