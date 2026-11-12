"""Permit role-scoped access to the global kill-switch state."""

from alembic import op

revision = "0010_system_state_rls_policies"
down_revision = "0009_grant_sequence_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE POLICY system_state_app_read ON rof12.system_state
            FOR SELECT TO rof12_app, rof12_audit USING (true);
        CREATE POLICY system_state_executor_read ON rof12.system_state
            FOR SELECT TO rof12_executor USING (true);
        CREATE POLICY system_state_executor_update ON rof12.system_state
            FOR UPDATE TO rof12_executor USING (true) WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS system_state_executor_update ON rof12.system_state;
        DROP POLICY IF EXISTS system_state_executor_read ON rof12.system_state;
        DROP POLICY IF EXISTS system_state_app_read ON rof12.system_state;
    """)
