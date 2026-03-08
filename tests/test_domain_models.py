from __future__ import annotations

from datetime import UTC, datetime, timedelta

from axiomai_proxy.domain.models import SubscriptionState


def test_subscription_state_is_active_for_free_user() -> None:
    state = SubscriptionState(is_free=True, expires_at=None)
    assert state.is_active() is True


def test_subscription_state_is_active_when_expiry_in_future() -> None:
    state = SubscriptionState(
        is_free=False,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    assert state.is_active() is True


def test_subscription_state_is_not_active_when_expiry_missing() -> None:
    state = SubscriptionState(is_free=False, expires_at=None)
    assert state.is_active() is False


def test_subscription_state_is_not_active_when_expiry_in_past() -> None:
    state = SubscriptionState(
        is_free=False,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    assert state.is_active() is False
