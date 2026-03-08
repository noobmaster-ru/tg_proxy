from __future__ import annotations

from datetime import datetime

from axiomai_proxy.application.dto import StarsPaymentDTO
from axiomai_proxy.application.exceptions import InvalidPaymentError
from axiomai_proxy.application.ports import SubscriptionGateway


class ProcessStarsPayment:
    def __init__(self, gateway: SubscriptionGateway, subscription_days: int) -> None:
        self._gateway = gateway
        self._subscription_days = subscription_days

    async def execute(self, payment: StarsPaymentDTO) -> datetime:
        if payment.amount <= 0:
            raise InvalidPaymentError("payment amount must be positive")

        await self._gateway.upsert_user(
            user_id=payment.user.user_id,
            username=payment.user.username,
            first_name=payment.user.first_name,
        )

        expiry = await self._gateway.extend_subscription(payment.user.user_id, self._subscription_days)
        await self._gateway.add_payment(
            user_id=payment.user.user_id,
            amount=payment.amount,
            currency=payment.currency,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
        )
        return expiry
