from pathlib import Path

import pytest

from app.api.dependencies import AuthContext
from app.documents import DocumentIngestor, DocumentUpload
from app.provenance import TrustLevel


def context(tenant="tenant_001"):
    return AuthContext("user_001", tenant, "operator", "ACTIVE", "user_001")


def test_document_is_stored_under_tenant_boundary_and_tainted(tmp_path: Path):
    stored = DocumentIngestor(str(tmp_path)).ingest(context(), DocumentUpload(filename="invoice.txt", media_type="text/plain", content=b"order_1042"))
    target = tmp_path / stored.storage_key
    assert target.read_bytes() == b"order_1042"
    assert target.stat().st_mode & 0o777 == 0o600
    assert stored.provenance.is_tainted is True
    assert stored.provenance.trust_level is TrustLevel.UNTRUSTED
    assert stored.storage_key.startswith("tenant_001/")


def test_document_filename_cannot_escape_tenant_storage(tmp_path: Path):
    ingestor = DocumentIngestor(str(tmp_path))
    with pytest.raises(ValueError):
        ingestor.ingest(context(), DocumentUpload(filename="../secret.txt", media_type="text/plain", content=b"x"))
    with pytest.raises(ValueError):
        ingestor.ingest(context(), DocumentUpload(filename="tenant_002/secret.txt", media_type="text/plain", content=b"x"))


def test_document_input_rejects_agent_identity_fields():
    with pytest.raises(ValueError):
        DocumentUpload(filename="x.txt", media_type="text/plain", content=b"x", tenant_id="tenant_002")  # pyright: ignore[reportCallIssue]

