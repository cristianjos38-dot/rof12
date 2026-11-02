from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.connection import create_app_engine

router = APIRouter()


@router.get("/health")
def health() -> dict:
    database = "unavailable"
    try:
        with create_app_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
            database = "ok"
    except SQLAlchemyError:
        database = "unavailable"
    return {"status": "ok", "service": "rof12", "database": database}


@router.get("/health/ready")
def readiness() -> dict:
    """Container readiness probe: return success only when PostgreSQL answers."""
    try:
        with create_app_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable") from exc
    return {"status": "ready", "service": "rof12", "database": "ok"}

