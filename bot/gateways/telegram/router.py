from __future__ import annotations

import logging
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.application.services.subscription_service import SubscriptionService
from bot.domain.models import SubscriptionState
from bot.gateways.telegram import texts
from bot.gateways.telegram.keyboards import (
    bank_transfer_admin_keyboard,
    bank_transfer_user_keyboard,
    menu_keyboard,
)


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


def _username_or_dash(username: str | None) -> str:
    if not username:
        return "-"
    return f"@{username}"


async def _notify_admins(
    bot: Bot,
    service: SubscriptionService,
    text: str,
    reply_markup=None,
) -> None:
    for admin_id in service.settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            logging.exception("Не удалось отправить уведомление админу %s", admin_id)


async def _send_proxy_link(bot: Bot, service: SubscriptionService, chat_id: int) -> bool:
    proxy_link = await service.get_proxy_link()
    if not proxy_link:
        await bot.send_message(chat_id, texts.proxy_not_configured_message())
        return False

    await bot.send_message(chat_id, texts.proxy_link_message(proxy_link))
    return True


def build_router(service: SubscriptionService) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if message.from_user is None:
            return

        await service.register_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await message.answer(texts.start_message(), reply_markup=menu_keyboard())

    @router.message(Command("help"))
    @router.message(F.text == texts.BUTTON_HELP)
    async def handle_help(message: Message) -> None:
        await message.answer(texts.help_message(), reply_markup=menu_keyboard())

    @router.message(Command("support"))
    async def handle_support(message: Message) -> None:
        await message.answer(texts.support_message(service.settings.support_contact))

    @router.message(Command("paysupport"))
    async def handle_paysupport(message: Message) -> None:
        await message.answer(texts.payment_support_message(service.settings.support_contact))

    @router.message(F.text == texts.BUTTON_SUB_STATUS)
    async def handle_subscription_status(message: Message) -> None:
        if message.from_user is None:
            return

        state = await service.get_subscription_state(message.from_user.id)
        await message.answer(f"Ваша подписка: {texts.format_subscription_state(state)}")

    @router.message(F.text == texts.BUTTON_GET_PROXY)
    async def handle_get_proxy(message: Message, bot: Bot) -> None:
        if message.from_user is None:
            return

        if not await service.has_proxy_access(message.from_user.id):
            await message.answer(texts.no_subscription_message())
            return

        await _send_proxy_link(bot, service, message.chat.id)

    @router.message(F.text == texts.BUTTON_BUY_SUB)
    async def handle_buy_subscription(message: Message, bot: Bot) -> None:
        if message.from_user is None:
            return

        await service.register_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        if service.is_free_user(message.from_user.id):
            await message.answer(texts.free_access_message(), reply_markup=menu_keyboard())
            await _send_proxy_link(bot, service, message.chat.id)
            return

        prices = [
            LabeledPrice(
                label=f"Доступ к прокси на {service.settings.subscription_days} дней",
                amount=service.settings.subscription_price_xtr,
            )
        ]

        payload = f"proxy_sub:{message.from_user.id}:{uuid4().hex}"
        await message.answer_invoice(
            title="Подписка на Telegram-прокси",
            description=f"Доступ к приватному прокси на {service.settings.subscription_days} дней",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="proxy-subscription",
        )

    @router.message(F.text == texts.BUTTON_BANK_TRANSFER)
    async def handle_bank_transfer(message: Message) -> None:
        if message.from_user is None:
            return

        await service.register_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        if service.is_free_user(message.from_user.id):
            await message.answer(texts.free_access_message())
            return

        pending_request = await service.get_pending_bank_transfer_request(message.from_user.id)
        if pending_request is not None:
            await message.answer(texts.bank_transfer_pending_exists_message())
            return

        await message.answer(
            texts.bank_transfer_instructions(
                card=service.settings.bank_card_number,
                phone=service.settings.bank_phone_number,
                amount_rub=service.settings.subscription_price_rub,
                days=service.settings.subscription_days,
            ),
            reply_markup=bank_transfer_user_keyboard(),
        )

    @router.callback_query(F.data == "bank_paid")
    async def handle_bank_paid(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None:
            await callback.answer("Пользователь не определен", show_alert=True)
            return

        if service.is_free_user(callback.from_user.id):
            await callback.answer("Для вашего аккаунта доступ уже бесплатный", show_alert=True)
            return

        request_id = await service.create_bank_transfer_request(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        if request_id is None:
            await callback.answer("Заявка уже находится в обработке", show_alert=True)
            return

        await _notify_admins(
            bot,
            service,
            texts.bank_transfer_admin_notification(
                request_id=request_id,
                user_id=callback.from_user.id,
                username=_username_or_dash(callback.from_user.username),
                amount_rub=service.settings.subscription_price_rub,
                days=service.settings.subscription_days,
            ),
            reply_markup=bank_transfer_admin_keyboard(request_id),
        )

        if callback.message is not None:
            await callback.message.answer(texts.bank_transfer_request_sent_message(), reply_markup=menu_keyboard())
        else:
            await bot.send_message(callback.from_user.id, texts.bank_transfer_request_sent_message())

        await callback.answer("Отправлено")

    @router.callback_query(F.data.startswith("bank_confirm:"))
    async def handle_bank_confirm(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None or not service.is_admin(callback.from_user.id):
            await callback.answer("Только для администраторов", show_alert=True)
            return

        request_id = _parse_request_id(callback.data, "bank_confirm:")
        if request_id is None:
            await callback.answer("Некорректный request_id", show_alert=True)
            return

        approved = await service.approve_bank_transfer(request_id=request_id, admin_id=callback.from_user.id)
        if approved is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not approved.applied_now:
            await callback.answer("Заявка уже обработана", show_alert=True)
            if callback.message is not None:
                await callback.message.edit_reply_markup(reply_markup=None)
            return

        if approved.new_expiry is None:
            await callback.answer("Ошибка: не удалось активировать подписку", show_alert=True)
            return

        await bot.send_message(approved.user_id, texts.bank_transfer_confirmed_user(approved.new_expiry))

        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                f"Заявка #{request_id} подтверждена. user_id={approved.user_id}, "
                f"expires={approved.new_expiry.strftime('%Y-%m-%d %H:%M UTC')}"
            )

        await callback.answer("Подтверждено")

    @router.callback_query(F.data.startswith("bank_reject:"))
    async def handle_bank_reject(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None or not service.is_admin(callback.from_user.id):
            await callback.answer("Только для администраторов", show_alert=True)
            return

        request_id = _parse_request_id(callback.data, "bank_reject:")
        if request_id is None:
            await callback.answer("Некорректный request_id", show_alert=True)
            return

        rejected = await service.reject_bank_transfer(request_id=request_id, admin_id=callback.from_user.id)
        if rejected is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not rejected.applied_now:
            await callback.answer("Заявка уже обработана", show_alert=True)
            if callback.message is not None:
                await callback.message.edit_reply_markup(reply_markup=None)
            return

        await bot.send_message(rejected.user_id, texts.bank_transfer_rejected_user())

        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(f"Заявка #{request_id} отклонена. user_id={rejected.user_id}")

        await callback.answer("Отклонено")

    @router.pre_checkout_query()
    async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @router.message(F.successful_payment)
    async def handle_successful_payment(message: Message, bot: Bot) -> None:
        if message.from_user is None or message.successful_payment is None:
            return

        payment = message.successful_payment
        expiry = await service.process_successful_stars_payment(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            amount=payment.total_amount,
            currency=payment.currency,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
        )

        await message.answer(texts.stars_payment_success_message(expiry), reply_markup=menu_keyboard())

        await _notify_admins(
            bot,
            service,
            texts.stars_payment_admin_notification(
                user_id=message.from_user.id,
                amount=payment.total_amount,
                currency=payment.currency,
                expiry=expiry,
            ),
        )

    @router.message(Command("setproxy"))
    async def admin_set_proxy(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not service.is_admin(message.from_user.id):
            return

        proxy_link = (command.args or "").strip()
        if not proxy_link:
            await message.answer(texts.admin_usage_setproxy())
            return

        if not _validate_proxy_link(proxy_link):
            await message.answer(texts.admin_invalid_proxy_message())
            return

        await service.set_proxy_link(proxy_link)
        await message.answer(texts.admin_proxy_updated_message())

    @router.message(Command("grant"))
    async def admin_grant_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not service.is_admin(message.from_user.id):
            return

        args = (command.args or "").split()
        if len(args) != 2:
            await message.answer(texts.admin_usage_grant())
            return

        try:
            user_id = int(args[0])
            days = int(args[1])
        except ValueError:
            await message.answer(texts.admin_numbers_required_message())
            return

        if days <= 0:
            await message.answer(texts.admin_days_positive_message())
            return

        new_expiry = await service.grant_subscription(user_id=user_id, days=days)
        await message.answer(texts.admin_grant_done_message(user_id, new_expiry))

    @router.message(Command("revoke"))
    async def admin_revoke_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not service.is_admin(message.from_user.id):
            return

        arg = (command.args or "").strip()
        if not arg:
            await message.answer(texts.admin_usage_revoke())
            return

        try:
            user_id = int(arg)
        except ValueError:
            await message.answer(texts.admin_user_id_number_required_message())
            return

        await service.revoke_subscription(user_id)
        await message.answer(texts.admin_revoke_done_message(user_id))

    @router.message(Command("check"))
    async def admin_check_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not service.is_admin(message.from_user.id):
            return

        arg = (command.args or "").strip()
        if not arg:
            await message.answer(texts.admin_usage_check())
            return

        try:
            user_id = int(arg)
        except ValueError:
            await message.answer(texts.admin_user_id_number_required_message())
            return

        state: SubscriptionState = await service.get_subscription_state(user_id)
        await message.answer(texts.admin_check_message(user_id, state))

    @router.message()
    async def fallback(message: Message) -> None:
        await message.answer(texts.fallback_message(), reply_markup=menu_keyboard())

    return router
