from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot

from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.telegram import text


def is_admin(container: AppContainer, user_id: int) -> bool:
    return user_id in container.config.admin_ids


def is_free_user(container: AppContainer, user_id: int) -> bool:
    return user_id in container.config.free_user_ids


async def notify_admins(
    bot: Bot,
    container: AppContainer,
    message_text: str,
    reply_markup: Any = None,
) -> None:
    for admin_id in container.config.admin_ids:
        try:
            await bot.send_message(admin_id, message_text, reply_markup=reply_markup)
        except Exception:
            logging.exception("Не удалось отправить уведомление админу %s", admin_id)


async def send_proxy_link(bot: Bot, container: AppContainer, chat_id: int) -> bool:
    proxy_link = await container.interactors.get_proxy_link.execute()
    if not proxy_link:
        await bot.send_message(chat_id, text.proxy_not_configured_message())
        return False

    await bot.send_message(chat_id, text.proxy_link_message(proxy_link))
    return True
