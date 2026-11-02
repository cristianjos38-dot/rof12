import io
from pathlib import Path

import pytest

from app.api.dependencies import AuthContext
from app.perception.file_validator import ValidationError, validate_artifact
from app.perception.ingestion import CHUNK_SIZE, IngestionError, receive_stream
from app.storage.artifact_store import ArtifactStorageError, ArtifactStore


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "adversarial"


def context(tenant="tenant_001"):
    return AuthContext("user_001", tenant, "operator", "ACTIVE", "user_001")


def test_all_adversarial_fixtures_stream_validate_and_store(tmp_path):
    store = ArtifactStore(str(tmp_path))
    for fixture in sorted(FIXTURES.iterdir()):
        artifact = receive_stream(context(), fixture.name, fixture.open("rb"))
        assert artifact.state.value == "RECEIVED"
        assert validate_artifact(artifact).valid is True
        stored = store.store(artifact)
        assert store.read_verified(context().tenant_id, artifact.artifact_id, stored.content_sha256) == fixture.read_bytes()
        assert stored.path.name == "original.bin"
        assert stored.path.stat().st_mode & 0o777 == 0o600


def test_ingestion_uses_64k_chunks_and_internal_uuid(tmp_path):
    class ChunkStream(io.BytesIO):
        def __init__(self, value):
            super().__init__(value)
            self.sizes = []

        def read(self, size=-1):
            self.sizes.append(size)
            return super().read(size)

    stream = ChunkStream((b"%PDF-1.7\n" + b"x" * (CHUNK_SIZE * 2)))
    artifact = receive_stream(context(), "untrusted.pdf", stream)
    assert all(size == CHUNK_SIZE for size in stream.sizes[:-1])
    assert len(artifact.artifact_id) == 36
    assert artifact.original_filename == "untrusted.pdf"


def test_ingestion_rejects_bad_extension_magic_and_oversize():
    with pytest.raises(IngestionError):
        receive_stream(context(), "malware.exe", io.BytesIO(b"MZ"))
    with pytest.raises(IngestionError):
        receive_stream(context(), "bad.pdf", io.BytesIO(b"not a pdf"))
    with pytest.raises(IngestionError):
        receive_stream(context(), "large.pdf", io.BytesIO(b"%PDF-" + b"x" * (10 * 1024 * 1024)))


def test_corrupt_artifact_is_quarantined_on_read(tmp_path):
    store = ArtifactStore(str(tmp_path))
    artifact = receive_stream(context(), "invoice.pdf", io.BytesIO((FIXTURES / "01_legitimate_invoice.pdf").read_bytes()))
    stored = store.store(artifact)
    stored.path.write_bytes(b"tampered")
    with pytest.raises(ArtifactStorageError, match="quarantined"):
        store.read_verified("tenant_001", artifact.artifact_id, stored.content_sha256)
    assert store.state("tenant_001", artifact.artifact_id).value == "QUARANTINED"
    assert (tmp_path / "quarantine" / "tenant_001" / artifact.artifact_id / "original.bin").exists()


def test_storage_uses_tenant_boundary_and_rejects_traversal(tmp_path):
    store = ArtifactStore(str(tmp_path))
    with pytest.raises(ArtifactStorageError):
        store.read_verified("../tenant_002", "00000000-0000-4000-8000-000000000000", "x")

