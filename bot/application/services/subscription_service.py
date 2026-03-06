from __future__ import annotations

from datetime import datetime

from bot.app.settings import Settings
from bot.application.ports import SubscriptionRepository
from bot.domain.models import ApprovedBankTransfer, BankTransferDecision, SubscriptionState


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings

    def is_admin(self, user_id: int) -> bool:
        return user_id in self._settings.admin_ids

    def is_free_user(self, user_id: int) -> bool:
        return user_id in self._settings.free_user_ids

    async def register_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        await self._repository.upsert_user(user_id=user_id, username=username, first_name=first_name)

    async def get_subscription_state(self, user_id: int) -> SubscriptionState:
        if self.is_free_user(user_id):
            return SubscriptionState(is_free=True, expires_at=None)

        expiry = await self._repository.get_subscription_expiry(user_id)
        return SubscriptionState(is_free=False, expires_at=expiry)

    async def has_proxy_access(self, user_id: int) -> bool:
        state = await self.get_subscription_state(user_id)
        return state.is_active()

    async def get_proxy_link(self) -> str | None:
        return await self._repository.get_proxy_link()

    async def set_proxy_link(self, proxy_link: str) -> None:
        await self._repository.set_proxy_link(proxy_link)

    async def process_successful_stars_payment(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        amount: int,
        currency: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
    ) -> datetime:
        await self.register_user(user_id, username, first_name)

        new_expiry = await self._repository.extend_subscription(user_id, self._settings.subscription_days)
        await self._repository.add_payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
        )
        return new_expiry

    async def create_bank_transfer_request(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> int | None:
        await self.register_user(user_id, username, first_name)

        pending_request_id = await self._repository.get_pending_bank_transfer_request(user_id)
        if pending_request_id is not None:
            return None

        return await self._repository.create_bank_transfer_request(user_id)

    async def get_pending_bank_transfer_request(self, user_id: int) -> int | None:
        return await self._repository.get_pending_bank_transfer_request(user_id)

    async def approve_bank_transfer(self, request_id: int, admin_id: int) -> ApprovedBankTransfer | None:
        result = await self._repository.approve_bank_transfer_request(request_id, admin_id)
        if result is None:
            return None

        if not result.applied_now:
            return ApprovedBankTransfer(user_id=result.user_id, applied_now=False, new_expiry=None)

        expiry = await self._repository.extend_subscription(result.user_id, self._settings.subscription_days)
        return ApprovedBankTransfer(user_id=result.user_id, applied_now=True, new_expiry=expiry)

    async def reject_bank_transfer(self, request_id: int, admin_id: int) -> BankTransferDecision | None:
        return await self._repository.reject_bank_transfer_request(request_id, admin_id)

    async def grant_subscription(self, user_id: int, days: int) -> datetime:
        return await self._repository.extend_subscription(user_id, days)

    async def revoke_subscription(self, user_id: int) -> None:
        await self._repository.revoke_subscription(user_id)
