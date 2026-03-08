from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway


class GetProxyLink:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> str | None:
        return await self._gateway.get_proxy_link()
