from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from axiomai_proxy.constants import (
    ADMIN_ACTION_CONFIRM,
    ADMIN_ACTION_REJECT,
    BUTTON_I_PAID,
    CALLBACK_BANK_CONFIRM_PREFIX,
    CALLBACK_BANK_PAID,
    CALLBACK_BANK_REJECT_PREFIX,
)


def bank_transfer_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BUTTON_I_PAID, callback_data=CALLBACK_BANK_PAID)]],
    )


def bank_transfer_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=ADMIN_ACTION_CONFIRM, callback_data=f"{CALLBACK_BANK_CONFIRM_PREFIX}{request_id}"),
                InlineKeyboardButton(text=ADMIN_ACTION_REJECT, callback_data=f"{CALLBACK_BANK_REJECT_PREFIX}{request_id}"),
            ]
        ]
    )
