from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Set

from app.domain.contracts import GateResult, ServerContext, ToolRequest
from app.domain.enums import Decision, DenyReason, QuarantineReason, RefundStatus
from app.tools.refund_service import execute_refund


CAPABILITY_LIMIT = Decimal("200.00")
APPROVAL_THRESHOLD = Decimal("180.00")


@dataclass
class OrderRecord:
    tenant_id: str
    refundable_balance: Decimal
    contaminated: bool = False


@dataclass
class RefundRepository:
    orders: Dict[str, OrderRecord] = field(default_factory=dict)
    operation_ids: Set[str] = field(default_factory=set)

    @classmethod
    def fixture(cls) -> "RefundRepository":
        return cls(
            orders={
                "order_1042": OrderRecord("tenant_001", Decimal("250.00")),
                "order_9999": OrderRecord("tenant_002", Decimal("250.00")),
                "order_contaminated": OrderRecord("tenant_001", Decimal("250.00"), contaminated=True),
            }
        )


class RefundWorkflow:
    """Authoritative gate and the sole caller of the refund side-effect tool."""

    def __init__(self, repository: RefundRepository = None):
        self.repository = repository or RefundRepository.fixture()

    def process(self, context: ServerContext, request: ToolRequest) -> GateResult:
        # Start denied. Every subsequent branch must explicitly establish a safer state.
        denied = self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.DEFAULT_DENY)
        order = self.repository.orders.get(request.order_id)
        if order is None or not context.user_id or not context.tenant_id:
            return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.INVALID_CONTEXT)
        if order.contaminated:
            return self._result(request, Decision.QUARANTINE, RefundStatus.QUARANTINED, quarantine_reason=QuarantineReason.CONTAMINATED_DATA)
        if request.operation_id in self.repository.operation_ids:
            return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.DUPLICATE_OPERATION)
        if order.tenant_id != context.tenant_id:
            return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.TENANT_MISMATCH)
        # Balance precedes capability so an amount beyond both limits reports balance exhaustion.
        if request.amount > order.refundable_balance:
            return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.AMOUNT_EXCEEDS_BALANCE)
        if request.amount > CAPABILITY_LIMIT:
            return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.AMOUNT_EXCEEDS_CAPABILITY)
        if request.amount > APPROVAL_THRESHOLD:
            self.repository.operation_ids.add(request.operation_id)
            return self._result(request, Decision.REQUIRE_APPROVAL, RefundStatus.HELD_FOR_APPROVAL)

        self.repository.operation_ids.add(request.operation_id)
        execute_refund(request.order_id, request.amount, request.operation_id)
        order.refundable_balance -= request.amount
        return self._result(request, Decision.ALLOW, RefundStatus.EXECUTED)

    @staticmethod
    def _result(request, decision, status, deny_reason=None, quarantine_reason=None):
        return GateResult(
            decision=decision,
            status=status,
            deny_reason=deny_reason,
            quarantine_reason=quarantine_reason,
            operation_id=request.operation_id,
            amount=request.amount,
        )

