from __future__ import annotations

from aiogram import Router

from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.tgbot.handlers import admin, fallback, payments, start, subscription


def build_router(container: AppContainer) -> Router:
    router = Router(name="root")
    router.include_router(start.build_router(container))
    router.include_router(subscription.build_router(container))
    router.include_router(payments.build_router(container))
    router.include_router(admin.build_router(container))
    router.include_router(fallback.build_router())
    return router
