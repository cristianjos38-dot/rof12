from datetime import UTC, datetime
from decimal import Decimal

from app.security.capability_manager import CapabilityManager


class Result:
    def __init__(self, value): self.value = value
    def first(self): return self.value


class FakeConnection:
    def __init__(self): self.statements = []
    def execute(self, statement, params):
        self.statements.append((str(statement), params))
        return Result(("cap-1",))


def test_consume_uses_atomic_active_expiry_update():
    connection = FakeConnection()
    manager = CapabilityManager(connection)
    class Request: amount = Decimal("10.00")
    class Context: tenant_id = "tenant_001"; user_id = "user_001"
    assert manager.consume("secret", Request(), Context(), datetime.now(UTC)) == "cap-1"
    sql, params = connection.statements[0]
    assert "UPDATE rof12.capabilities" in sql
    assert "status = 'ACTIVE'" in sql
    assert "expires_at > :now" in sql
    assert "RETURNING capability_id" in sql
    assert params["amount"] == Decimal("10.00")

