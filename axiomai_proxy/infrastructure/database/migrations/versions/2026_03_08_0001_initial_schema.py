"""initial schema

Revision ID: 202603080001
Revises:
Create Date: 2026-03-08 00:01:00
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202603080001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            telegram_payment_charge_id TEXT,
            provider_payment_charge_id TEXT,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL,
            paid_at TIMESTAMPTZ NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bank_transfer_requests (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
            reviewed_by BIGINT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_bank_transfer_requests_user_status
        ON bank_transfer_requests (user_id, status);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS bank_transfer_requests;
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS settings;
        DROP TABLE IF EXISTS subscriptions;
        DROP TABLE IF EXISTS users;
        """
    )
