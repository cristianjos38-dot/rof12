"""Add model consumption telemetry."""

from alembic import op

revision = "0007_add_model_usage"
down_revision = "0006_add_holds_killswitch_audit_gate"
branch_labels = None
depends_on = None

UPGRADE_SQL = """
CREATE TABLE rof12.model_usage (
    usage_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    estimated_cost NUMERIC(12, 6) NOT NULL CHECK (estimated_cost >= 0),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT model_usage_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);
ALTER TABLE rof12.model_usage ENABLE ROW LEVEL SECURITY;
CREATE POLICY model_usage_tenant_isolation ON rof12.model_usage
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON rof12.model_usage FROM PUBLIC;
GRANT SELECT, INSERT ON rof12.model_usage TO rof12_app, rof12_executor, rof12_audit
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS rof12.model_usage"


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

