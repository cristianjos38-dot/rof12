from decimal import Decimal

import pytest

from app.agents.budget_guard import BudgetExceeded, BudgetGuard


def test_preventive_reservation_and_cancel():
    guard = BudgetGuard(max_tokens_per_tenant=100, max_cost_per_tenant=Decimal("1.00"))
    reservation = guard.reserve("tenant_001", "muse-spark-1.3", 40, 20, Decimal("0.20"))
    with pytest.raises(BudgetExceeded):
        guard.reserve("tenant_001", "muse-spark-1.3", 50, 20, Decimal("0.20"))
    guard.cancel(reservation)
    assert guard.reserve("tenant_001", "muse-spark-1.3", 50, 20, Decimal("0.20"))


def test_settle_cuts_off_actual_overrun():
    guard = BudgetGuard(max_tokens_per_tenant=100, max_cost_per_tenant=Decimal("1.00"))
    reservation = guard.reserve("tenant_001", "muse-wonder-1.0", 10, 10, Decimal("0.10"))
    with pytest.raises(BudgetExceeded):
        guard.settle(reservation, 80, 40, Decimal("0.10"))

