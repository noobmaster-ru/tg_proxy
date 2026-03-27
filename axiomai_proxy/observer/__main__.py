from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.di import build_container, close_container
from axiomai_proxy.infrastructure.logging import setup_logging
from axiomai_proxy.infrastructure.telegram import text

logger = logging.getLogger(__name__)


async def _notify_expiring_24h(bot: Bot, container: AppContainer) -> int:
    targets = await container.interactors.claim_expiring_24h_notifications.execute()
    sent = 0
    for target in targets:
        try:
            await bot.send_message(
                target.user_id,
                text.subscription_expiring_24h_message(target.expires_at),
            )
            sent += 1
        except Exception:
            logger.exception("Не удалось отправить уведомление expiring_24h user_id=%s", target.user_id)
    return sent


async def _notify_expired(bot: Bot, container: AppContainer) -> int:
    targets = await container.interactors.claim_expired_notifications.execute()
    sent = 0
    for target in targets:
        try:
            await bot.send_message(
                target.user_id,
                text.subscription_expired_message(target.expires_at),
            )
            sent += 1
        except Exception:
            logger.exception("Не удалось отправить уведомление expired user_id=%s", target.user_id)
    return sent


async def run() -> None:
    setup_logging()
    container = await build_container()
    bot = Bot(token=container.config.bot_token)
    try:
        logger.info("Observer запущен")
        while True:
            try:
                sent_24h = await _notify_expiring_24h(bot, container)
                sent_expired = await _notify_expired(bot, container)
                if sent_24h > 0 or sent_expired > 0:
                    logger.info(
                        "Observer отправил уведомления: expiring_24h=%s expired=%s",
                        sent_24h,
                        sent_expired,
                    )
            except Exception:
                logger.exception("Ошибка observer-цикла уведомлений")

            await asyncio.sleep(container.config.observer_poll_interval_seconds)
    finally:
        await bot.session.close()
        await close_container(container)


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Observer остановлен")


if __name__ == "__main__":
    main()
