from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway
from axiomai_proxy.domain.models import BankTransferDecision


class RejectBankTransfer:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, request_id: int, admin_id: int) -> BankTransferDecision | None:
        return await self._gateway.reject_bank_transfer_request(request_id=request_id, admin_id=admin_id)
