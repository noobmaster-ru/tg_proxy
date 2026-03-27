from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from axiomai_proxy.application.exceptions import InvalidSubscriptionPeriodError
from axiomai_proxy.constants import CALLBACK_BANK_CONFIRM_PREFIX, CALLBACK_BANK_REJECT_PREFIX
from axiomai_proxy.infrastructure.di import AppContainer
from axiomai_proxy.infrastructure.telegram import text
from axiomai_proxy.infrastructure.telegram.common import parse_request_id, validate_proxy_link
from axiomai_proxy.tgbot.handlers.common import (
    broadcast_proxy_link_to_active_subscribers,
    is_admin,
    send_proxy_link,
)


def build_router(container: AppContainer) -> Router:
    router = Router(name="admin")

    @router.callback_query(F.data.startswith(CALLBACK_BANK_CONFIRM_PREFIX))
    async def handle_bank_confirm(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None or not is_admin(container, callback.from_user.id):
            await callback.answer("Только для администраторов", show_alert=True)
            return

        request_id = parse_request_id(callback.data, CALLBACK_BANK_CONFIRM_PREFIX)
        if request_id is None:
            await callback.answer("Некорректный request_id", show_alert=True)
            return

        approved = await container.interactors.approve_bank_transfer.execute(
            request_id=request_id,
            admin_id=callback.from_user.id,
        )
        if approved is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not approved.applied_now:
            await callback.answer("Заявка уже обработана", show_alert=True)
            if isinstance(callback.message, Message):
                await callback.message.edit_reply_markup(reply_markup=None)
            return

        if approved.new_expiry is None:
            await callback.answer("Ошибка: не удалось активировать подписку", show_alert=True)
            return

        await bot.send_message(approved.user_id, text.bank_transfer_confirmed_user(approved.new_expiry))
        await send_proxy_link(bot, container, approved.user_id)

        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                f"Заявка #{request_id} подтверждена. user_id={approved.user_id}, "
                f"expires={approved.new_expiry.strftime('%Y-%m-%d %H:%M UTC')}"
            )

        await callback.answer("Подтверждено")

    @router.callback_query(F.data.startswith(CALLBACK_BANK_REJECT_PREFIX))
    async def handle_bank_reject(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None or not is_admin(container, callback.from_user.id):
            await callback.answer("Только для администраторов", show_alert=True)
            return

        request_id = parse_request_id(callback.data, CALLBACK_BANK_REJECT_PREFIX)
        if request_id is None:
            await callback.answer("Некорректный request_id", show_alert=True)
            return

        rejected = await container.interactors.reject_bank_transfer.execute(
            request_id=request_id,
            admin_id=callback.from_user.id,
        )
        if rejected is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not rejected.applied_now:
            await callback.answer("Заявка уже обработана", show_alert=True)
            if isinstance(callback.message, Message):
                await callback.message.edit_reply_markup(reply_markup=None)
            return

        await bot.send_message(rejected.user_id, text.bank_transfer_rejected_user())

        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(f"Заявка #{request_id} отклонена. user_id={rejected.user_id}")

        await callback.answer("Отклонено")

    @router.message(Command("setproxy"))
    async def admin_set_proxy(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not is_admin(container, message.from_user.id):
            return

        proxy_link = (command.args or "").strip()
        if not proxy_link:
            await message.answer(text.admin_usage_setproxy())
            return

        if not validate_proxy_link(proxy_link):
            await message.answer(text.admin_invalid_proxy_message())
            return

        await container.interactors.set_proxy_link.execute(proxy_link)
        await message.answer(text.admin_proxy_updated_message())

    @router.message(Command("rotateproxy"))
    async def admin_rotate_proxy(message: Message, bot: Bot) -> None:
        if message.from_user is None or not is_admin(container, message.from_user.id):
            return

        if container.proxy_secret_rotator is None:
            await message.answer(text.admin_proxy_rotation_disabled_message())
            return

        await message.answer(text.admin_proxy_rotation_started_message())

        try:
            rotation_result = await container.proxy_secret_rotator.rotate()
            await container.interactors.set_proxy_link.execute(rotation_result.proxy_link)
        except Exception as error:
            await message.answer(text.admin_proxy_rotation_failed_message(str(error)))
            return

        notified_count = await broadcast_proxy_link_to_active_subscribers(bot, container)
        await message.answer(
            text.admin_proxy_rotation_done_message(
                proxy_link=rotation_result.proxy_link,
                notified_count=notified_count,
            )
        )

    @router.message(Command("grant"))
    async def admin_grant_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not is_admin(container, message.from_user.id):
            return

        args = (command.args or "").split()
        if len(args) != 2:
            await message.answer(text.admin_usage_grant())
            return

        try:
            user_id = int(args[0])
            days = int(args[1])
        except ValueError:
            await message.answer(text.admin_numbers_required_message())
            return

        try:
            new_expiry = await container.interactors.grant_subscription.execute(user_id=user_id, days=days)
        except InvalidSubscriptionPeriodError:
            await message.answer(text.admin_days_positive_message())
            return

        await message.answer(text.admin_grant_done_message(user_id, new_expiry))

    @router.message(Command("revoke"))
    async def admin_revoke_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not is_admin(container, message.from_user.id):
            return

        arg = (command.args or "").strip()
        if not arg:
            await message.answer(text.admin_usage_revoke())
            return

        try:
            user_id = int(arg)
        except ValueError:
            await message.answer(text.admin_user_id_number_required_message())
            return

        await container.interactors.revoke_subscription.execute(user_id)
        await message.answer(text.admin_revoke_done_message(user_id))

    @router.message(Command("check"))
    async def admin_check_subscription(message: Message, command: CommandObject) -> None:
        if message.from_user is None or not is_admin(container, message.from_user.id):
            return

        arg = (command.args or "").strip()
        if not arg:
            await message.answer(text.admin_usage_check())
            return

        try:
            user_id = int(arg)
        except ValueError:
            await message.answer(text.admin_user_id_number_required_message())
            return

        state = await container.interactors.get_subscription_state.execute(user_id)
        await message.answer(text.admin_check_message(user_id, state))

    return router
