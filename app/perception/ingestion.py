import hashlib
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO

from app.api.dependencies import AuthContext

CHUNK_SIZE = 64 * 1024
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg"})
MAGIC_BYTES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


class ArtifactState(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class ReceivedArtifact:
    artifact_id: str
    tenant_id: str
    original_filename: str
    extension: str
    content_sha256: str
    byte_size: int
    content: bytes
    state: ArtifactState = ArtifactState.RECEIVED


class IngestionError(ValueError):
    pass


def _extension(filename: str) -> str:
    # The name is metadata only; it is never used to build a filesystem path.
    suffix = os.path.splitext(os.path.basename(filename))[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise IngestionError("unsupported document extension")
    return suffix


def receive_stream(context: AuthContext, original_filename: str, stream: BinaryIO) -> ReceivedArtifact:
    extension = _extension(original_filename)
    artifact_id = str(uuid.uuid4())
    digest = hashlib.sha256()
    chunks = []
    total = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise IngestionError("stream must return bytes")
        total += len(chunk)
        if total > MAX_ARTIFACT_BYTES:
            raise IngestionError("document exceeds 10 MiB limit")
        digest.update(chunk)
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise IngestionError("document is empty")
    if not any(content.startswith(magic) for magic in MAGIC_BYTES[extension]):
        raise IngestionError("magic bytes do not match extension")
    return ReceivedArtifact(artifact_id, context.tenant_id, original_filename, extension, digest.hexdigest(), total, content)

