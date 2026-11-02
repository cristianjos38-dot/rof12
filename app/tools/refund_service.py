from decimal import Decimal


def execute_refund(order_id: str, amount: Decimal, operation_id: str) -> dict:
    """The only side-effect adapter; production persistence is intentionally deferred."""
    return {"order_id": order_id, "amount": amount, "operation_id": operation_id, "executed": True}

