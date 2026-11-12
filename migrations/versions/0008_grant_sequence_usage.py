"""Grant application roles the sequence privileges needed for audited inserts."""

from alembic import op


revision = "0009_grant_sequence_usage"
down_revision = "0008_add_model_usage_request_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rof12 "
        "TO rof12_app, rof12_executor, rof12_audit"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rof12 "
        "FROM rof12_app, rof12_executor, rof12_audit"
    )
