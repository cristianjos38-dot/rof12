import os


MODEL_MODE = os.getenv("MODEL_MODE", "mock").lower()
APP_ENV = os.getenv("APP_ENV", "local")
DOCUMENT_STORAGE_ROOT = os.getenv("DOCUMENT_STORAGE_ROOT", "/tmp/rof12-documents")
JWT_SECRET = os.getenv("JWT_SECRET", "rof12-local-secret-change-me-32-bytes")
JWT_ISSUER = os.getenv("JWT_ISSUER", "rof12-auth")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "rof12-api")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

if APP_ENV == "production" and JWT_SECRET == "rof12-local-secret-change-me-32-bytes":
    raise RuntimeError("JWT_SECRET must be configured outside local development")

