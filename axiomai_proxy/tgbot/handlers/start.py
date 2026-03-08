from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from axiomai_proxy.application.dto import UserDTO
from axiomai_proxy.constants import BUTTON_HELP
from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.telegram.keyboards import menu_keyboard
from axiomai_proxy.infrastructure.telegram import text


def build_router(container: AppContainer) -> Router:
    router = Router(name="start")

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if message.from_user is None:
            return

        await container.interactors.register_user.execute(
            UserDTO(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
        )
        await message.answer(text.start_message(), reply_markup=menu_keyboard())

    @router.message(Command("help"))
    @router.message(F.text == BUTTON_HELP)
    async def handle_help(message: Message) -> None:
        await message.answer(text.help_message(), reply_markup=menu_keyboard())

    @router.message(Command("support"))
    async def handle_support(message: Message) -> None:
        await message.answer(text.support_message(container.config.support_contact))

    @router.message(Command("paysupport"))
    async def handle_paysupport(message: Message) -> None:
        await message.answer(text.payment_support_message(container.config.support_contact))

    return router
