import os

MODEL_MODE = os.getenv("MODEL_MODE", "mock").lower()
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
META_API_KEY = os.getenv("META_API_KEY", "")
META_API_BASE_URL = "https://api.meta.ai/v1"
META_API_RESPONSES_URL = "https://api.meta.ai/v1/chat/completions"
MODEL_API_URL = os.getenv("MODEL_API_URL", META_API_RESPONSES_URL)
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "15"))
_APP_ENV_CONFIGURED = os.getenv("APP_ENV")
APP_ENV = _APP_ENV_CONFIGURED or "local"
DOCUMENT_STORAGE_ROOT = os.getenv("DOCUMENT_STORAGE_ROOT", "/tmp/rof12-documents")
JWT_SECRET = os.getenv("JWT_SECRET", "rof12-local-secret-change-me-32-bytes")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "rof12-auth")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "rof12-api")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
DATABASE_PREPARE_THRESHOLD = os.getenv("DATABASE_PREPARE_THRESHOLD", "default")

if _APP_ENV_CONFIGURED is None and os.getenv("DATABASE_URL"):
    raise RuntimeError("APP_ENV must be explicit when DATABASE_URL is configured")
if APP_ENV in {"staging", "production", "ci"}:
    if JWT_ALGORITHM.startswith(("RS", "ES")) and not JWT_PUBLIC_KEY:
        raise RuntimeError("JWT_PUBLIC_KEY must be configured for asymmetric deployments")
    if JWT_ALGORITHM.startswith("HS") and JWT_SECRET == "rof12-local-secret-change-me-32-bytes":
        raise RuntimeError("JWT_SECRET must be configured outside local development")

