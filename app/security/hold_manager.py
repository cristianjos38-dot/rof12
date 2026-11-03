from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HoldStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class HoldError(ValueError):
    pass


@dataclass
class Hold:
    hold_id: str
    tenant_id: str
    created_by: str
    expires_at: datetime
    status: HoldStatus = HoldStatus.OPEN
    approver_id: str | None = None
    justification: str = ""


class HoldManager:
    AUTHORIZED_ROLES = frozenset({"approver", "admin", "security_admin"})

    def __init__(self):
        self.holds: dict[str, Hold] = {}

    def open(self, hold: Hold) -> Hold:
        self.holds[hold.hold_id] = hold
        return hold

    def resolve(self, hold_id: str, ctx, now: datetime, approve: bool, revalidate: Callable[[], Any], justification: str = "") -> Hold:
        hold = self.holds.get(hold_id)
        if hold is None:
            raise HoldError("hold not found")
        if getattr(ctx, "role", None) not in self.AUTHORIZED_ROLES:
            raise HoldError("role cannot resolve hold")
        if hold.status is not HoldStatus.OPEN:
            raise HoldError("hold is not open")
        if now >= hold.expires_at:
            hold.status = HoldStatus.EXPIRED
            raise HoldError("hold expired")
        if not approve:
            hold.status = HoldStatus.REJECTED
            hold.approver_id = getattr(ctx, "user_id", None)
            hold.justification = justification
            return hold
        result = revalidate()
        if getattr(result, "decision", None) is not None and str(getattr(result.decision, "value", result.decision)) != "ALLOW":
            raise HoldError("revalidation did not allow execution")
        hold.status = HoldStatus.APPROVED
        hold.approver_id = getattr(ctx, "user_id", None)
        hold.justification = justification
        return hold

