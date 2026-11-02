"""Phase 3: tenant-isolated PostgreSQL persistence and least-privilege grants."""

from alembic import op

revision = "0001_phase3_persistence_rls"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE SCHEMA IF NOT EXISTS rof12 AUTHORIZATION rof12_owner;
REVOKE ALL ON SCHEMA rof12 FROM PUBLIC;
GRANT USAGE ON SCHEMA rof12 TO rof12_app, rof12_executor, rof12_audit;

CREATE TABLE rof12.tenants (
    tenant_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rof12.orders (
    tenant_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    refundable_balance NUMERIC(12, 2) NOT NULL CHECK (refundable_balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, order_id),
    CONSTRAINT orders_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

CREATE TABLE rof12.order_balances (
    tenant_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    available_amount NUMERIC(12, 2) NOT NULL CHECK (available_amount >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, order_id),
    CONSTRAINT order_balances_order_fk FOREIGN KEY (tenant_id, order_id)
        REFERENCES rof12.orders (tenant_id, order_id)
);

CREATE TABLE rof12.refunds (
    refund_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL CHECK (status IN ('EXECUTED', 'HELD_FOR_APPROVAL')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT refunds_operation_uq UNIQUE (tenant_id, operation_id),
    CONSTRAINT refunds_order_fk FOREIGN KEY (tenant_id, order_id)
        REFERENCES rof12.orders (tenant_id, order_id)
);

CREATE TABLE rof12.audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT audit_events_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

ALTER TABLE rof12.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.order_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.audit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenants_tenant_isolation ON rof12.tenants
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY orders_tenant_isolation ON rof12.orders
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY order_balances_tenant_isolation ON rof12.order_balances
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY refunds_tenant_isolation ON rof12.refunds
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY audit_events_tenant_isolation ON rof12.audit_events
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

REVOKE ALL ON ALL TABLES IN SCHEMA rof12 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON rof12.tenants, rof12.orders, rof12.audit_events TO rof12_app;
GRANT SELECT ON rof12.order_balances, rof12.refunds TO rof12_app;
REVOKE INSERT, UPDATE, DELETE ON rof12.refunds, rof12.order_balances FROM rof12_app;

GRANT SELECT ON rof12.tenants, rof12.orders, rof12.order_balances TO rof12_executor;
GRANT INSERT ON rof12.refunds TO rof12_executor;
GRANT UPDATE (refundable_balance) ON rof12.orders TO rof12_executor;
REVOKE UPDATE, DELETE ON rof12.refunds FROM rof12_executor;
REVOKE INSERT, UPDATE, DELETE ON rof12.order_balances FROM rof12_executor;

GRANT SELECT, INSERT ON rof12.audit_events TO rof12_audit;
REVOKE UPDATE, DELETE ON rof12.audit_events FROM rof12_audit;
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS rof12.audit_events;
DROP TABLE IF EXISTS rof12.refunds;
DROP TABLE IF EXISTS rof12.order_balances;
DROP TABLE IF EXISTS rof12.orders;
DROP TABLE IF EXISTS rof12.tenants;
DROP SCHEMA IF EXISTS rof12;
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

