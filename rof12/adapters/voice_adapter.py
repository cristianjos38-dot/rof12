"""Bidirectional macOS voice I/O for human proposals and Gate decisions.

Voice input is treated exactly like any other untrusted proposal.  This module
does not execute tools or grant authority; callers must pass the returned
proposal through the SecurityGate and may only speak the resulting decision.
SpeechRecognition and PyAudio are optional so CI and keyboard-only demos stay
offline and deterministic.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable


DECISION_MESSAGES = {
    "ALLOW": "Acción autorizada. Permiso HMAC emitido.",
    "DENY": "Acción denegada por política determinista.",
    "QUARANTINE": "Peligro. Inyección detectada. Documento en cuarentena.",
    "HOLD": "Atención. Operación retenida. ¿Desea autorizar la ejecución?",
    "REQUIRE_APPROVAL": "Atención. Operación retenida. ¿Desea autorizar la ejecución?",
}


@dataclass(frozen=True)
class VoiceProposal:
    """Human-spoken intent, still untrusted until evaluated by the Gate."""

    task_id: str
    agent: str
    tool: str
    args: dict
    rationale: str
    tenant_id: str


def speak(text: str, voice: str = "Monica") -> None:
    """Speak a bounded, caller-provided status message using macOS ``say``."""
    if not text or len(text) > 500:
        raise ValueError("speech text must be between 1 and 500 characters")
    subprocess.run(["say", "-v", voice, text], check=False)


def speak_decision(decision: str, speaker: Callable[[str], None] = speak) -> str:
    """Speak the fixed message associated with a Gate decision."""
    normalized = decision.upper()
    message = DECISION_MESSAGES.get(normalized, DECISION_MESSAGES["DENY"])
    speaker(message)
    return message


def listen_text(*, timeout: float = 5.0, phrase_time_limit: float = 12.0) -> str:
    """Capture one microphone phrase, or raise a clear optional-dependency error."""
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError("SpeechRecognition no está instalado; usa --keyboard") from exc

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        # Google recognition is intentionally opt-in at the runner level because
        # it is a network service; callers can instead use keyboard fallback.
        return recognizer.recognize_google(audio, language="es-GT")
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("no se detectó voz dentro del tiempo límite") from exc
    except (sr.UnknownValueError, sr.RequestError) as exc:
        raise RuntimeError("no fue posible transcribir la entrada de voz") from exc
    except OSError as exc:
        raise RuntimeError("micrófono no disponible") from exc


def parse_proposal(
    text: str,
    *,
    task_id: str = "TKT-1042",
    agent: str = "support-agent-01",
    tenant_id: str = "tenant_001",
) -> VoiceProposal:
    """Parse a deliberately small command grammar into an untrusted proposal."""
    if not text or len(text) > 1000:
        raise ValueError("comando vacío o demasiado largo")
    lowered = text.casefold()
    if any(marker in lowered for marker in ("exporta", "exportar", "base de datos", "shell", "terminal")):
        return VoiceProposal(task_id, agent, "db.export_customers", {"destination": "voice-request"}, text, tenant_id)
    amount_match = re.search(r"(?:q|\$|usd\s*)\s*([0-9]+(?:[.,][0-9]{1,2})?)", lowered)
    order_match = re.search(r"(?:orden|order)\s*([a-z0-9-]+)", lowered, re.IGNORECASE)
    if not amount_match or not order_match:
        raise ValueError("usa, por ejemplo: reembolsa Q45.00 en la orden ORD-7731")
    try:
        amount = Decimal(amount_match.group(1).replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("importe inválido") from exc
    if not amount.is_finite():
        raise ValueError("importe no finito")
    return VoiceProposal(
        task_id,
        agent,
        "refunds.create",
        {"order_id": order_match.group(1).upper(), "amount": amount, "reason": "propuesta recibida por voz"},
        text,
        tenant_id,
    )


def approval_from_text(text: str) -> bool:
    """Return True only for an explicit approval word; everything else denies."""
    return text.strip().casefold() in {"autorizar", "autorizo", "aprobar", "apruebo", "sí", "si"}
