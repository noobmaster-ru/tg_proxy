from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway


class SetProxyLink:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, proxy_link: str) -> None:
        await self._gateway.set_proxy_link(proxy_link)
