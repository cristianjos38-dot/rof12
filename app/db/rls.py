from sqlalchemy import text


def set_tenant(connection, tenant_id: str) -> None:
    """Set tenant context transaction-locally; callers must invoke inside a transaction."""
    if not tenant_id or "'" in tenant_id or "\\" in tenant_id:
        raise ValueError("invalid tenant_id")
    connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})

