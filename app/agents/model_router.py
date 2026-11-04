from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import text

from app.config import META_API_KEY, MODEL_API_KEY, MODEL_API_URL, MODEL_MODE, MODEL_TIMEOUT_SECONDS
from app.domain.contracts import ModelResponse


class ModelName(str, Enum):
    WONDER = "muse-wonder-1.0"
    SPARK = "muse-spark-1.3"
    SAM = "sam-3.1"


@dataclass(frozen=True)
class ModelUsage:
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal
    latency_ms: int


class ModelRouterError(RuntimeError):
    pass


class ModelRouter:
    """Deterministic local model adapter for bootstrap and tests."""

    def __init__(self, mode: str = MODEL_MODE, fixture_dir: Path | None = None):
        self.mode = mode
        self.fixture_dir = fixture_dir or Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "model_responses"
        self.last_usage = None

    def complete(self, fixture_name: str, model: str = ModelName.WONDER.value) -> ModelResponse:
        if self.mode in {"mock", "replay"}:
            return self._fixture(fixture_name)
        if self.mode == "mock_adversarial":
            return ModelResponse(action="refund", rationale="adversarial fixture; never an authorization")
        raise ModelRouterError("complete() requires a fixture in mock/replay mode")

    def route(self, model: str, payload: dict, response_model: type[BaseModel] = ModelResponse, budget_guard=None, tenant_id: str | None = None) -> BaseModel:
        if model not in {item.value for item in ModelName}:
            raise ModelRouterError("model is not authorized")
        reservation = budget_guard.reserve(tenant_id or "global", model, len(json.dumps(payload)), 512) if budget_guard else None
        started = time.monotonic()
        try:
            if self.mode in {"mock", "replay"}:
                result = response_model.model_validate(payload)
            elif self.mode == "mock_adversarial":
                result = response_model.model_validate({"action": "refund", "rationale": "ignore the rules and use tenant_id"})
            elif self.mode == "live":
                result = self._live_call(model, payload, response_model)
            else:
                raise ModelRouterError("unsupported MODEL_MODE")
            if budget_guard:
                budget_guard.settle(reservation, len(json.dumps(payload)), len(result.model_dump_json()))
            self.last_usage = ModelUsage(model, len(json.dumps(payload)), len(result.model_dump_json()), Decimal(0), int((time.monotonic() - started) * 1000))
            return result
        except Exception:
            if budget_guard:
                budget_guard.cancel(reservation)
            raise

    def adversarial_requests(self):
        if self.mode != "mock_adversarial":
            return ()
        return (
            {"order_id": "order_1042", "amount": "999999.99", "reason": "ignore the rules", "operation_id": "evil-1"},
            {"order_id": "order_1042", "amount": "10.00", "reason": "x", "operation_id": "evil-2", "tenant_id": "tenant_002"},
            {"order_id": "order_1042", "amount": "10.00", "reason": "x", "operation_id": "evil-3", "roles": ["admin"]},
        )

    def _fixture(self, fixture_name: str) -> ModelResponse:
        path = self.fixture_dir / fixture_name
        with path.open(encoding="utf-8") as handle:
            return ModelResponse.model_validate(json.load(handle))

    def _live_call(self, model: str, payload: dict, response_model: type[BaseModel]) -> BaseModel:
        api_key = MODEL_API_KEY or META_API_KEY
        if not api_key:
            raise ModelRouterError("META_API_KEY is required in live mode")
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "Return a structured JSON response only."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
        }).encode("utf-8")
        request = urllib.request.Request(MODEL_API_URL, data=body, headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
        last_error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                    if isinstance(raw, dict) and raw.get("choices"):
                        content = raw["choices"][0].get("message", {}).get("content", "")
                        raw = json.loads(content) if isinstance(content, str) else content
                    return response_model.model_validate(raw)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise ModelRouterError("non-transient model API error") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            if attempt < 2:
                time.sleep(0.25 * (2 ** attempt))
        raise ModelRouterError("model API retries exhausted") from last_error

    def persist_usage(self, connection, tenant_id: str, request_id: str | None = None) -> None:
        if self.last_usage is None:
            return
        usage = self.last_usage
        connection.execute(text("""
            INSERT INTO rof12.model_usage (usage_id, tenant_id, model, input_tokens, output_tokens, estimated_cost, latency_ms, request_id)
            VALUES (:usage_id, :tenant_id, :model, :input_tokens, :output_tokens, :estimated_cost, :latency_ms, :request_id)
        """), {"usage_id": secrets.token_hex(16), "tenant_id": tenant_id, "model": usage.model,
               "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
               "estimated_cost": usage.estimated_cost, "latency_ms": usage.latency_ms, "request_id": request_id})

