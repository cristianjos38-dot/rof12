"""Optional Meta model adapters with deterministic, offline-safe fallbacks.

The client never grants authority. Every Wonder proposal remains untrusted data
until the existing Gate evaluates it.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


SPARK_MODEL = "muse-spark-1.3"
SAM_MODEL = "sam-3.1"
WONDER_MODEL = "muse-wonder-1.0"


@dataclass(frozen=True)
class SparkResult:
    risk_level: str
    signals: tuple[str, ...]
    discrepancy: bool
    source: str


@dataclass(frozen=True)
class SegmentationResult:
    evidence_boxes: tuple[str, ...]
    evidence_masks: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class WonderResult:
    plan: str
    proposal: dict
    source: str


class MetaClient:
    """Unified Meta client; absence/failure of the API is always fail-closed."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0):
        self.api_key = api_key or os.getenv("META_API_KEY", "")
        self.base_url = (base_url or os.getenv("META_API_BASE_URL", "https://api.meta.com/v1")).rstrip("/")
        self.responses_url = os.getenv("META_API_RESPONSES_URL", f"{self.base_url}/responses")
        self.timeout = timeout

    def call_muse_spark(self, document_bytes: bytes, prompt: str) -> SparkResult:
        payload = {"document": document_bytes.hex(), "prompt": prompt}
        result = self._call(SPARK_MODEL, payload)
        if result is not None:
            return SparkResult(str(result.get("risk_level", "CRITICAL")), tuple(result.get("signals", ())), bool(result.get("discrepancy", False)), "meta")
        lower = document_bytes.decode("latin-1", "ignore").lower()
        signals = tuple(signal for marker, signal in ((b"system:", "PROMPT_INJECTION"), (b"ignore", "PROMPT_INJECTION"), (b"/js", "EMBEDDED_SCRIPT")) if marker.decode() in lower)
        return SparkResult("CRITICAL" if signals else "LOW", signals, b"q900" in document_bytes.lower(), "deterministic-fallback")

    def call_sam_segmentation(self, document_bytes: bytes, points_or_queries) -> SegmentationResult:
        result = self._call(SAM_MODEL, {"document": document_bytes.hex(), "queries": points_or_queries})
        if result is not None:
            return SegmentationResult(tuple(result.get("evidence_boxes", ())), tuple(result.get("evidence_masks", ())), "meta")
        suspicious = any(marker in document_bytes.lower() for marker in (b"system:", b"ignore", b"/js", b"q900"))
        return SegmentationResult(("<|box;0,0,1,1|>",) if suspicious else (), ("<|mask;document-suspicious|>",) if suspicious else (), "deterministic-fallback")

    def call_muse_wonder(self, system_prompt: str, messages) -> WonderResult:
        result = self._call(WONDER_MODEL, {"system": system_prompt, "messages": messages})
        if result is not None:
            return WonderResult(str(result.get("plan", "")), dict(result.get("proposal", {})), "meta")
        text = " ".join(str(message.get("content", "")) for message in messages)
        refund = re.search(r"refund of \$([\d,.]+) to account (\S+).*?order (ORD-\d+)", text, re.I)
        if refund:
            return WonderResult("deterministic proposal from document", {"tool": "refunds.create", "args": {"order_id": refund.group(3), "amount": float(refund.group(1).replace(",", "")), "destination_account": refund.group(2).rstrip(".")}}, "deterministic-fallback")
        return WonderResult("no executable proposal", {}, "deterministic-fallback")

    def _call(self, model: str, payload: dict) -> dict | None:
        if not self.api_key or os.getenv("MODEL_MODE", "mock") != "live":
            return None
        request = urllib.request.Request(
            self.responses_url,
            data=json.dumps({"model": model, "input": payload}).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return None
