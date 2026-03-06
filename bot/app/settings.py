from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv


def _parse_int_set(raw_value: str) -> set[int]:
    result: set[int] = set()
    for raw_id in raw_value.split(","):
        value = raw_id.strip()
        if not value:
            continue
        result.add(int(value))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    free_user_ids: set[int]
    postgres_dsn: str
    subscription_days: int
    subscription_price_xtr: int
    subscription_price_rub: int
    support_contact: str
    bank_card_number: str
    bank_phone_number: str


def _build_postgres_dsn(
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
) -> str:
    user_encoded = quote_plus(user)
    password_encoded = quote_plus(password)
    dbname_encoded = quote_plus(dbname)
    return f"postgresql+psycopg://{user_encoded}:{password_encoded}@{host}:{port}/{dbname_encoded}"


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

    postgresql_host = os.getenv("POSTGRESQL_HOST", "postgres").strip()
    postgresql_port = int(os.getenv("POSTGRESQL_PORT", "5432"))
    postgresql_user = os.getenv("POSTGRESQL_USER", "postgres").strip()
    postgresql_password = os.getenv("POSTGRESQL_PASSWORD", "postgres")
    postgresql_dbname = os.getenv("POSTGRESQL_DBNAME", "default_db").strip()

    if not postgresql_host:
        raise ValueError("POSTGRESQL_HOST is required")
    if postgresql_port <= 0:
        raise ValueError("POSTGRESQL_PORT must be positive")
    if not postgresql_user:
        raise ValueError("POSTGRESQL_USER is required")
    if not postgresql_dbname:
        raise ValueError("POSTGRESQL_DBNAME is required")

    postgres_dsn = _build_postgres_dsn(
        host=postgresql_host,
        port=postgresql_port,
        user=postgresql_user,
        password=postgresql_password,
        dbname=postgresql_dbname,
    )

    subscription_days = int(os.getenv("SUBSCRIPTION_DAYS", "30"))
    if subscription_days <= 0:
        raise ValueError("SUBSCRIPTION_DAYS must be positive")

    subscription_price_xtr = int(os.getenv("SUBSCRIPTION_PRICE_XTR", "200"))
    if subscription_price_xtr <= 0:
        raise ValueError("SUBSCRIPTION_PRICE_XTR must be positive")

    subscription_price_rub = int(os.getenv("SUBSCRIPTION_PRICE_RUB", "299"))
    if subscription_price_rub <= 0:
        raise ValueError("SUBSCRIPTION_PRICE_RUB must be positive")

    support_contact = os.getenv("SUPPORT_CONTACT", "@your_support_username").strip()
    bank_card_number = os.getenv("BANK_CARD_NUMBER", "5536 9140 2640 7977").strip()
    bank_phone_number = os.getenv("BANK_PHONE_NUMBER", "89109681153").strip()

    if not bank_card_number:
        raise ValueError("BANK_CARD_NUMBER is required")
    if not bank_phone_number:
        raise ValueError("BANK_PHONE_NUMBER is required")

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        free_user_ids=free_user_ids,
        postgres_dsn=postgres_dsn,
        subscription_days=subscription_days,
        subscription_price_xtr=subscription_price_xtr,
        subscription_price_rub=subscription_price_rub,
        support_contact=support_contact,
        bank_card_number=bank_card_number,
        bank_phone_number=bank_phone_number,
    )
