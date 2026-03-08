from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserDTO:
    user_id: int
    username: str | None
    first_name: str | None


@dataclass(frozen=True)
class StarsPaymentDTO:
    user: UserDTO
    amount: int
    currency: str
    telegram_payment_charge_id: str | None
    provider_payment_charge_id: str | None
