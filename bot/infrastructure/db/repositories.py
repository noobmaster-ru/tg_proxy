from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from bot.domain.models import BankTransferDecision


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PostgresSubscriptionRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _ensure_user_exists(self, connection: AsyncConnection, user_id: int) -> None:
        now = _utcnow()
        await connection.execute(
            text(
                """
                INSERT INTO users (user_id, username, first_name, created_at, updated_at)
                VALUES (:user_id, NULL, NULL, :now, :now)
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "now": now},
        )

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        now = _utcnow()
        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO users (user_id, username, first_name, created_at, updated_at)
                    VALUES (:user_id, :username, :first_name, :now, :now)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "now": now,
                },
            )

    async def get_subscription_expiry(self, user_id: int) -> datetime | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text("SELECT expires_at FROM subscriptions WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            value = result.scalar_one_or_none()
            return value

    async def extend_subscription(self, user_id: int, days: int) -> datetime:
        if days <= 0:
            raise ValueError("days must be positive")

        now = _utcnow()
        async with self._engine.begin() as connection:
            await self._ensure_user_exists(connection, user_id)

            current_expiry_result = await connection.execute(
                text("SELECT expires_at FROM subscriptions WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            current_expiry = current_expiry_result.scalar_one_or_none()

            if current_expiry is not None and current_expiry > now:
                base = current_expiry
            else:
                base = now

            new_expiry = base + timedelta(days=days)

            await connection.execute(
                text(
                    """
                    INSERT INTO subscriptions (user_id, expires_at, updated_at)
                    VALUES (:user_id, :expires_at, :updated_at)
                    ON CONFLICT (user_id) DO UPDATE SET
                        expires_at = EXCLUDED.expires_at,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "user_id": user_id,
                    "expires_at": new_expiry,
                    "updated_at": now,
                },
            )

        return new_expiry

    async def revoke_subscription(self, user_id: int) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM subscriptions WHERE user_id = :user_id"),
                {"user_id": user_id},
            )

    async def set_proxy_link(self, proxy_link: str) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO settings (key, value)
                    VALUES ('proxy_link', :proxy_link)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                    """
                ),
                {"proxy_link": proxy_link},
            )

    async def get_proxy_link(self) -> str | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text("SELECT value FROM settings WHERE key = 'proxy_link'")
            )
            value = result.scalar_one_or_none()
            return value

    async def add_payment(
        self,
        user_id: int,
        amount: int,
        currency: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
    ) -> None:
        now = _utcnow()
        async with self._engine.begin() as connection:
            await self._ensure_user_exists(connection, user_id)
            await connection.execute(
                text(
                    """
                    INSERT INTO payments (
                        user_id,
                        telegram_payment_charge_id,
                        provider_payment_charge_id,
                        amount,
                        currency,
                        paid_at
                    ) VALUES (
                        :user_id,
                        :telegram_payment_charge_id,
                        :provider_payment_charge_id,
                        :amount,
                        :currency,
                        :paid_at
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "telegram_payment_charge_id": telegram_payment_charge_id,
                    "provider_payment_charge_id": provider_payment_charge_id,
                    "amount": amount,
                    "currency": currency,
                    "paid_at": now,
                },
            )

    async def get_pending_bank_transfer_request(self, user_id: int) -> int | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT id
                    FROM bank_transfer_requests
                    WHERE user_id = :user_id AND status = 'pending'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"user_id": user_id},
            )
            value = result.scalar_one_or_none()
            if value is None:
                return None
            return int(value)

    async def create_bank_transfer_request(self, user_id: int) -> int:
        now = _utcnow()
        async with self._engine.begin() as connection:
            await self._ensure_user_exists(connection, user_id)
            result = await connection.execute(
                text(
                    """
                    INSERT INTO bank_transfer_requests (user_id, status, reviewed_by, created_at, updated_at)
                    VALUES (:user_id, 'pending', NULL, :now, :now)
                    RETURNING id
                    """
                ),
                {"user_id": user_id, "now": now},
            )
            request_id = result.scalar_one_or_none()

        if request_id is None:
            raise RuntimeError("Failed to create bank transfer request")
        return int(request_id)

    async def approve_bank_transfer_request(self, request_id: int, admin_id: int) -> BankTransferDecision | None:
        now = _utcnow()
        async with self._engine.begin() as connection:
            update_result = await connection.execute(
                text(
                    """
                    UPDATE bank_transfer_requests
                    SET status = 'approved',
                        reviewed_by = :admin_id,
                        updated_at = :now
                    WHERE id = :request_id AND status = 'pending'
                    RETURNING user_id
                    """
                ),
                {
                    "request_id": request_id,
                    "admin_id": admin_id,
                    "now": now,
                },
            )
            updated_user_id = update_result.scalar_one_or_none()
            if updated_user_id is not None:
                return BankTransferDecision(user_id=int(updated_user_id), applied_now=True)

            existing_result = await connection.execute(
                text("SELECT user_id FROM bank_transfer_requests WHERE id = :request_id"),
                {"request_id": request_id},
            )
            existing_user_id = existing_result.scalar_one_or_none()
            if existing_user_id is None:
                return None

            return BankTransferDecision(user_id=int(existing_user_id), applied_now=False)

    async def reject_bank_transfer_request(self, request_id: int, admin_id: int) -> BankTransferDecision | None:
        now = _utcnow()
        async with self._engine.begin() as connection:
            update_result = await connection.execute(
                text(
                    """
                    UPDATE bank_transfer_requests
                    SET status = 'rejected',
                        reviewed_by = :admin_id,
                        updated_at = :now
                    WHERE id = :request_id AND status = 'pending'
                    RETURNING user_id
                    """
                ),
                {
                    "request_id": request_id,
                    "admin_id": admin_id,
                    "now": now,
                },
            )
            updated_user_id = update_result.scalar_one_or_none()
            if updated_user_id is not None:
                return BankTransferDecision(user_id=int(updated_user_id), applied_now=True)

            existing_result = await connection.execute(
                text("SELECT user_id FROM bank_transfer_requests WHERE id = :request_id"),
                {"request_id": request_id},
            )
            existing_user_id = existing_result.scalar_one_or_none()
            if existing_user_id is None:
                return None

            return BankTransferDecision(user_id=int(existing_user_id), applied_now=False)
