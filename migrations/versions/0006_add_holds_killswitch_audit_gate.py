"""Add holds, kill switch state, gate decisions, outbox and audit chain fields."""

from alembic import op

revision = "0006_add_holds_killswitch_audit_gate"
down_revision = "0005_add_order_status"
branch_labels = None
depends_on = None

UPGRADE_SQL = """
ALTER TABLE rof12.audit_events ADD COLUMN chain_sequence BIGSERIAL;
ALTER TABLE rof12.audit_events ADD COLUMN prev_hash TEXT NOT NULL DEFAULT 'GENESIS';
ALTER TABLE rof12.audit_events ADD COLUMN event_hash TEXT NOT NULL DEFAULT '';

CREATE TABLE rof12.system_state (
    state_id BOOLEAN PRIMARY KEY DEFAULT true CHECK (state_id = true),
    kill_switch_active BOOLEAN NOT NULL DEFAULT false,
    reason TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO rof12.system_state (state_id) VALUES (true) ON CONFLICT DO NOTHING;

CREATE TABLE rof12.holds (
    hold_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'APPROVED', 'REJECTED', 'EXPIRED')),
    expires_at TIMESTAMPTZ NOT NULL,
    resolved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT holds_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

CREATE TABLE rof12.gate_decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'QUARANTINE', 'REQUIRE_APPROVAL')),
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    permit_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT gate_decisions_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

CREATE TABLE rof12.outbox_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT outbox_events_tenant_fk FOREIGN KEY (tenant_id) REFERENCES rof12.tenants (tenant_id)
);

ALTER TABLE rof12.system_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.holds ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.gate_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.outbox_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY holds_tenant_isolation ON rof12.holds USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY gate_decisions_tenant_isolation ON rof12.gate_decisions USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY outbox_events_tenant_isolation ON rof12.outbox_events USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON rof12.system_state, rof12.holds, rof12.gate_decisions, rof12.outbox_events FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON rof12.holds, rof12.gate_decisions, rof12.outbox_events TO rof12_executor;
GRANT SELECT ON rof12.system_state, rof12.holds, rof12.gate_decisions, rof12.outbox_events TO rof12_app, rof12_audit;
GRANT UPDATE ON rof12.system_state TO rof12_executor;
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS rof12.outbox_events;
DROP TABLE IF EXISTS rof12.gate_decisions;
DROP TABLE IF EXISTS rof12.holds;
DROP TABLE IF EXISTS rof12.system_state;
ALTER TABLE rof12.audit_events DROP COLUMN IF EXISTS chain_sequence;
ALTER TABLE rof12.audit_events DROP COLUMN IF EXISTS prev_hash;
ALTER TABLE rof12.audit_events DROP COLUMN IF EXISTS event_hash
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

