from __future__ import annotations

from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from axiomai_proxy.application.dto import StarsPaymentDTO, UserDTO
from axiomai_proxy.constants import BUTTON_BANK_TRANSFER, BUTTON_BUY_SUB, CALLBACK_BANK_PAID
from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.telegram import text
from axiomai_proxy.infrastructure.telegram.keyboards import (
    bank_transfer_admin_keyboard,
    bank_transfer_user_keyboard,
    menu_keyboard,
)
from axiomai_proxy.tgbot.handlers.common import is_free_user, notify_admins, send_proxy_link


def build_router(container: AppContainer) -> Router:
    router = Router(name="payments")

    @router.message(F.text == BUTTON_BUY_SUB)
    async def handle_buy_subscription(message: Message, bot: Bot) -> None:
        if message.from_user is None:
            return

        user = UserDTO(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await container.interactors.register_user.execute(user)

        if is_free_user(container, message.from_user.id):
            await message.answer(text.free_access_message(), reply_markup=menu_keyboard())
            await send_proxy_link(bot, container, message.chat.id)
            return

        prices = [
            LabeledPrice(
                label=f"Доступ к прокси на {container.config.subscription_days} дней",
                amount=container.config.subscription_price_xtr,
            )
        ]

        payload = f"proxy_sub:{message.from_user.id}:{uuid4().hex}"
        await message.answer_invoice(
            title="Подписка на Telegram-прокси",
            description=f"Доступ к приватному прокси на {container.config.subscription_days} дней",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="proxy-subscription",
        )

    @router.message(F.text == BUTTON_BANK_TRANSFER)
    async def handle_bank_transfer(message: Message) -> None:
        if message.from_user is None:
            return

        user = UserDTO(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await container.interactors.register_user.execute(user)

        if is_free_user(container, message.from_user.id):
            await message.answer(text.free_access_message())
            return

        pending_request = await container.interactors.get_pending_bank_transfer_request.execute(message.from_user.id)
        if pending_request is not None:
            await message.answer(text.bank_transfer_pending_exists_message())
            return

        await message.answer(
            text.bank_transfer_instructions(
                card=container.config.bank_card_number,
                phone=container.config.bank_phone_number,
                amount_rub=container.config.subscription_price_rub,
                days=container.config.subscription_days,
            ),
            reply_markup=bank_transfer_user_keyboard(),
        )

    @router.callback_query(F.data == CALLBACK_BANK_PAID)
    async def handle_bank_paid(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None:
            await callback.answer("Пользователь не определен", show_alert=True)
            return

        if is_free_user(container, callback.from_user.id):
            await callback.answer("Для вашего аккаунта доступ уже бесплатный", show_alert=True)
            return

        request_id = await container.interactors.create_bank_transfer_request.execute(
            UserDTO(
                user_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )
        )
        if request_id is None:
            await callback.answer("Заявка уже находится в обработке", show_alert=True)
            return

        await notify_admins(
            bot,
            container,
            text.bank_transfer_admin_notification(
                request_id=request_id,
                user_id=callback.from_user.id,
                username=f"@{callback.from_user.username}" if callback.from_user.username else "-",
                amount_rub=container.config.subscription_price_rub,
                days=container.config.subscription_days,
            ),
            reply_markup=bank_transfer_admin_keyboard(request_id),
        )

        if isinstance(callback.message, Message):
            await callback.message.answer(text.bank_transfer_request_sent_message(), reply_markup=menu_keyboard())
        else:
            await bot.send_message(callback.from_user.id, text.bank_transfer_request_sent_message())

        await callback.answer("Отправлено")

    @router.pre_checkout_query()
    async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @router.message(F.successful_payment)
    async def handle_successful_payment(message: Message, bot: Bot) -> None:
        if message.from_user is None or message.successful_payment is None:
            return

        payment = message.successful_payment
        expiry = await container.interactors.process_stars_payment.execute(
            StarsPaymentDTO(
                user=UserDTO(
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                ),
                amount=payment.total_amount,
                currency=payment.currency,
                telegram_payment_charge_id=payment.telegram_payment_charge_id,
                provider_payment_charge_id=payment.provider_payment_charge_id,
            )
        )

        await message.answer(text.stars_payment_success_message(expiry), reply_markup=menu_keyboard())

        await notify_admins(
            bot,
            container,
            text.stars_payment_admin_notification(
                user_id=message.from_user.id,
                amount=payment.total_amount,
                currency=payment.currency,
                expiry=expiry,
            ),
        )

    return router
