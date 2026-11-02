"""Add users, memberships, and immutable provenance records."""

from alembic import op

revision = "0002_add_core_security_tables"
down_revision = "0001_phase3_persistence_rls"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE TABLE rof12.users (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id),
    CONSTRAINT users_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

CREATE TABLE rof12.memberships (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'REVOKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id, role),
    CONSTRAINT memberships_user_fk FOREIGN KEY (tenant_id, user_id)
        REFERENCES rof12.users (tenant_id, user_id)
);

CREATE TABLE rof12.provenance_records (
    tenant_id TEXT NOT NULL,
    provenance_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    fragment_hash TEXT NOT NULL,
    contamination_status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provenance_id),
    CONSTRAINT provenance_records_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

ALTER TABLE rof12.orders
    ADD CONSTRAINT orders_owner_user_fk FOREIGN KEY (tenant_id, owner_user_id)
    REFERENCES rof12.users (tenant_id, user_id);
ALTER TABLE rof12.audit_events
    ADD CONSTRAINT audit_events_actor_user_fk FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES rof12.users (tenant_id, user_id);

ALTER TABLE rof12.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.provenance_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_tenant_isolation ON rof12.users
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY memberships_tenant_isolation ON rof12.memberships
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY provenance_records_tenant_isolation ON rof12.provenance_records
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

REVOKE ALL ON rof12.users, rof12.memberships, rof12.provenance_records FROM PUBLIC;
GRANT SELECT ON rof12.users, rof12.memberships TO rof12_app;
GRANT SELECT, INSERT ON rof12.provenance_records TO rof12_app;
GRANT SELECT ON rof12.users, rof12.memberships, rof12.provenance_records TO rof12_executor;
GRANT SELECT ON rof12.users, rof12.memberships TO rof12_audit;
GRANT SELECT ON rof12.provenance_records TO rof12_audit;
REVOKE UPDATE, DELETE ON rof12.provenance_records FROM rof12_app, rof12_executor, rof12_audit
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS rof12.provenance_records;
DROP TABLE IF EXISTS rof12.memberships;
ALTER TABLE rof12.orders DROP CONSTRAINT IF EXISTS orders_owner_user_fk;
ALTER TABLE rof12.audit_events DROP CONSTRAINT IF EXISTS audit_events_actor_user_fk;
DROP TABLE IF EXISTS rof12.users
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

