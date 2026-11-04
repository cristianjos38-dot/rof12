"""Herramientas simuladas + runtime que SOLO ejecuta con un permit firmado valido."""
from __future__ import annotations

import datetime as dt
import secrets


class PermitError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


class Store:
    """Base de datos en memoria (stand-in de Postgres/Supabase)."""

    def __init__(self):
        today = dt.date.today()
        d = lambda n: (today - dt.timedelta(days=n)).isoformat()
        self.orders = {
            "ORD-7731": {"customer_id": "C-204", "total": 45.00, "refunded": 0.0, "currency": "USD", "date": d(6)},
            "ORD-7788": {"customer_id": "C-204", "total": 340.00, "refunded": 0.0, "currency": "USD", "date": d(9)},
            "ORD-9001": {"customer_id": "C-204", "total": 1850.00, "refunded": 0.0, "currency": "USD", "date": d(4)},
            "ORD-5555": {"customer_id": "C-377", "total": 80.00, "refunded": 0.0, "currency": "USD", "date": d(3)},
        }
        self.refunds = []


class ToolRuntime:
    """Unica via de ejecucion. Sin permit valido, ninguna herramienta con efectos corre."""

    def __init__(self, store: Store, verify_permit):
        self.store = store
        self._verify = verify_permit
        self._used = set()

    def call(self, tool: str, args: dict, permit: dict | None, **binding):
        if not permit:
            raise PermitError("NO_PERMIT", "la ejecucion requiere un permit firmado por el gate")
        self._verify(permit, tool, args, **binding)  # firma, expiracion, identity, args_hash
        if permit["permit_id"] in self._used:
            raise PermitError("PERMIT_ALREADY_USED", f"{permit['permit_id']} es de un solo uso")
        self._used.add(permit["permit_id"])
        fn = {"orders.read": self._orders_read, "refunds.create": self._refunds_create}.get(tool)
        if not fn:
            raise PermitError("TOOL_NOT_IMPLEMENTED", tool)
        return fn(**args)

    def _orders_read(self, order_id):
        return dict(self.store.orders[order_id], order_id=order_id)

    def _refunds_create(self, order_id, amount, reason="", **_):
        o = self.store.orders[order_id]
        o["refunded"] = round(o["refunded"] + float(amount), 2)
        rec = {"refund_id": "RF-" + secrets.token_hex(3).upper(), "order_id": order_id,
               "amount": float(amount), "currency": o["currency"], "reason": reason}
        self.store.refunds.append(rec)
        return rec
