import os

from sqlalchemy import create_engine


def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://rof12_app:rof12_app_dev@localhost:5432/rof12")


def create_app_engine():
    """Create the API engine; migration code must use DATABASE_OWNER_URL instead."""
    return create_engine(database_url(), pool_pre_ping=True)

