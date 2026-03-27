from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from axiomai_proxy.domain.models import BankTransferDecision, SubscriptionNotificationTarget
from axiomai_proxy.infrastructure.database.gateways.base import BaseGateway


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PostgresSubscriptionGateway(BaseGateway):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

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
            return result.scalar_one_or_none()

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

            base = current_expiry if current_expiry is not None and current_expiry > now else now
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
            await connection.execute(text("DELETE FROM subscriptions WHERE user_id = :user_id"), {"user_id": user_id})

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
            result = await connection.execute(text("SELECT value FROM settings WHERE key = 'proxy_link'"))
            return result.scalar_one_or_none()

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
            return None if value is None else int(value)

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
            raise RuntimeError("failed to create bank transfer request")
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

    async def list_active_subscription_user_ids(self) -> list[int]:
        now = _utcnow()
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text("SELECT user_id FROM subscriptions WHERE expires_at > :now"),
                {"now": now},
            )
            return [int(row[0]) for row in result.fetchall()]

    async def claim_expiring_24h_notifications(self) -> list[SubscriptionNotificationTarget]:
        now = _utcnow()
        horizon = now + timedelta(hours=24)

        async with self._engine.begin() as connection:
            result = await connection.execute(
                text(
                    """
                    INSERT INTO subscription_notifications (user_id, notification_type, expires_at, sent_at)
                    SELECT s.user_id, 'expiring_24h', s.expires_at, :now
                    FROM subscriptions s
                    WHERE s.expires_at > :now AND s.expires_at <= :horizon
                    ON CONFLICT (user_id, notification_type, expires_at) DO NOTHING
                    RETURNING user_id, expires_at
                    """
                ),
                {"now": now, "horizon": horizon},
            )
            rows = result.fetchall()

        return [
            SubscriptionNotificationTarget(user_id=int(row[0]), expires_at=row[1])
            for row in rows
        ]

    async def claim_expired_notifications(self) -> list[SubscriptionNotificationTarget]:
        now = _utcnow()

        async with self._engine.begin() as connection:
            result = await connection.execute(
                text(
                    """
                    INSERT INTO subscription_notifications (user_id, notification_type, expires_at, sent_at)
                    SELECT s.user_id, 'expired', s.expires_at, :now
                    FROM subscriptions s
                    WHERE s.expires_at <= :now
                    ON CONFLICT (user_id, notification_type, expires_at) DO NOTHING
                    RETURNING user_id, expires_at
                    """
                ),
                {"now": now},
            )
            rows = result.fetchall()

        return [
            SubscriptionNotificationTarget(user_id=int(row[0]), expires_at=row[1])
            for row in rows
        ]
