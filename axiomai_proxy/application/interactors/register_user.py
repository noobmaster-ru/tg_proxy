from __future__ import annotations

from axiomai_proxy.application.dto import UserDTO
from axiomai_proxy.application.ports import SubscriptionGateway


class RegisterUser:
    def __init__(self, gateway: SubscriptionGateway) -> None:
        self._gateway = gateway

    async def execute(self, user: UserDTO) -> None:
        await self._gateway.upsert_user(user_id=user.user_id, username=user.username, first_name=user.first_name)
