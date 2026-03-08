from __future__ import annotations

from axiomai_proxy.application.interactors.get_subscription_state import GetSubscriptionState


class HasProxyAccess:
    def __init__(self, get_subscription_state: GetSubscriptionState) -> None:
        self._get_subscription_state = get_subscription_state

    async def execute(self, user_id: int) -> bool:
        state = await self._get_subscription_state.execute(user_id)
        return state.is_active()
