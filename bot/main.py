from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
)

from bot.config import Settings, load_settings
from bot.db import Database

router = Router()

SETTINGS: Settings
DB: Database


def _is_admin(user_id: int) -> bool:
    return user_id in SETTINGS.admin_ids


def _menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Get proxy"), KeyboardButton(text="Subscription status")],
            [KeyboardButton(text="Buy subscription"), KeyboardButton(text="Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Select an action",
    )


def _format_expiry(expiry: datetime | None) -> str:
    if expiry is None:
        return "no active subscription"

    now = datetime.now(UTC)
    if expiry <= now:
        return f"expired at {expiry.strftime('%Y-%m-%d %H:%M UTC')}"

    remaining = expiry - now
    days_left = remaining.days
    hours_left = remaining.seconds // 3600
    return f"active until {expiry.strftime('%Y-%m-%d %H:%M UTC')} ({days_left}d {hours_left}h left)"


async def _notify_admins(bot: Bot, text: str) -> None:
    for admin_id in SETTINGS.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logging.exception("Failed to notify admin %s", admin_id)


def _validate_proxy_link(link: str) -> bool:
    return link.startswith("https://t.me/proxy?") or link.startswith("tg://proxy?")


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    if message.from_user is None:
        return

    await DB.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    text = (
        "This bot gives access to your private Telegram proxy by subscription.\n\n"
        "Use menu buttons below to buy access and get proxy link."
    )
    await message.answer(text, reply_markup=_menu_keyboard())


@router.message(Command("help"))
@router.message(F.text == "Help")
async def handle_help(message: Message) -> None:
    text = (
        "User commands:\n"
        "/start - open menu\n"
        "/help - this help\n"
        "/support - contact support\n"
        "/paysupport - payment support contact\n\n"
        "Admin commands:\n"
        "/setproxy <t.me or tg:// proxy link>\n"
        "/grant <user_id> <days>\n"
        "/revoke <user_id>\n"
        "/check <user_id>"
    )
    await message.answer(text, reply_markup=_menu_keyboard())


@router.message(Command("paysupport"))
async def handle_payment_support(message: Message) -> None:
    await message.answer(f"Payment support: contact {SETTINGS.support_contact}")


@router.message(Command("support"))
async def handle_support(message: Message) -> None:
    await message.answer(f"Support contact: {SETTINGS.support_contact}")


@router.message(F.text == "Subscription status")
async def handle_subscription_status(message: Message) -> None:
    if message.from_user is None:
        return

    expiry = await DB.get_subscription_expiry(message.from_user.id)
    await message.answer(f"Your subscription is {_format_expiry(expiry)}.")


@router.message(F.text == "Get proxy")
async def handle_get_proxy(message: Message) -> None:
    if message.from_user is None:
        return

    if not await DB.has_active_subscription(message.from_user.id):
        await message.answer("No active subscription. Buy access first.")
        return

    proxy_link = await DB.get_proxy_link()
    if not proxy_link:
        await message.answer("Proxy link is not configured yet. Contact support.")
        return

    await message.answer(
        "Your proxy link:\n"
        f"{proxy_link}\n\n"
        "Tap the link and confirm connection in Telegram settings."
    )


@router.message(F.text == "Buy subscription")
async def handle_buy_subscription(message: Message) -> None:
    if message.from_user is None:
        return

    await DB.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    prices = [
        LabeledPrice(
            label=f"Proxy access for {SETTINGS.subscription_days} days",
            amount=SETTINGS.subscription_price_xtr,
        )
    ]

    payload = f"proxy_sub:{message.from_user.id}:{uuid4().hex}"
    await message.answer_invoice(
        title="Telegram proxy subscription",
        description=f"Access to private proxy for {SETTINGS.subscription_days} days",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="proxy-subscription",
    )


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.successful_payment is None:
        return

    payment = message.successful_payment

    await DB.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    new_expiry = await DB.extend_subscription(message.from_user.id, SETTINGS.subscription_days)
    await DB.add_payment(
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
    )

    await message.answer(
        "Payment received. Subscription activated.\n"
        f"Access is active until {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}.",
        reply_markup=_menu_keyboard(),
    )

    await _notify_admins(
        bot,
        (
            "New payment:\n"
            f"user_id={message.from_user.id}\n"
            f"amount={payment.total_amount} {payment.currency}\n"
            f"expires={new_expiry.strftime('%Y-%m-%d %H:%M UTC')}"
        ),
    )


@router.message(Command("setproxy"))
async def admin_set_proxy(message: Message, command: CommandObject) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id):
        return

    proxy_link = (command.args or "").strip()
    if not proxy_link:
        await message.answer("Usage: /setproxy <https://t.me/proxy?...>")
        return

    if not _validate_proxy_link(proxy_link):
        await message.answer("Proxy link must start with https://t.me/proxy? or tg://proxy?")
        return

    await DB.set_proxy_link(proxy_link)
    await message.answer("Proxy link updated.")


@router.message(Command("grant"))
async def admin_grant_subscription(message: Message, command: CommandObject) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id):
        return

    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("Usage: /grant <user_id> <days>")
        return

    try:
        user_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await message.answer("user_id and days must be numbers")
        return

    if days <= 0:
        await message.answer("days must be positive")
        return

    new_expiry = await DB.extend_subscription(user_id, days)
    await message.answer(f"Subscription updated: {user_id} -> {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}")


@router.message(Command("revoke"))
async def admin_revoke_subscription(message: Message, command: CommandObject) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id):
        return

    arg = (command.args or "").strip()
    if not arg:
        await message.answer("Usage: /revoke <user_id>")
        return

    try:
        user_id = int(arg)
    except ValueError:
        await message.answer("user_id must be a number")
        return

    await DB.revoke_subscription(user_id)
    await message.answer(f"Subscription revoked for user {user_id}")


@router.message(Command("check"))
async def admin_check_subscription(message: Message, command: CommandObject) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id):
        return

    arg = (command.args or "").strip()
    if not arg:
        await message.answer("Usage: /check <user_id>")
        return

    try:
        user_id = int(arg)
    except ValueError:
        await message.answer("user_id must be a number")
        return

    expiry = await DB.get_subscription_expiry(user_id)
    await message.answer(f"User {user_id}: {_format_expiry(expiry)}")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Use menu buttons or /help", reply_markup=_menu_keyboard())


async def main() -> None:
    global SETTINGS
    global DB

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    SETTINGS = load_settings()
    DB = Database(SETTINGS.database_path)
    await DB.init()

    bot = Bot(token=SETTINGS.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    logging.info("Bot started")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await DB.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
