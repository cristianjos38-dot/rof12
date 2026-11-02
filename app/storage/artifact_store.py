import hashlib
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.perception.ingestion import ArtifactState, ReceivedArtifact


class ArtifactStorageError(ValueError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    artifact_id: str
    tenant_id: str
    path: Path
    content_sha256: str
    state: ArtifactState


class ArtifactStore:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.quarantine = self.root / "quarantine"
        self.quarantine.mkdir(mode=0o700, exist_ok=True)
        self._states: dict[tuple, ArtifactState] = {}

    @staticmethod
    def _check_tenant(value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ArtifactStorageError("invalid tenant id")
        return value

    @staticmethod
    def _check_id(value: str, label: str) -> str:
        try:
            uuid.UUID(value)
        except (ValueError, AttributeError) as exc:
            raise ArtifactStorageError(f"invalid {label}") from exc
        return value

    def _artifact_dir(self, tenant_id: str, artifact_id: str) -> Path:
        self._check_tenant(tenant_id)
        self._check_id(artifact_id, "artifact id")
        base = (self.root / tenant_id / artifact_id).resolve()
        tenant_root = (self.root / tenant_id).resolve()
        if tenant_root not in base.parents:
            raise ArtifactStorageError("storage boundary violation")
        return base

    def store(self, artifact: ReceivedArtifact) -> StoredArtifact:
        artifact_dir = self._artifact_dir(artifact.tenant_id, artifact.artifact_id)
        artifact_dir.parent.mkdir(mode=0o700, exist_ok=True)
        os.chmod(artifact_dir.parent, 0o700)
        artifact_dir.mkdir(mode=0o700, exist_ok=False)
        target = artifact_dir / "original.bin"
        with target.open("xb") as handle:
            handle.write(artifact.content)
        os.chmod(target, 0o600)
        self._states[(artifact.tenant_id, artifact.artifact_id)] = ArtifactState.RECEIVED
        return StoredArtifact(artifact.artifact_id, artifact.tenant_id, target, artifact.content_sha256, ArtifactState.RECEIVED)

    def mark_validated(self, tenant_id: str, artifact_id: str) -> None:
        self._check_id(artifact_id, "artifact id")
        if not (self._artifact_dir(tenant_id, artifact_id) / "original.bin").is_file():
            raise ArtifactStorageError("artifact not found")
        self._states[(tenant_id, artifact_id)] = ArtifactState.VALIDATED

    def read_verified(self, tenant_id: str, artifact_id: str, expected_sha256: str) -> bytes:
        artifact_dir = self._artifact_dir(tenant_id, artifact_id)
        target = artifact_dir / "original.bin"
        if not target.is_file():
            raise ArtifactStorageError("artifact not found")
        content = target.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected_sha256:
            self._quarantine(tenant_id, artifact_id)
            raise ArtifactStorageError("artifact integrity check failed; quarantined")
        return content

    def state(self, tenant_id: str, artifact_id: str) -> ArtifactState:
        return self._states.get((tenant_id, artifact_id), ArtifactState.QUARANTINED)

    def _quarantine(self, tenant_id: str, artifact_id: str) -> None:
        source = self._artifact_dir(tenant_id, artifact_id)
        if source.exists():
            destination = self.quarantine / tenant_id / artifact_id
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        self._states[(tenant_id, artifact_id)] = ArtifactState.QUARANTINED

