from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway


class RevokeSubscription:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, user_id: int) -> None:
        await self._gateway.revoke_subscription(user_id)
