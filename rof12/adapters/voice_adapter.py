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
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable
from pathlib import Path


DECISION_MESSAGES = {
    "ALLOW": "Acción autorizada. Permiso HMAC emitido por SecurityGate.",
    "DENY": "Acción denegada por política determinista.",
    "DENY_ORDER_NOT_FOUND": "Acción denegada por SecurityGate. La orden especificada no existe.",
    "QUARANTINE": "Alerta de seguridad. Inyección detectada. Documento en cuarentena.",
    "HOLD": "Atención. Operación retenida. ¿Desea autorizar la ejecución?",
    "REQUIRE_APPROVAL": "Atención. Operación retenida. ¿Desea autorizar la ejecución?",
}
DEFAULT_VOICE = "es-MX-JorgeNeural"
FALLBACK_VOICE = "Paulina"
ALERT_AUDIO_PATH = Path("/tmp/rof12_alert.mp3")
INVALID_COMMAND_MESSAGE = "No pude interpretar la orden. Por favor especifique el monto y el identificador."


@dataclass(frozen=True)
class VoiceProposal:
    """Human-spoken intent, still untrusted until evaluated by the Gate."""

    task_id: str
    agent: str
    tool: str
    args: dict
    rationale: str
    tenant_id: str


def _installed_voices() -> list[tuple[str, bool]]:
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
    except OSError:
        return []
    voices: list[tuple[str, bool]] = []
    for line in (result.stdout or "").splitlines():
        fields = line.strip().split(maxsplit=1) if line.strip() else []
        name = fields[0] if fields else ""
        if name:
            voices.append((name, "es_" in line))
    return voices


def _resolve_voice(preferred: str) -> str | None:
    installed = _installed_voices()
    names = {name for name, _ in installed}
    if preferred in names:
        return preferred
    spanish = next((name for name, is_spanish in installed if is_spanish), None)
    return spanish


def _legacy_speak(text: str) -> None:
    selected = _resolve_voice(FALLBACK_VOICE)
    command = ["say"]
    if selected:
        command.extend(["-v", selected])
    command.append(text)
    try:
        subprocess.run(command, check=False)
    except OSError:
        return


def speak(text: str, voice: str = DEFAULT_VOICE) -> None:
    """Synthesize neural speech with Edge-TTS, falling back to macOS ``say``."""
    if not text or len(text) > 500:
        raise ValueError("speech text must be between 1 and 500 characters")
    try:
        ALERT_AUDIO_PATH.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text, "--write-media", str(ALERT_AUDIO_PATH)],
            check=False,
            timeout=20,
        )
        if result.returncode == 0 and ALERT_AUDIO_PATH.exists() and ALERT_AUDIO_PATH.stat().st_size > 0:
            subprocess.run(["afplay", "/tmp/rof12_alert.mp3"], check=False)
            return
    except (OSError, subprocess.SubprocessError):
        pass
    _legacy_speak(text)


def speak_decision(
    decision: str,
    speaker: Callable[[str], None] = speak,
    codes: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Speak a contextual, fixed message associated with a Gate decision."""
    normalized = decision.upper()
    code_set = {str(code).upper() for code in (codes or ())}
    key = "DENY_ORDER_NOT_FOUND" if normalized == "DENY" and "ORDER_NOT_FOUND" in code_set else normalized
    message = DECISION_MESSAGES.get(key, DECISION_MESSAGES["DENY"])
    speaker(message)
    return message


def listen_text(*, timeout: float = 30.0, phrase_time_limit: float = 12.0) -> str:
    """Capture one microphone phrase, or raise a clear optional-dependency error."""
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError("SpeechRecognition no está instalado; usa --keyboard") from exc

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
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
    if not re.search(r"\b(reembols(?:a|ar)|devolver|procesar\s+reembolso)\b", lowered):
        raise ValueError("usa una acción como reembolsa, devolver o procesar reembolso")
    amount_match = re.search(
        r"(?<![\w.-])(?:(?:q|gtq|usd|eur)\s*|\$\s*)?([0-9]+(?:[.,][0-9]{1,2})?)(?![\w.])",
        lowered,
    )
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
        {"order_id": order_match.group(1).upper(), "amount": amount, "reason": text.strip()},
        text,
        tenant_id,
    )


def parse_command(text: str, **kwargs) -> VoiceProposal:
    """Public parser name used by terminal integrations."""
    return parse_proposal(text, **kwargs)


def approval_from_text(text: str) -> bool:
    """Return True only for an explicit approval word; everything else denies."""
    return text.strip().casefold() in {"autorizar", "autorizo", "aprobar", "apruebo", "sí", "si"}
