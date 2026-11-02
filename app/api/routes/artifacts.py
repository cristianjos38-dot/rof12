import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import AuthContext, get_auth_context
from app.api.state import api_state
from app.documents import DocumentIngestor, DocumentUpload

router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])
ingestor = DocumentIngestor()


class ArtifactUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=127)
    content_base64: str = Field(min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_artifact(payload: ArtifactUpload, context: AuthContext = Depends(get_auth_context)):
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        stored = ingestor.ingest(context, DocumentUpload(filename=payload.filename, media_type=payload.media_type, content=content))
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(400, detail="invalid artifact") from exc
    data = {"artifact_id": stored.document_id, "tenant_id": context.tenant_id, "content_sha256": stored.content_sha256, "byte_size": stored.byte_size, "risk_report": None}
    with api_state.lock:
        api_state.artifacts[(context.tenant_id, stored.document_id)] = data
    return data


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str, context: AuthContext = Depends(get_auth_context)):
    with api_state.lock:
        artifact = api_state.artifacts.get((context.tenant_id, artifact_id))
    if artifact is None:
        raise HTTPException(404, detail="artifact not found")
    return artifact

