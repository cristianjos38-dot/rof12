import os

import pytest


@pytest.mark.skipif(not os.getenv("ROF12_TEST_DATABASE_URL"), reason="requires live PostgreSQL Docker database")
def test_postgres_restart_resilience():
    pytest.fail("live resilience harness is enabled only with ROF12_TEST_DATABASE_URL and Docker orchestration")

