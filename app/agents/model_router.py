import json
from pathlib import Path

from app.config import MODEL_MODE
from app.domain.contracts import ModelResponse


class ModelRouter:
    """Deterministic local model adapter for bootstrap and tests."""

    def __init__(self, mode: str = MODEL_MODE, fixture_dir: Path = None):
        self.mode = mode
        self.fixture_dir = fixture_dir or Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "model_responses"

    def complete(self, fixture_name: str) -> ModelResponse:
        if self.mode != "mock":
            raise RuntimeError("Only MODEL_MODE=mock is enabled in ROF12 bootstrap")
        path = self.fixture_dir / fixture_name
        with path.open(encoding="utf-8") as handle:
            return ModelResponse.model_validate(json.load(handle))

