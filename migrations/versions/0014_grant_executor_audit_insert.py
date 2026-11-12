"""Allow the executor transaction to append its own atomic audit event."""

from alembic import op

revision = "0014_grant_executor_audit_insert"
down_revision = "0013_hold_resolution_justification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        GRANT SELECT ON rof12.system_state TO rof12_app, rof12_audit, rof12_executor;
        GRANT SELECT ON rof12.refunds TO rof12_executor;
        GRANT UPDATE ON rof12.system_state TO rof12_executor;
        GRANT INSERT ON rof12.audit_events TO rof12_executor;
    """)


def downgrade() -> None:
    op.execute("""
        REVOKE INSERT ON rof12.audit_events FROM rof12_executor;
        REVOKE UPDATE ON rof12.system_state FROM rof12_executor;
        REVOKE SELECT ON rof12.system_state, rof12.refunds FROM rof12_executor;
    """)
