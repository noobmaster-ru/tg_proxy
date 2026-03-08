from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from axiomai_proxy.application.dto import StarsPaymentDTO, UserDTO
from axiomai_proxy.application.exceptions import InvalidPaymentError, InvalidSubscriptionPeriodError
from axiomai_proxy.application.interactors.approve_bank_transfer import ApproveBankTransfer
from axiomai_proxy.application.interactors.create_bank_transfer_request import CreateBankTransferRequest
from axiomai_proxy.application.interactors.get_subscription_state import GetSubscriptionState
from axiomai_proxy.application.interactors.grant_subscription import GrantSubscription
from axiomai_proxy.application.interactors.has_proxy_access import HasProxyAccess
from axiomai_proxy.application.interactors.process_stars_payment import ProcessStarsPayment
from axiomai_proxy.domain.models import BankTransferDecision


def _run(coro):
    return asyncio.run(coro)


def test_get_subscription_state_free_user_does_not_call_gateway() -> None:
    gateway = SimpleNamespace(get_subscription_expiry=AsyncMock())
    interactor = GetSubscriptionState(gateway=gateway, free_user_ids={1, 2})

    state = _run(interactor.execute(1))

    assert state.is_free is True
    assert state.expires_at is None
    gateway.get_subscription_expiry.assert_not_awaited()


def test_get_subscription_state_paid_user_reads_expiry() -> None:
    expiry = datetime.now(UTC) + timedelta(days=10)
    gateway = SimpleNamespace(get_subscription_expiry=AsyncMock(return_value=expiry))
    interactor = GetSubscriptionState(gateway=gateway, free_user_ids=set())

    state = _run(interactor.execute(77))

    assert state.is_free is False
    assert state.expires_at == expiry
    gateway.get_subscription_expiry.assert_awaited_once_with(77)


def test_has_proxy_access_reflects_subscription_state() -> None:
    expiry = datetime.now(UTC) + timedelta(days=2)
    gateway = SimpleNamespace(get_subscription_expiry=AsyncMock(return_value=expiry))
    get_state = GetSubscriptionState(gateway=gateway, free_user_ids=set())
    has_access = HasProxyAccess(get_subscription_state=get_state)

    result = _run(has_access.execute(42))

    assert result is True


def test_process_stars_payment_updates_user_subscription_and_payment() -> None:
    expiry = datetime.now(UTC) + timedelta(days=30)
    gateway = SimpleNamespace(
        upsert_user=AsyncMock(),
        extend_subscription=AsyncMock(return_value=expiry),
        add_payment=AsyncMock(),
    )
    interactor = ProcessStarsPayment(gateway=gateway, subscription_days=30)
    payment = StarsPaymentDTO(
        user=UserDTO(user_id=10, username="test", first_name="Kirill"),
        amount=200,
        currency="XTR",
        telegram_payment_charge_id="tg_123",
        provider_payment_charge_id="pr_456",
    )

    result = _run(interactor.execute(payment))

    assert result == expiry
    gateway.upsert_user.assert_awaited_once_with(user_id=10, username="test", first_name="Kirill")
    gateway.extend_subscription.assert_awaited_once_with(10, 30)
    gateway.add_payment.assert_awaited_once_with(
        user_id=10,
        amount=200,
        currency="XTR",
        telegram_payment_charge_id="tg_123",
        provider_payment_charge_id="pr_456",
    )


def test_process_stars_payment_rejects_non_positive_amount() -> None:
    gateway = SimpleNamespace(
        upsert_user=AsyncMock(),
        extend_subscription=AsyncMock(),
        add_payment=AsyncMock(),
    )
    interactor = ProcessStarsPayment(gateway=gateway, subscription_days=30)
    payment = StarsPaymentDTO(
        user=UserDTO(user_id=10, username=None, first_name=None),
        amount=0,
        currency="XTR",
        telegram_payment_charge_id=None,
        provider_payment_charge_id=None,
    )

    with pytest.raises(InvalidPaymentError):
        _run(interactor.execute(payment))

    gateway.upsert_user.assert_not_awaited()
    gateway.extend_subscription.assert_not_awaited()
    gateway.add_payment.assert_not_awaited()


def test_grant_subscription_rejects_non_positive_days() -> None:
    gateway = SimpleNamespace(extend_subscription=AsyncMock())
    interactor = GrantSubscription(gateway=gateway)

    with pytest.raises(InvalidSubscriptionPeriodError):
        _run(interactor.execute(user_id=5, days=0))

    gateway.extend_subscription.assert_not_awaited()


def test_grant_subscription_calls_gateway_for_valid_days() -> None:
    expiry = datetime.now(UTC) + timedelta(days=5)
    gateway = SimpleNamespace(extend_subscription=AsyncMock(return_value=expiry))
    interactor = GrantSubscription(gateway=gateway)

    result = _run(interactor.execute(user_id=5, days=5))

    assert result == expiry
    gateway.extend_subscription.assert_awaited_once_with(user_id=5, days=5)


def test_approve_bank_transfer_returns_none_when_missing_request() -> None:
    gateway = SimpleNamespace(
        approve_bank_transfer_request=AsyncMock(return_value=None),
        extend_subscription=AsyncMock(),
    )
    interactor = ApproveBankTransfer(gateway=gateway, subscription_days=30)

    result = _run(interactor.execute(request_id=1, admin_id=99))

    assert result is None
    gateway.extend_subscription.assert_not_awaited()


def test_approve_bank_transfer_does_not_extend_when_already_processed() -> None:
    gateway = SimpleNamespace(
        approve_bank_transfer_request=AsyncMock(return_value=BankTransferDecision(user_id=55, applied_now=False)),
        extend_subscription=AsyncMock(),
    )
    interactor = ApproveBankTransfer(gateway=gateway, subscription_days=30)

    result = _run(interactor.execute(request_id=1, admin_id=99))

    assert result is not None
    assert result.user_id == 55
    assert result.applied_now is False
    assert result.new_expiry is None
    gateway.extend_subscription.assert_not_awaited()


def test_approve_bank_transfer_extends_subscription_when_pending_request() -> None:
    expiry = datetime.now(UTC) + timedelta(days=30)
    gateway = SimpleNamespace(
        approve_bank_transfer_request=AsyncMock(return_value=BankTransferDecision(user_id=55, applied_now=True)),
        extend_subscription=AsyncMock(return_value=expiry),
    )
    interactor = ApproveBankTransfer(gateway=gateway, subscription_days=30)

    result = _run(interactor.execute(request_id=1, admin_id=99))

    assert result is not None
    assert result.user_id == 55
    assert result.applied_now is True
    assert result.new_expiry == expiry
    gateway.extend_subscription.assert_awaited_once_with(55, 30)


def test_create_bank_transfer_request_returns_none_when_pending_exists() -> None:
    gateway = SimpleNamespace(
        upsert_user=AsyncMock(),
        get_pending_bank_transfer_request=AsyncMock(return_value=123),
        create_bank_transfer_request=AsyncMock(),
    )
    interactor = CreateBankTransferRequest(gateway=gateway)

    result = _run(interactor.execute(UserDTO(user_id=50, username="x", first_name="y")))

    assert result is None
    gateway.create_bank_transfer_request.assert_not_awaited()


def test_create_bank_transfer_request_creates_new_request() -> None:
    gateway = SimpleNamespace(
        upsert_user=AsyncMock(),
        get_pending_bank_transfer_request=AsyncMock(return_value=None),
        create_bank_transfer_request=AsyncMock(return_value=777),
    )
    interactor = CreateBankTransferRequest(gateway=gateway)

    result = _run(interactor.execute(UserDTO(user_id=50, username="x", first_name="y")))

    assert result == 777
    gateway.create_bank_transfer_request.assert_awaited_once_with(50)
