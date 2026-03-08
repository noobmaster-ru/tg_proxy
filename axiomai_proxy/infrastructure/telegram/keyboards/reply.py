from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from axiomai_proxy.constants import BUTTON_BANK_TRANSFER, BUTTON_BUY_SUB, BUTTON_GET_PROXY, BUTTON_HELP, BUTTON_SUB_STATUS


def menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_GET_PROXY), KeyboardButton(text=BUTTON_SUB_STATUS)],
            [KeyboardButton(text=BUTTON_BUY_SUB), KeyboardButton(text=BUTTON_BANK_TRANSFER)],
            [KeyboardButton(text=BUTTON_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
