from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from axiomai_proxy.infrastructure.telegram import text
from axiomai_proxy.infrastructure.telegram.keyboards import menu_keyboard


def build_router() -> Router:
    router = Router(name="fallback")

    @router.message()
    async def fallback(message: Message) -> None:
        await message.answer(text.fallback_message(), reply_markup=menu_keyboard())

    return router
