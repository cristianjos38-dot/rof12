from decimal import Decimal

from app.domain.contracts import ServerContext, ToolRequest
from app.domain.enums import Decision, DenyReason, QuarantineReason
from app.services.refund_workflow import RefundRepository, RefundWorkflow


def ctx(tenant="tenant_001", user="user_001"):
    return ServerContext(tenant_id=tenant, user_id=user)


def req(amount, order="order_1042", operation="op"):
    return ToolRequest(order_id=order, amount=Decimal(amount), reason="customer request", operation_id=operation)


def test_gate_boundaries_and_approval():
    assert RefundWorkflow().process(ctx(), req("180.00", operation="a")).decision is Decision.ALLOW
    assert RefundWorkflow().process(ctx(), req("180.01", operation="b")).decision is Decision.REQUIRE_APPROVAL
    assert RefundWorkflow().process(ctx(), req("200.00", operation="c")).decision is Decision.REQUIRE_APPROVAL
    result = RefundWorkflow().process(ctx(), req("200.01", operation="d"))
    assert result.deny_reason is DenyReason.AMOUNT_EXCEEDS_CAPABILITY


def test_balance_tenant_duplicate_and_quarantine():
    workflow = RefundWorkflow()
    assert workflow.process(ctx(), req("250.01", operation="a")).deny_reason is DenyReason.AMOUNT_EXCEEDS_BALANCE
    assert workflow.process(ctx("tenant_002", "user_002"), req("10.00", operation="b")).deny_reason is DenyReason.TENANT_MISMATCH
    assert workflow.process(ctx(), req("10.00", operation="c")).decision is Decision.ALLOW
    assert workflow.process(ctx(), req("10.00", operation="c")).deny_reason is DenyReason.DUPLICATE_OPERATION
    contaminated = workflow.process(ctx(), req("10.00", order="order_contaminated", operation="e"))
    assert contaminated.quarantine_reason is QuarantineReason.CONTAMINATED_DATA

