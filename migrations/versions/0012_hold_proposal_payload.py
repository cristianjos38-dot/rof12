"""Persist the proposal required for hold revalidation."""

from alembic import op

revision = "0012_hold_proposal_payload"
down_revision = "0011_gate_proposal_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE rof12.holds ADD COLUMN proposal JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE rof12.holds ADD COLUMN capability_token_hash TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE rof12.holds DROP COLUMN IF EXISTS capability_token_hash")
    op.execute("ALTER TABLE rof12.holds DROP COLUMN IF EXISTS proposal")
