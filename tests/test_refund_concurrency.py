from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from app.domain.contracts import ServerContext, ToolRequest
from app.services.refund_workflow import RefundRepository, RefundWorkflow


def test_same_operation_id_allows_exactly_one_concurrent_execution():
    workflow = RefundWorkflow(RefundRepository.fixture())
    context = ServerContext(user_id="user_001", tenant_id="tenant_001")
    request = ToolRequest(order_id="order_1042", amount=Decimal("10.00"), reason="test", operation_id="race-1")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: workflow.process(context, request), range(2)))
    assert sum(result.status.value == "EXECUTED" for result in results) == 1
    assert sum(result.deny_reason.value == "DUPLICATE_OPERATION" for result in results if result.deny_reason) == 1
