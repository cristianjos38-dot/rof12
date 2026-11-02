from decimal import Decimal
from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field, condecimal

from app.domain.enums import Decision, DenyReason, QuarantineReason, RefundStatus

Money = condecimal(max_digits=12, decimal_places=2, gt=0)


class ServerContext(BaseModel):
    """Trusted authentication output; never populated from agent input."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    user_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    roles: FrozenSet[str] = frozenset()


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str = Field(min_length=1)
    amount: Money
    reason: str = Field(min_length=1, max_length=500)
    operation_id: str = Field(min_length=1, max_length=128)


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: str = Field(min_length=1)
    payload: dict


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Decision = Decision.DENY
    status: RefundStatus = RefundStatus.DENIED
    reason: Optional[str] = None
    deny_reason: Optional[DenyReason] = None
    quarantine_reason: Optional[QuarantineReason] = None
    operation_id: str
    amount: Money

