from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway


class ListActiveSubscriptionUserIds:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> list[int]:
        return await self._gateway.list_active_subscription_user_ids()
