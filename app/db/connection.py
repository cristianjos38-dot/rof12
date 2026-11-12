import os

from sqlalchemy import create_engine

from app.config import DATABASE_PREPARE_THRESHOLD


def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://rof12_app:rof12_app_dev@localhost:5432/rof12")


def create_app_engine():
    """Create the API engine; migration code must use DATABASE_OWNER_URL instead."""
    connect_args = {}
    if DATABASE_PREPARE_THRESHOLD.lower() == "none":
        # Required for PgBouncer/Supabase transaction pooling.
        connect_args["prepare_threshold"] = None
    elif DATABASE_PREPARE_THRESHOLD.isdigit():
        connect_args["prepare_threshold"] = int(DATABASE_PREPARE_THRESHOLD)
    return create_engine(database_url(), pool_pre_ping=True, connect_args=connect_args)


def create_executor_engine():
    """Use the dedicated executor role for irreversible security mutations."""
    url = os.getenv("DATABASE_EXECUTOR_URL") or database_url()
    connect_args = {}
    if DATABASE_PREPARE_THRESHOLD.lower() == "none":
        connect_args["prepare_threshold"] = None
    elif DATABASE_PREPARE_THRESHOLD.isdigit():
        connect_args["prepare_threshold"] = int(DATABASE_PREPARE_THRESHOLD)
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)

