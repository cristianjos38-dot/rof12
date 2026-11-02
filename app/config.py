import os

MODEL_MODE = os.getenv("MODEL_MODE", "mock").lower()
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MODEL_API_URL = os.getenv("MODEL_API_URL", "https://api.meta.ai/v1/models")
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "15"))
APP_ENV = os.getenv("APP_ENV", "local")
DOCUMENT_STORAGE_ROOT = os.getenv("DOCUMENT_STORAGE_ROOT", "/tmp/rof12-documents")
JWT_SECRET = os.getenv("JWT_SECRET", "rof12-local-secret-change-me-32-bytes")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "rof12-auth")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "rof12-api")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
DATABASE_PREPARE_THRESHOLD = os.getenv("DATABASE_PREPARE_THRESHOLD", "default")

if APP_ENV in {"staging", "production"}:
    if JWT_ALGORITHM.startswith("RS") and not JWT_PUBLIC_KEY:
        raise RuntimeError("JWT_PUBLIC_KEY must be configured for asymmetric staging/production JWTs")
    if JWT_ALGORITHM.startswith("HS") and JWT_SECRET == "rof12-local-secret-change-me-32-bytes":
        raise RuntimeError("JWT_SECRET must be configured outside local development")

