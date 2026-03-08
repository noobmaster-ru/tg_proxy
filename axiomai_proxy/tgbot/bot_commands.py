from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть меню"),
            BotCommand(command="help", description="Справка"),
            BotCommand(command="support", description="Поддержка"),
            BotCommand(command="paysupport", description="Поддержка по оплате"),
        ]
    )
