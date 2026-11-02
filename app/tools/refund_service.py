from decimal import Decimal


def execute_refund(order_id: str, amount: Decimal, operation_id: str) -> dict:
    """Legacy adapter intentionally cannot execute without a Gate permit."""
    raise PermissionError("refund execution requires a SecurityGate permit")


def execute_refund_transaction(connection, request, context, permit) -> dict:
    """Execute only after the workflow has minted an internal permit."""
    permit._assert_internal()
    connection.execute(__import__("sqlalchemy").text("""
        INSERT INTO rof12.refunds (refund_id, tenant_id, order_id, operation_id, amount, status)
        VALUES (:refund_id, :tenant_id, :order_id, :operation_id, :amount, 'EXECUTED')
    """), {"refund_id": permit.permit_id, "tenant_id": context.tenant_id, "order_id": request.order_id,
           "operation_id": request.operation_id, "amount": request.amount})
    connection.execute(__import__("sqlalchemy").text("""
        UPDATE rof12.orders
           SET refundable_balance = refundable_balance - :amount
         WHERE tenant_id = :tenant_id AND order_id = :order_id
    """), {"tenant_id": context.tenant_id, "order_id": request.order_id, "amount": request.amount})
    return {"order_id": request.order_id, "amount": request.amount, "operation_id": request.operation_id, "executed": True}

