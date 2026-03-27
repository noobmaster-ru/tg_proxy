"""add subscription notifications table

Revision ID: 202603270002
Revises: 202603080001
Create Date: 2026-03-27 12:00:00
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202603270002"
down_revision = "202603080001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at
        ON subscriptions (expires_at);

        CREATE TABLE IF NOT EXISTS subscription_notifications (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            notification_type TEXT NOT NULL CHECK (notification_type IN ('expiring_24h', 'expired')),
            expires_at TIMESTAMPTZ NOT NULL,
            sent_at TIMESTAMPTZ NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_notifications_unique
        ON subscription_notifications (user_id, notification_type, expires_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_subscription_notifications_unique;
        DROP TABLE IF EXISTS subscription_notifications;
        DROP INDEX IF EXISTS idx_subscriptions_expires_at;
        """
    )
