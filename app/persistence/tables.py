from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, MetaData, Table, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.sql import text


metadata = MetaData(schema="rof12")

tenants = Table(
    "tenants", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)

users = Table(
    "users", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("user_id", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(["tenant_id"], ["rof12.tenants.tenant_id"], name="users_tenant_fk"),
)

memberships = Table(
    "memberships", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("user_id", Text, primary_key=True),
    Column("role", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(["tenant_id", "user_id"], ["rof12.users.tenant_id", "rof12.users.user_id"], name="memberships_user_fk"),
)

orders = Table(
    "orders", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("order_id", Text, primary_key=True),
    Column("owner_user_id", Text, nullable=False),
    Column("refundable_balance", NUMERIC(12, 2), nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("refundable_balance >= 0", name="orders_refundable_balance_ck"),
    ForeignKeyConstraint(["tenant_id"], ["rof12.tenants.tenant_id"], name="orders_tenant_fk"),
    ForeignKeyConstraint(["tenant_id", "owner_user_id"], ["rof12.users.tenant_id", "rof12.users.user_id"], name="orders_owner_user_fk"),
)

order_balances = Table(
    "order_balances", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("order_id", Text, primary_key=True),
    Column("available_amount", NUMERIC(12, 2), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("available_amount >= 0", name="order_balances_available_amount_ck"),
    ForeignKeyConstraint(["tenant_id", "order_id"], ["rof12.orders.tenant_id", "rof12.orders.order_id"], name="order_balances_order_fk"),
)

refunds = Table(
    "refunds", metadata,
    Column("refund_id", Text, primary_key=True),
    Column("tenant_id", Text, nullable=False),
    Column("order_id", Text, nullable=False),
    Column("operation_id", Text, nullable=False),
    Column("amount", NUMERIC(12, 2), nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("amount > 0", name="refunds_amount_ck"),
    UniqueConstraint("tenant_id", "operation_id", name="refunds_operation_uq"),
    ForeignKeyConstraint(["tenant_id", "order_id"], ["rof12.orders.tenant_id", "rof12.orders.order_id"], name="refunds_order_fk"),
)

provenance_records = Table(
    "provenance_records", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("provenance_id", Text, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_uri", Text, nullable=False),
    Column("fragment_hash", Text, nullable=False),
    Column("contamination_status", Text, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(["tenant_id"], ["rof12.tenants.tenant_id"], name="provenance_records_tenant_fk"),
)

documents = Table(
    "documents", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("document_id", Text, primary_key=True),
    Column("original_filename", Text, nullable=False),
    Column("media_type", Text, nullable=False),
    Column("byte_size", NUMERIC(12, 0), nullable=False),
    Column("content_sha256", Text, nullable=False),
    Column("storage_key", Text, nullable=False),
    Column("provenance_id", Text, nullable=False),
    Column("created_by", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("tenant_id", "content_sha256", name="documents_content_sha256_uq"),
    ForeignKeyConstraint(["tenant_id", "provenance_id"], ["rof12.provenance_records.tenant_id", "rof12.provenance_records.provenance_id"], name="documents_provenance_fk"),
)

document_fragments = Table(
    "document_fragments", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("document_id", Text, primary_key=True),
    Column("fragment_id", Text, primary_key=True),
    Column("ordinal", NUMERIC(12, 0), nullable=False),
    Column("content_sha256", Text, nullable=False),
    Column("text_content", Text, nullable=False),
    Column("is_tainted", Text, nullable=False, server_default=text("'true'")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(["tenant_id", "document_id"], ["rof12.documents.tenant_id", "rof12.documents.document_id"], name="document_fragments_document_fk"),
)

audit_events = Table(
    "audit_events", metadata,
    Column("event_id", Text, primary_key=True),
    Column("tenant_id", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("actor_user_id", Text, nullable=False),
    Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(["tenant_id"], ["rof12.tenants.tenant_id"], name="audit_events_tenant_fk"),
    ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["rof12.users.tenant_id", "rof12.users.user_id"], name="audit_events_actor_user_fk"),
)

