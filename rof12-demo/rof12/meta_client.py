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
from decimal import Decimal, InvalidOperation


SPARK_MODEL = "muse-spark-1.3"
SAM_MODEL = "sam-3.1"
WONDER_MODEL = "muse-wonder-1.0"
META_BASE_URL = "https://api.meta.ai/v1"
META_CHAT_COMPLETIONS_URL = f"{META_BASE_URL}/chat/completions"


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


@dataclass(frozen=True)
class ConversationResult:
    mode: str
    text: str
    proposal: dict
    source: str


class MetaClient:
    """Unified Meta client; absence/failure of the API is always fail-closed."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0):
        self.api_key = api_key or os.getenv("META_API_KEY", "")
        self.base_url = (base_url or META_BASE_URL).rstrip("/")
        configured_url = os.getenv("META_API_RESPONSES_URL", META_CHAT_COMPLETIONS_URL)
        self.responses_url = configured_url if configured_url == META_CHAT_COMPLETIONS_URL else META_CHAT_COMPLETIONS_URL
        self.timeout = timeout

    def call_muse_spark(self, document_bytes: bytes, prompt: str) -> SparkResult:
        payload = {"document": document_bytes.hex(), "prompt": prompt}
        result = self._call(SPARK_MODEL, payload, "Classify document risk and discrepancies. Return JSON only.")
        if result is not None:
            return SparkResult(str(result.get("risk_level", "CRITICAL")), tuple(result.get("signals", ())), bool(result.get("discrepancy", False)), "meta")
        lower = document_bytes.decode("latin-1", "ignore").lower()
        signals = tuple(signal for marker, signal in ((b"system:", "PROMPT_INJECTION"), (b"ignore", "PROMPT_INJECTION"), (b"/js", "EMBEDDED_SCRIPT")) if marker.decode() in lower)
        return SparkResult("CRITICAL" if signals else "LOW", signals, b"q900" in document_bytes.lower(), "deterministic-fallback")

    def call_sam_segmentation(self, document_bytes: bytes, points_or_queries) -> SegmentationResult:
        result = self._call(SAM_MODEL, {"document": document_bytes.hex(), "queries": points_or_queries}, "Return suspicious evidence boxes and masks as JSON only.")
        if result is not None:
            return SegmentationResult(tuple(result.get("evidence_boxes", ())), tuple(result.get("evidence_masks", ())), "meta")
        suspicious = any(marker in document_bytes.lower() for marker in (b"system:", b"ignore", b"/js", b"q900"))
        return SegmentationResult(("<|box;0,0,1,1|>",) if suspicious else (), ("<|mask;document-suspicious|>",) if suspicious else (), "deterministic-fallback")

    def call_muse_wonder(self, system_prompt: str, messages) -> WonderResult:
        result = self._call(WONDER_MODEL, {"messages": messages}, system_prompt)
        if result is not None:
            return WonderResult(str(result.get("plan", "")), dict(result.get("proposal", {})), "meta")
        text = " ".join(str(message.get("content", "")) for message in messages)
        refund = re.search(r"refund of \$([\d,.]+) to account (\S+).*?order (ORD-\d+)", text, re.I)
        if refund:
            return WonderResult("deterministic proposal from document", {"tool": "refunds.create", "args": {"order_id": refund.group(3), "amount": float(refund.group(1).replace(",", "")), "destination_account": refund.group(2).rstrip(".")}}, "deterministic-fallback")
        return WonderResult("no executable proposal", {}, "deterministic-fallback")

    def respond(self, user_text: str) -> ConversationResult:
        """Classify every turn as conversation or an untrusted tool proposal."""
        system_prompt = (
            "You are the ROF12 voice assistant. Return JSON only. For greetings, status questions, "
            "or questions about ROF12, return {\"mode\":\"conversation\",\"text\":\"...\"} "
            "with at most two concise professional Spanish sentences saying the runtime is active, "
            "monitoring threats, and ready to evaluate actions. For requests to refund, transfer, "
            "delete, or change data, return {\"mode\":\"proposal\",\"tool_name\":\"...\",\"args\":{}}. "
            "Never claim execution or authorization."
        )
        result = self._call(SPARK_MODEL, {"user_message": user_text}, system_prompt)
        if result is not None:
            mode = str(result.get("mode", "conversation")).lower()
            if mode == "proposal" or result.get("tool_name") or result.get("proposal"):
                proposal = result.get("proposal", result)
                return ConversationResult("proposal", "", dict(proposal), "meta")
            return ConversationResult("conversation", self._two_sentences(str(result.get("text", ""))), {}, "meta")

        lowered = user_text.casefold()
        if any(marker in lowered for marker in ("hola", "buenas", "qué haces", "que haces", "función", "funcion", "alertas", "sistema")):
            return ConversationResult(
                "conversation",
                "ROF12 está activo, monitorea amenazas y está listo para evaluar acciones.",
                {},
                "deterministic-fallback",
            )
        if any(marker in lowered for marker in ("reembols", "devolver", "reembolso", "transfer", "mover dinero", "borrar", "borra", "eliminar", "elimina", "cambiar datos", "cambia datos")):
            amount_match = re.search(r"(?<![\w.-])(?:q|gtq|usd|eur|\$)?\s*([0-9]+(?:[.,][0-9]{1,2})?)(?![\w.])", lowered)
            order_match = re.search(r"(?:orden|order)\s*([a-z0-9-]+)|\b(ORD-[0-9]+)\b", lowered, re.IGNORECASE)
            if "reembols" in lowered or "reembolso" in lowered or "devolver" in lowered:
                try:
                    amount = Decimal(amount_match.group(1).replace(",", ".")) if amount_match else Decimal("0")
                except InvalidOperation:
                    amount = Decimal("0")
                order_id = (order_match.group(1) or order_match.group(2)).upper() if order_match else "UNKNOWN"
                return ConversationResult("proposal", "", {"tool_name": "process_refund", "args": {"order_id": order_id, "amount": amount, "reason": user_text}}, "deterministic-fallback")
            tool = "money.transfer" if "transfer" in lowered or "mover dinero" in lowered else "records.mutate"
            return ConversationResult("proposal", "", {"tool_name": tool, "args": {"request": user_text}}, "deterministic-fallback")
        return ConversationResult(
            "conversation",
            "ROF12 está activo y listo para evaluar acciones o responder preguntas de seguridad.",
            {},
            "deterministic-fallback",
        )

    @staticmethod
    def _two_sentences(text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return " ".join(sentences[:2]) or "ROF12 está activo y listo para evaluar acciones."

    def _call(self, model: str, payload: dict, system_prompt: str) -> dict | None:
        if not self.api_key or os.getenv("MODEL_MODE", "mock") != "live":
            return None
        request = urllib.request.Request(
            self.responses_url,
            data=json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                "temperature": 0.1,
            }).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode())
                if isinstance(raw, dict) and isinstance(raw.get("choices"), list) and raw["choices"]:
                    content = raw["choices"][0].get("message", {}).get("content", "")
                    if isinstance(content, str):
                        parsed = json.loads(content)
                        return parsed if isinstance(parsed, dict) else None
                    return content if isinstance(content, dict) else None
                return raw if isinstance(raw, dict) else None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError, TypeError):
            return None
