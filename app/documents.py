import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import AuthContext
from app.config import DOCUMENT_STORAGE_ROOT
from app.provenance import ProvenanceTracker, TaintedValue

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


class DocumentUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=127)
    content: bytes = Field(min_length=1, max_length=MAX_DOCUMENT_BYTES)


@dataclass(frozen=True)
class StoredDocument:
    tenant_id: str
    document_id: str
    storage_key: str
    content_sha256: str
    byte_size: int
    provenance: TaintedValue[bytes]


class DocumentIngestor:
    def __init__(self, root: Optional[str] = None, provenance: Optional[ProvenanceTracker] = None):
        self.root = Path(root or DOCUMENT_STORAGE_ROOT).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.provenance = provenance or ProvenanceTracker()

    @staticmethod
    def _validate_filename(filename: str) -> str:
        if filename in {".", ".."} or Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError("filename must be a simple leaf name")
        return filename

    def ingest(self, context: AuthContext, upload: DocumentUpload) -> StoredDocument:
        filename = self._validate_filename(upload.filename)
        document_id = secrets.token_hex(16)
        digest = hashlib.sha256(upload.content).hexdigest()
        tenant_root = (self.root / context.tenant_id).resolve()
        if self.root not in tenant_root.parents:
            raise ValueError("invalid tenant storage boundary")
        tenant_root.mkdir(mode=0o700, exist_ok=True)
        storage_key = "%s/%s/%s" % (context.tenant_id, document_id, filename)
        target = (tenant_root / document_id / filename).resolve()
        if tenant_root not in target.parents:
            raise ValueError("invalid storage boundary")
        target.parent.mkdir(mode=0o700, exist_ok=False)
        with target.open("xb") as handle:
            handle.write(upload.content)
        os.chmod(target, 0o600)
        source_id = "document:%s" % document_id
        tainted = self.provenance.extract(upload.content, source_id, "external_document", digest)
        return StoredDocument(context.tenant_id, document_id, storage_key, digest, len(upload.content), tainted)

