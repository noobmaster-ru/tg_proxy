from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                telegram_payment_charge_id TEXT,
                provider_payment_charge_id TEXT,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                paid_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bank_transfer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                reviewed_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not initialized")
        return self._conn

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        now = _utcnow().isoformat()
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
            """,
            (user_id, username, first_name, now, now),
        )
        await self.conn.commit()

    async def _ensure_user_exists(self, user_id: int) -> None:
        now_iso = _utcnow().isoformat()
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at, updated_at)
            VALUES (?, NULL, NULL, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, now_iso, now_iso),
        )

    async def get_subscription_expiry(self, user_id: int) -> datetime | None:
        cursor = await self.conn.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None

        return datetime.fromisoformat(row["expires_at"])

    async def has_active_subscription(self, user_id: int) -> bool:
        expiry = await self.get_subscription_expiry(user_id)
        return expiry is not None and expiry > _utcnow()

    async def extend_subscription(self, user_id: int, days: int) -> datetime:
        if days <= 0:
            raise ValueError("days must be positive")

        now = _utcnow()
        now_iso = now.isoformat()

        await self._ensure_user_exists(user_id)

        current_expiry = await self.get_subscription_expiry(user_id)
        base = current_expiry if current_expiry and current_expiry > now else now
        new_expiry = base + timedelta(days=days)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (user_id, expires_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """,
            (user_id, new_expiry.isoformat(), now_iso),
        )
        await self.conn.commit()
        return new_expiry

    async def revoke_subscription(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def set_proxy_link(self, proxy_link: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES ('proxy_link', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (proxy_link,),
        )
        await self.conn.commit()

    async def get_proxy_link(self) -> str | None:
        cursor = await self.conn.execute(
            "SELECT value FROM settings WHERE key = 'proxy_link'"
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None
        return row["value"]

    async def add_payment(
        self,
        user_id: int,
        amount: int,
        currency: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
    ) -> None:
        now_iso = _utcnow().isoformat()
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at, updated_at)
            VALUES (?, NULL, NULL, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, now_iso, now_iso),
        )

        await self.conn.execute(
            """
            INSERT INTO payments (
                user_id,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                amount,
                currency,
                paid_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                amount,
                currency,
                now_iso,
            ),
        )
        await self.conn.commit()

    async def get_pending_bank_transfer_request(self, user_id: int) -> int | None:
        cursor = await self.conn.execute(
            """
            SELECT id
            FROM bank_transfer_requests
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return int(row["id"])

    async def create_bank_transfer_request(self, user_id: int) -> int:
        await self._ensure_user_exists(user_id)
        now_iso = _utcnow().isoformat()
        cursor = await self.conn.execute(
            """
            INSERT INTO bank_transfer_requests (user_id, status, reviewed_by, created_at, updated_at)
            VALUES (?, 'pending', NULL, ?, ?)
            """,
            (user_id, now_iso, now_iso),
        )
        await self.conn.commit()
        return int(cursor.lastrowid)

    async def approve_bank_transfer_request(self, request_id: int, admin_id: int) -> tuple[int, bool] | None:
        cursor = await self.conn.execute(
            "SELECT user_id, status FROM bank_transfer_requests WHERE id = ?",
            (request_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None

        if row["status"] != "pending":
            return int(row["user_id"]), False

        now_iso = _utcnow().isoformat()
        cursor = await self.conn.execute(
            """
            UPDATE bank_transfer_requests
            SET status = 'approved',
                reviewed_by = ?,
                updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (admin_id, now_iso, request_id),
        )
        updated_rows = cursor.rowcount
        await self.conn.commit()
        return int(row["user_id"]), updated_rows > 0

    async def reject_bank_transfer_request(self, request_id: int, admin_id: int) -> tuple[int, bool] | None:
        cursor = await self.conn.execute(
            "SELECT user_id, status FROM bank_transfer_requests WHERE id = ?",
            (request_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None

        if row["status"] != "pending":
            return int(row["user_id"]), False

        now_iso = _utcnow().isoformat()
        cursor = await self.conn.execute(
            """
            UPDATE bank_transfer_requests
            SET status = 'rejected',
                reviewed_by = ?,
                updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (admin_id, now_iso, request_id),
        )
        updated_rows = cursor.rowcount
        await self.conn.commit()
        return int(row["user_id"]), updated_rows > 0
