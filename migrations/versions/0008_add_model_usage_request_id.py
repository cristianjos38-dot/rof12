"""Add request correlation to model usage."""

from alembic import op

revision = "0008_add_model_usage_request_id"
down_revision = "0007_add_model_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE rof12.model_usage ADD COLUMN request_id TEXT")


def downgrade():
    op.execute("ALTER TABLE rof12.model_usage DROP COLUMN IF EXISTS request_id")

