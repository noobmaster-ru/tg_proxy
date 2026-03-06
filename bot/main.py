from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

KIRILL_CARD_NUMBER = "5536 9140 2640 7977"
KIRILL_PHONE_NUMBER = "89109681153"


def _is_admin(user_id: int) -> bool:
    return user_id in SETTINGS.admin_ids


def _is_free_user(user_id: int) -> bool:
    return user_id in SETTINGS.free_user_ids


async def _has_proxy_access(user_id: int) -> bool:
    return _is_free_user(user_id) or await DB.has_active_subscription(user_id)


def _menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Get proxy"), KeyboardButton(text="Subscription status")],
            [KeyboardButton(text="Buy subscription"), KeyboardButton(text="Bank transfer")],
            [KeyboardButton(text="Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Select an action",
    )


def _bank_transfer_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="I paid", callback_data="bank_paid")]]
    )


def _bank_transfer_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Confirm", callback_data=f"bank_confirm:{request_id}"),
                InlineKeyboardButton(text="Reject", callback_data=f"bank_reject:{request_id}"),
            ]
        ]
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


async def _notify_admins(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    for admin_id in SETTINGS.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            logging.exception("Failed to notify admin %s", admin_id)


def _validate_proxy_link(link: str) -> bool:
    return link.startswith("https://t.me/proxy?") or link.startswith("tg://proxy?")


def _parse_request_id(data: str | None, prefix: str) -> int | None:
    if data is None or not data.startswith(prefix):
        return None

    raw_request_id = data.split(":", maxsplit=1)[1]
    try:
        return int(raw_request_id)
    except ValueError:
        return None


async def _send_proxy_link_to_chat(bot: Bot, chat_id: int) -> None:
    proxy_link = await DB.get_proxy_link()
    if not proxy_link:
        await bot.send_message(chat_id, "Proxy link is not configured yet. Contact support.")
        return

    await bot.send_message(
        chat_id,
        "Your proxy link:\n"
        f"{proxy_link}\n\n"
        "Tap the link and confirm connection in Telegram settings.",
    )


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
        "Buttons:\n"
        "Buy subscription - pay with Telegram Stars\n"
        "Bank transfer - pay by card/SBP and wait for admin confirmation\n\n"
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

    if _is_free_user(message.from_user.id):
        await message.answer("Your subscription is active without payment (whitelisted account).")
        return

    expiry = await DB.get_subscription_expiry(message.from_user.id)
    await message.answer(f"Your subscription is {_format_expiry(expiry)}.")


@router.message(F.text == "Get proxy")
async def handle_get_proxy(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return

    if not await _has_proxy_access(message.from_user.id):
        await message.answer("No active subscription. Buy access first.")
        return

    await _send_proxy_link_to_chat(bot, message.chat.id)


@router.message(F.text == "Buy subscription")
async def handle_buy_subscription(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return

    await DB.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if _is_free_user(message.from_user.id):
        await message.answer("For your account subscription is enabled without payment.")
        await _send_proxy_link_to_chat(bot, message.chat.id)
        return

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


@router.message(F.text == "Bank transfer")
async def handle_bank_transfer(message: Message) -> None:
    if message.from_user is None:
        return

    await DB.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if _is_free_user(message.from_user.id):
        await message.answer("For your account subscription is enabled without payment.")
        return

    pending_request_id = await DB.get_pending_bank_transfer_request(message.from_user.id)
    if pending_request_id is not None:
        await message.answer(
            "You already have a pending payment request. "
            "Wait for admin confirmation or contact support."
        )
        return

    await message.answer(
        "Pay for subscription by bank transfer:\n"
        f"Card number: {KIRILL_CARD_NUMBER}\n"
        f"Phone (SBP): {KIRILL_PHONE_NUMBER}\n\n"
        f"After payment, press 'I paid'. Subscription term: {SETTINGS.subscription_days} days.",
        reply_markup=_bank_transfer_user_keyboard(),
    )


@router.callback_query(F.data == "bank_paid")
async def handle_bank_paid(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user is None:
        await callback.answer("Unknown user", show_alert=True)
        return

    await DB.upsert_user(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    if _is_free_user(callback.from_user.id):
        await callback.answer("For your account access is already free", show_alert=True)
        return

    pending_request_id = await DB.get_pending_bank_transfer_request(callback.from_user.id)
    if pending_request_id is not None:
        await callback.answer("Request is already pending", show_alert=True)
        return

    request_id = await DB.create_bank_transfer_request(callback.from_user.id)
    username = f"@{callback.from_user.username}" if callback.from_user.username else "-"

    await _notify_admins(
        bot,
        (
            "Bank transfer payment request\n"
            f"request_id={request_id}\n"
            f"user_id={callback.from_user.id}\n"
            f"username={username}\n\n"
            "Confirm only after money is received."
        ),
        reply_markup=_bank_transfer_admin_keyboard(request_id),
    )

    if callback.message is not None:
        await callback.message.answer("Payment request sent to admin. Wait for confirmation.")
    else:
        await bot.send_message(callback.from_user.id, "Payment request sent to admin. Wait for confirmation.")

    await callback.answer("Sent for review")


@router.callback_query(F.data.startswith("bank_confirm:"))
async def handle_bank_confirm(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user is None or not _is_admin(callback.from_user.id):
        await callback.answer("Admins only", show_alert=True)
        return

    request_id = _parse_request_id(callback.data, "bank_confirm:")
    if request_id is None:
        await callback.answer("Invalid request id", show_alert=True)
        return

    result = await DB.approve_bank_transfer_request(request_id, callback.from_user.id)
    if result is None:
        await callback.answer("Request not found", show_alert=True)
        return

    user_id, applied_now = result
    if not applied_now:
        await callback.answer("Request already processed", show_alert=True)
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    new_expiry = await DB.extend_subscription(user_id, SETTINGS.subscription_days)

    await bot.send_message(
        user_id,
        "Bank transfer confirmed. Subscription activated.\n"
        f"Access is active until {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}.",
    )

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"Confirmed request #{request_id}. user_id={user_id}, "
            f"expires={new_expiry.strftime('%Y-%m-%d %H:%M UTC')}"
        )

    await callback.answer("Confirmed")


@router.callback_query(F.data.startswith("bank_reject:"))
async def handle_bank_reject(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user is None or not _is_admin(callback.from_user.id):
        await callback.answer("Admins only", show_alert=True)
        return

    request_id = _parse_request_id(callback.data, "bank_reject:")
    if request_id is None:
        await callback.answer("Invalid request id", show_alert=True)
        return

    result = await DB.reject_bank_transfer_request(request_id, callback.from_user.id)
    if result is None:
        await callback.answer("Request not found", show_alert=True)
        return

    user_id, applied_now = result
    if not applied_now:
        await callback.answer("Request already processed", show_alert=True)
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await bot.send_message(
        user_id,
        "Bank transfer request was rejected. If you already paid, contact support.",
    )

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"Rejected request #{request_id}. user_id={user_id}")

    await callback.answer("Rejected")


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

    if _is_free_user(user_id):
        await message.answer(f"User {user_id}: free access enabled (no payment required)")
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
