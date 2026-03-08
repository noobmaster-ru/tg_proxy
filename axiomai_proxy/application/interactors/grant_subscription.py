from __future__ import annotations

from datetime import datetime

from axiomai_proxy.application.exceptions import InvalidSubscriptionPeriodError
from axiomai_proxy.application.ports import SubscriptionGateway


class GrantSubscription:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, user_id: int, days: int) -> datetime:
        if days <= 0:
            raise InvalidSubscriptionPeriodError("days must be positive")
        return await self._gateway.extend_subscription(user_id=user_id, days=days)
