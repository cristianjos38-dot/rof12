"""Add tenant-isolated document metadata and fragments."""

from alembic import op

revision = "0003_add_isolated_documents"
down_revision = "0002_add_core_security_tables"
branch_labels = None
depends_on = None

UPGRADE_SQL = """
CREATE TABLE rof12.documents (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    byte_size NUMERIC(12, 0) NOT NULL CHECK (byte_size > 0),
    content_sha256 TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    provenance_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, document_id),
    CONSTRAINT documents_content_sha256_uq UNIQUE (tenant_id, content_sha256),
    CONSTRAINT documents_provenance_fk FOREIGN KEY (tenant_id, provenance_id)
        REFERENCES rof12.provenance_records (tenant_id, provenance_id)
);

CREATE TABLE rof12.document_fragments (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    fragment_id TEXT NOT NULL,
    ordinal NUMERIC(12, 0) NOT NULL CHECK (ordinal >= 0),
    content_sha256 TEXT NOT NULL,
    text_content TEXT NOT NULL,
    is_tainted BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, document_id, fragment_id),
    CONSTRAINT document_fragments_document_fk FOREIGN KEY (tenant_id, document_id)
        REFERENCES rof12.documents (tenant_id, document_id)
);

ALTER TABLE rof12.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rof12.document_fragments ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_tenant_isolation ON rof12.documents
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY document_fragments_tenant_isolation ON rof12.document_fragments
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

REVOKE ALL ON rof12.documents, rof12.document_fragments FROM PUBLIC;
GRANT SELECT, INSERT ON rof12.documents, rof12.document_fragments TO rof12_app;
GRANT SELECT ON rof12.documents, rof12.document_fragments TO rof12_executor, rof12_audit;
REVOKE UPDATE, DELETE ON rof12.documents, rof12.document_fragments FROM rof12_app, rof12_executor, rof12_audit
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS rof12.document_fragments;
DROP TABLE IF EXISTS rof12.documents
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(DOWNGRADE_SQL)

