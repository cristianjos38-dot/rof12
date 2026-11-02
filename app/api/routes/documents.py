import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import AuthContext, get_auth_context
from app.documents import DocumentIngestor, DocumentUpload

router = APIRouter(prefix="/documents", tags=["documents"])
ingestor = DocumentIngestor()


class DocumentUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=127)
    content_base64: str = Field(min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(payload: DocumentUploadRequest, context: AuthContext = Depends(get_auth_context)) -> dict:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        stored = ingestor.ingest(context, DocumentUpload(filename=payload.filename, media_type=payload.media_type, content=content))
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid document") from exc
    return {"document_id": stored.document_id, "tenant_id": stored.tenant_id, "content_sha256": stored.content_sha256, "byte_size": stored.byte_size}

