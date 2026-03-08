from __future__ import annotations

from axiomai_proxy.application.ports import SubscriptionGateway
from axiomai_proxy.domain.models import ApprovedBankTransfer


class ApproveBankTransfer:
    def __init__(self, gateway: SubscriptionGateway, subscription_days: int) -> None:
        self._gateway = gateway
        self._subscription_days = subscription_days

    async def execute(self, request_id: int, admin_id: int) -> ApprovedBankTransfer | None:
        result = await self._gateway.approve_bank_transfer_request(request_id=request_id, admin_id=admin_id)
        if result is None:
            return None

        if not result.applied_now:
            return ApprovedBankTransfer(user_id=result.user_id, applied_now=False, new_expiry=None)

        expiry = await self._gateway.extend_subscription(result.user_id, self._subscription_days)
        return ApprovedBankTransfer(user_id=result.user_id, applied_now=True, new_expiry=expiry)
