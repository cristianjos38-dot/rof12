"""Add hashed, expiring and consumable capabilities."""

from alembic import op

revision = "0004_add_capabilities"
down_revision = "0003_add_isolated_documents"
branch_labels = None
depends_on = None

UPGRADE_SQL = """
CREATE TABLE rof12.capabilities (
    capability_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL,
    max_amount NUMERIC(12, 2) NOT NULL CHECK (max_amount > 0),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CONSUMED', 'REVOKED')),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT capabilities_user_fk FOREIGN KEY (tenant_id, subject_user_id)
        REFERENCES rof12.users (tenant_id, user_id)
);
ALTER TABLE rof12.capabilities ENABLE ROW LEVEL SECURITY;
CREATE POLICY capabilities_tenant_isolation ON rof12.capabilities
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON rof12.capabilities FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON rof12.capabilities TO rof12_executor;
GRANT SELECT ON rof12.capabilities TO rof12_app, rof12_audit;
REVOKE DELETE ON rof12.capabilities FROM rof12_app, rof12_executor, rof12_audit
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS rof12.capabilities"


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

