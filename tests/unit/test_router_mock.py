import pytest

from app.agents.model_router import ModelRouter


def test_mock_router_loads_fixture():
    result = ModelRouter(mode="mock").complete("spark_ok.json")
    assert result.action == "refund"


def test_non_mock_router_is_blocked():
    with pytest.raises(RuntimeError):
        ModelRouter(mode="external").complete("spark_ok.json")

