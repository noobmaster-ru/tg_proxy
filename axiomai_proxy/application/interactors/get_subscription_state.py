from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway
from axiomai_proxy.domain.models import SubscriptionState


class GetSubscriptionState:
    def __init__(self, gateway: SubscriptionGateway, free_user_ids: set[int]) -> None:
        self._gateway = gateway
        self._free_user_ids = free_user_ids

    async def execute(self, user_id: int) -> SubscriptionState:
        if user_id in self._free_user_ids:
            return SubscriptionState(is_free=True, expires_at=None)

        expiry = await self._gateway.get_subscription_expiry(user_id)
        return SubscriptionState(is_free=False, expires_at=expiry)
