from fastapi import APIRouter

from app.db.connection import create_app_engine

router = APIRouter()


@router.get("/health")
def health() -> dict:
    database = "unavailable"
    try:
        with create_app_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
            database = "ok"
    except Exception:
        database = "unavailable"
    return {"status": "ok", "service": "rof12", "database": database}

