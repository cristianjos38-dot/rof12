import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv("ROF12_TEST_DATABASE_URL"), reason="requires live PostgreSQL Docker database")
def test_postgres_restart_resilience():
    engine = create_engine(os.environ["ROF12_TEST_DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
    with create_engine(os.environ["ROF12_TEST_DATABASE_URL"], pool_pre_ping=True).connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

