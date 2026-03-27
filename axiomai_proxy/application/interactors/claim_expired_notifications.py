from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway
from axiomai_proxy.domain.models import SubscriptionNotificationTarget


class ClaimExpiredNotifications:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> list[SubscriptionNotificationTarget]:
        return await self._gateway.claim_expired_notifications()
