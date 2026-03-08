from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message

from axiomai_proxy.constants import BUTTON_GET_PROXY, BUTTON_SUB_STATUS
from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.telegram import text
from axiomai_proxy.tgbot.handlers.common import send_proxy_link


def build_router(container: AppContainer) -> Router:
    router = Router(name="subscription")

    @router.message(F.text == BUTTON_SUB_STATUS)
    async def handle_subscription_status(message: Message) -> None:
        if message.from_user is None:
            return

        state = await container.interactors.get_subscription_state.execute(message.from_user.id)
        await message.answer(f"Ваша подписка: {text.format_subscription_state(state)}")

    @router.message(F.text == BUTTON_GET_PROXY)
    async def handle_get_proxy(message: Message, bot: Bot) -> None:
        if message.from_user is None:
            return

        has_access = await container.interactors.has_proxy_access.execute(message.from_user.id)
        if not has_access:
            await message.answer(text.no_subscription_message())
            return

        await send_proxy_link(bot, container, message.chat.id)

    return router
