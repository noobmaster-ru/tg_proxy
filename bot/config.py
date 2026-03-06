from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _parse_int_set(raw_value: str) -> set[int]:
    result: set[int] = set()
    for raw_id in raw_value.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        result.add(int(raw_id))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    free_user_ids: set[int]
    database_path: str
    subscription_days: int
    subscription_price_xtr: int
    support_contact: str


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    admin_raw = os.getenv("ADMIN_IDS", "").strip()
    if not admin_raw:
        raise ValueError("ADMIN_IDS is required")

    admin_ids = _parse_int_set(admin_raw)
    if not admin_ids:
        raise ValueError("ADMIN_IDS must contain at least one numeric Telegram user id")

    free_user_ids = _parse_int_set(os.getenv("FREE_USER_IDS", "694144143,547299317"))

    database_path = os.getenv("DATABASE_PATH", "data/subscriptions.db").strip() or "data/subscriptions.db"

    subscription_days = int(os.getenv("SUBSCRIPTION_DAYS", "30"))
    if subscription_days <= 0:
        raise ValueError("SUBSCRIPTION_DAYS must be positive")

    subscription_price_xtr = int(os.getenv("SUBSCRIPTION_PRICE_XTR", "200"))
    if subscription_price_xtr <= 0:
        raise ValueError("SUBSCRIPTION_PRICE_XTR must be positive")

    support_contact = os.getenv("SUPPORT_CONTACT", "@your_support_username").strip()

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        free_user_ids=free_user_ids,
        database_path=database_path,
        subscription_days=subscription_days,
        subscription_price_xtr=subscription_price_xtr,
        support_contact=support_contact,
    )
