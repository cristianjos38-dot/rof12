from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.contracts import ServerContext, ToolRequest


def test_tool_request_rejects_identity_and_extra_fields():
    with pytest.raises(ValidationError):
        ToolRequest(order_id="order_1042", amount=Decimal("10.00"), reason="x", operation_id="op-1", tenant_id="tenant_001")


def test_money_is_decimal_and_positive():
    request = ToolRequest(order_id="order_1042", amount="10.00", reason="x", operation_id="op-1")
    assert request.amount == Decimal("10.00")
    with pytest.raises(ValidationError):
        ToolRequest(order_id="order_1042", amount="0.00", reason="x", operation_id="op-2")


def test_server_context_is_immutable():
    context = ServerContext(user_id="user_001", tenant_id="tenant_001")
    with pytest.raises(ValidationError):
        context.tenant_id = "tenant_002"

