"""Live PostgreSQL RLS checks; skipped unless ROF12_LIVE_DB_URL is provided."""

import os

import pytest
import psycopg


pytestmark = pytest.mark.skipif(
    not os.getenv("ROF12_LIVE_DB_URL"),
    reason="ROF12_LIVE_DB_URL is required for live PostgreSQL RLS verification",
)


def _visible_order_count(connection: psycopg.Connection, tenant_id: str) -> int:
    with connection.transaction():
        connection.execute(
            "SELECT set_config('app.tenant_id', %s, true)", (tenant_id,)
        )
        return int(
            connection.execute(
                "SELECT count(*) FROM rof12.orders WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()[0]
        )


def test_two_real_tenants_are_isolated_by_postgres_rls() -> None:
    url = os.environ["ROF12_LIVE_DB_URL"]
    with psycopg.connect(url) as tenant_a:
        assert _visible_order_count(tenant_a, "tenant_001") == 1
        assert _visible_order_count(tenant_a, "tenant_002") == 0

    with psycopg.connect(url) as tenant_b:
        assert _visible_order_count(tenant_b, "tenant_002") == 1
        assert _visible_order_count(tenant_b, "tenant_001") == 0
