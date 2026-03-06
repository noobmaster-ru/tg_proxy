from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class SubscriptionState:
    is_free: bool
    expires_at: datetime | None

    def is_active(self) -> bool:
        if self.is_free:
            return True
        return self.expires_at is not None and self.expires_at > datetime.now(UTC)


@dataclass(frozen=True)
class BankTransferDecision:
    user_id: int
    applied_now: bool


@dataclass(frozen=True)
class ApprovedBankTransfer:
    user_id: int
    applied_now: bool
    new_expiry: datetime | None
