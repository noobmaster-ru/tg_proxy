from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway


class GetPendingBankTransferRequest:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, user_id: int) -> int | None:
        return await self._gateway.get_pending_bank_transfer_request(user_id)
