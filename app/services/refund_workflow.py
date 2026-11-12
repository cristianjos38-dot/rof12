from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from threading import RLock
from uuid import uuid4

from app.domain.contracts import GateResult, ServerContext, ToolRequest
from app.domain.enums import Decision, DenyReason, QuarantineReason, RefundStatus

CAPABILITY_LIMIT = Decimal("200.00")
APPROVAL_THRESHOLD = Decimal("180.00")


@dataclass
class OrderRecord:
    tenant_id: str
    refundable_balance: Decimal
    contaminated: bool = False


@dataclass
class RefundRepository:
    orders: dict[str, OrderRecord] = field(default_factory=dict)
    operation_ids: set[str] = field(default_factory=set)
    lock: RLock = field(default_factory=RLock, repr=False)

    @classmethod
    def fixture(cls) -> RefundRepository:
        return cls(
            orders={
                "order_1042": OrderRecord("tenant_001", Decimal("250.00")),
                "order_9999": OrderRecord("tenant_002", Decimal("250.00")),
                "order_contaminated": OrderRecord("tenant_001", Decimal("250.00"), contaminated=True),
            }
        )


class RefundWorkflow:
    """Authoritative gate and the sole caller of the refund side-effect tool."""

    def __init__(self, repository: RefundRepository | None = None):
        self.repository = repository or RefundRepository.fixture()

    def process(self, context: ServerContext, request: ToolRequest) -> GateResult:
        # Start denied. Every subsequent branch must explicitly establish a safer state.
        self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.DEFAULT_DENY)
        with self.repository.lock:
            order = self.repository.orders.get(request.order_id)
            if order is None or not context.user_id or not context.tenant_id:
                return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.INVALID_CONTEXT)
            if order.contaminated:
                return self._result(request, Decision.QUARANTINE, RefundStatus.QUARANTINED, quarantine_reason=QuarantineReason.CONTAMINATED_DATA)
            if request.operation_id in self.repository.operation_ids:
                return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.DUPLICATE_OPERATION)
            if order.tenant_id != context.tenant_id:
                return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.TENANT_MISMATCH)
            if request.amount > order.refundable_balance:
                return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.AMOUNT_EXCEEDS_BALANCE)
            if request.amount > CAPABILITY_LIMIT:
                return self._result(request, Decision.DENY, RefundStatus.DENIED, deny_reason=DenyReason.AMOUNT_EXCEEDS_CAPABILITY)
            if request.amount > APPROVAL_THRESHOLD:
                self.repository.operation_ids.add(request.operation_id)
                return self._result(request, Decision.REQUIRE_APPROVAL, RefundStatus.HELD_FOR_APPROVAL)
            self.repository.operation_ids.add(request.operation_id)
            order.refundable_balance -= request.amount
            return self._result(request, Decision.ALLOW, RefundStatus.EXECUTED)

    def execute_transaction(self, connection, context, request, capability, provenance, risk_report, now, capability_token):
        """The only production execution sequence; caller supplies an open DB transaction."""
        from sqlalchemy import text

        from app.persistence.audit_logger import AuditLogger
        from app.security.capability_manager import CapabilityManager
        from app.security.capability_manager import validate as validate_capability
        from app.security.kill_switch import KillSwitch
        from app.security.security_gate import SecurityGate
        from app.tools.refund_service import execute_refund_transaction
        from app.verification.verityflow import evaluate

        # 1–4: receive, context, authority and emergency state.
        state = KillSwitch().read(connection)
        capability_validation = validate_capability(capability, request, context, now)
        # 5–6: VerityFlow acquires FOR UPDATE and all policy dimensions revalidate.
        verity = evaluate(connection, request, context, capability, now)
        gate = SecurityGate()
        policy = gate.evaluate(context, request, capability_validation, provenance, risk_report, verity, state)
        connection.execute(text("""
            INSERT INTO rof12.gate_decisions (decision_id, tenant_id, operation_id, decision, reasons)
            VALUES (:id, :tenant_id, :operation_id, :decision, CAST(:reasons AS jsonb))
        """), {"id": f"decision:{request.operation_id}:{uuid4()}", "tenant_id": context.tenant_id, "operation_id": request.operation_id,
               "decision": policy.decision.value, "reasons": __import__("json").dumps(policy.reasons)})
        if policy.decision.value != "ALLOW":
            return policy
        # 7: one-time atomic capability consumption; 8: tool writes in this same transaction.
        permit = gate.mint_if_allowed(policy)
        if not CapabilityManager(connection).consume(capability_token, request, context, now):
            from app.security.policy_engine import GateDecision, PolicyResult

            return PolicyResult(GateDecision.DENY, ("CAPABILITY_NOT_CONSUMABLE",), policy.dimensions)
        execute_refund_transaction(connection, request, context, permit)
        # 9: outbox and audit are part of this transaction; commit belongs to the caller.
        connection.execute(text("""
            INSERT INTO rof12.outbox_events (event_id, tenant_id, event_type, payload)
            VALUES (:id, :tenant_id, 'REFUND_EXECUTED', CAST(:payload AS jsonb))
        """), {"id": permit.permit_id, "tenant_id": context.tenant_id, "payload": __import__("json").dumps({"operation_id": request.operation_id})})
        AuditLogger().append(connection, permit.permit_id, context.tenant_id, "REFUND_EXECUTED", context.user_id, {"operation_id": request.operation_id})
        return permit

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

