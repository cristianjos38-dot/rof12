from dataclasses import dataclass
from decimal import Decimal
from threading import Lock


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    tenant_id: str
    model: str
    tokens: int
    estimated_cost: Decimal


class BudgetGuard:
    def __init__(self, max_tokens_per_tenant=4096, max_cost_per_tenant=Decimal("1.00"), max_retries=2):
        self.max_tokens = max_tokens_per_tenant
        self.max_cost = max_cost_per_tenant
        self.max_retries = max_retries
        self._reserved: dict[str, tuple] = {}
        self._counter = 0
        self._lock = Lock()

    def reserve(self, tenant_id: str, model: str, input_tokens: int, output_tokens: int, estimated_cost: Decimal = Decimal(0)) -> BudgetReservation:
        tokens = int(input_tokens) + int(output_tokens)
        with self._lock:
            used_tokens, used_cost = self._reserved.get(tenant_id, (0, Decimal(0)))
            if used_tokens + tokens > self.max_tokens or used_cost + estimated_cost > self.max_cost:
                raise BudgetExceeded("preventive budget limit exceeded")
            self._counter += 1
            reservation = BudgetReservation(str(self._counter), tenant_id, model, tokens, estimated_cost)
            self._reserved[tenant_id] = (used_tokens + tokens, used_cost + estimated_cost)
            return reservation

    def settle(self, reservation: BudgetReservation, actual_input_tokens: int, actual_output_tokens: int, actual_cost: Decimal = Decimal(0)) -> None:
        with self._lock:
            used_tokens, used_cost = self._reserved.get(reservation.tenant_id, (0, Decimal(0)))
            self._reserved[reservation.tenant_id] = (max(0, used_tokens - reservation.tokens + actual_input_tokens + actual_output_tokens), max(Decimal(0), used_cost - reservation.estimated_cost + actual_cost))
            if self._reserved[reservation.tenant_id][0] > self.max_tokens or self._reserved[reservation.tenant_id][1] > self.max_cost:
                raise BudgetExceeded("actual model usage exceeded budget")

    def cancel(self, reservation: BudgetReservation) -> None:
        with self._lock:
            used_tokens, used_cost = self._reserved.get(reservation.tenant_id, (0, Decimal(0)))
            self._reserved[reservation.tenant_id] = (max(0, used_tokens - reservation.tokens), max(Decimal(0), used_cost - reservation.estimated_cost))

