from __future__ import annotations

from axiomai_proxy.application.dto import UserDTO
from axiomai_proxy.application.ports import SubscriptionGateway


class CreateBankTransferRequest:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, user: UserDTO) -> int | None:
        await self._gateway.upsert_user(user_id=user.user_id, username=user.username, first_name=user.first_name)
        pending_request_id = await self._gateway.get_pending_bank_transfer_request(user.user_id)
        if pending_request_id is not None:
            return None
        return await self._gateway.create_bank_transfer_request(user.user_id)
