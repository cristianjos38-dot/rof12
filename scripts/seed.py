"""Idempotent local-only fixture seed for the ROF12 demonstration database."""
import os

from sqlalchemy import create_engine, text


DATABASE_OWNER_URL = os.getenv(
    "DATABASE_OWNER_URL",
    "postgresql+psycopg://rof12_owner:rof12_owner_dev_only@localhost:5432/rof12",
)


def seed() -> None:
    engine = create_engine(DATABASE_OWNER_URL, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO rof12.tenants (tenant_id) VALUES ('tenant_001'), ('tenant_002') ON CONFLICT DO NOTHING"))
        connection.execute(text("""
            INSERT INTO rof12.users (tenant_id, user_id, status)
            VALUES ('tenant_001', 'user_001', 'ACTIVE'), ('tenant_002', 'user_002', 'ACTIVE')
            ON CONFLICT DO NOTHING
        """))
        connection.execute(text("""
            INSERT INTO rof12.memberships (tenant_id, user_id, role, status)
            VALUES ('tenant_001', 'user_001', 'operator', 'ACTIVE'), ('tenant_002', 'user_002', 'operator', 'ACTIVE')
            ON CONFLICT DO NOTHING
        """))
        connection.execute(text("""
            INSERT INTO rof12.orders (tenant_id, order_id, owner_user_id, refundable_balance)
            VALUES ('tenant_001', 'order_1042', 'user_001', 250.00), ('tenant_002', 'order_9999', 'user_002', 250.00)
            ON CONFLICT DO NOTHING
        """))
        connection.execute(text("""
            INSERT INTO rof12.order_balances (tenant_id, order_id, available_amount)
            VALUES ('tenant_001', 'order_1042', 250.00), ('tenant_002', 'order_9999', 250.00)
            ON CONFLICT DO NOTHING
        """))
        connection.execute(text("""
            INSERT INTO rof12.provenance_records
                (tenant_id, provenance_id, source_type, source_uri, fragment_hash, contamination_status)
            VALUES ('tenant_001', 'prov_seed_1042', 'internal_fixture', 'seed://order_1042', 'seed', 'RECONCILED')
            ON CONFLICT DO NOTHING
        """))
    print("ROF12 local fixtures seeded")


if __name__ == "__main__":
    seed()

