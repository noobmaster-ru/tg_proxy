from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.gateways.telegram import texts


def menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BUTTON_GET_PROXY), KeyboardButton(text=texts.BUTTON_SUB_STATUS)],
            [KeyboardButton(text=texts.BUTTON_BUY_SUB), KeyboardButton(text=texts.BUTTON_BANK_TRANSFER)],
            [KeyboardButton(text=texts.BUTTON_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def bank_transfer_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=texts.BUTTON_I_PAID, callback_data="bank_paid")]]
    )


def bank_transfer_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.ADMIN_ACTION_CONFIRM, callback_data=f"bank_confirm:{request_id}"),
                InlineKeyboardButton(text=texts.ADMIN_ACTION_REJECT, callback_data=f"bank_reject:{request_id}"),
            ]
        ]
    )
