"""Add commercial order status for deterministic verification."""

from alembic import op

revision = "0005_add_order_status"
down_revision = "0004_add_capabilities"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE rof12.orders ADD COLUMN status TEXT NOT NULL DEFAULT 'PAID'")
    op.execute("ALTER TABLE rof12.orders ADD CONSTRAINT orders_status_ck CHECK (status IN ('PAID', 'FULFILLED', 'REFUNDABLE', 'CANCELLED'))")


def downgrade():
    op.execute("ALTER TABLE rof12.orders DROP CONSTRAINT IF EXISTS orders_status_ck")
    op.execute("ALTER TABLE rof12.orders DROP COLUMN IF EXISTS status")

