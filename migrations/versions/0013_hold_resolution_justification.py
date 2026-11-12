"""Persist human approval metadata for hold resolution auditing."""

from alembic import op

revision = "0013_hold_resolution_justification"
down_revision = "0012_hold_proposal_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE rof12.holds ADD COLUMN justification TEXT NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE rof12.holds DROP COLUMN IF EXISTS justification")
