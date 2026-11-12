"""Bind persisted gate decisions to the evaluated proposal."""

from alembic import op

revision = "0011_gate_proposal_hash"
down_revision = "0010_system_state_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE rof12.gate_decisions ADD COLUMN proposal_hash TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE rof12.gate_decisions DROP COLUMN IF EXISTS proposal_hash")
