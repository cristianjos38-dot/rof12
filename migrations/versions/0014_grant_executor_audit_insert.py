"""Allow the executor transaction to append its own atomic audit event."""

from alembic import op

revision = "0014_grant_executor_audit_insert"
down_revision = "0013_hold_resolution_justification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT INSERT ON rof12.audit_events TO rof12_executor")


def downgrade() -> None:
    op.execute("REVOKE INSERT ON rof12.audit_events FROM rof12_executor")
