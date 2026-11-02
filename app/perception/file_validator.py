from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.perception.ingestion import MAX_ARTIFACT_BYTES, ReceivedArtifact


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidationResult:
    artifact_id: str
    valid: bool
    media_kind: str


def validate_artifact(artifact: ReceivedArtifact) -> ValidationResult:
    if artifact.byte_size <= 0 or artifact.byte_size > MAX_ARTIFACT_BYTES:
        raise ValidationError("invalid artifact size")
    try:
        if artifact.extension == ".pdf":
            reader = PdfReader(BytesIO(artifact.content), strict=True)
            if len(reader.pages) < 1:
                raise ValidationError("PDF has no pages")
            kind = "pdf"
        else:
            with Image.open(BytesIO(artifact.content)) as image:
                image.verify()
            with Image.open(BytesIO(artifact.content)) as image:
                image.load()
            kind = "image"
    except (OSError, ValueError, UnidentifiedImageError, PdfReadError) as exc:
        raise ValidationError("malformed or corrupt document") from exc
    return ValidationResult(artifact.artifact_id, True, kind)

