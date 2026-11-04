"""Small public SDK facade with default-deny tool protection.

This facade is intentionally independent from the refund demo.  It gives
third-party integrations a safe starting point while preserving the rule that
proposals are not execution authority until the gate emits a bound permit.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Mapping


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Proposal:
    tool_name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class GateExecutionPermit:
    tool_name: str
    args_hash: str
    signature: str


@dataclass(frozen=True)
class GateDecision:
    decision: str
    reason: str
    permit: GateExecutionPermit | None = None


class SecurityGate:
    """Allow only explicitly listed tools and bind permits to exact arguments."""

    def __init__(self, allowed_tools: set[str] | frozenset[str] = frozenset()):
        self._allowed_tools = frozenset(allowed_tools)
        self._secret = secrets.token_bytes(32)
        self._used: set[str] = set()

    def evaluate(self, proposal: Proposal) -> GateDecision:
        if proposal.tool_name not in self._allowed_tools:
            return GateDecision("DENY", "tool_not_authorized")
        args_hash = _digest(proposal.arguments)
        body = f"{proposal.tool_name}:{args_hash}".encode()
        signature = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return GateDecision("ALLOW", "explicit_policy_match", GateExecutionPermit(proposal.tool_name, args_hash, signature))

    def execute(self, proposal: Proposal, function: Callable[..., Any]) -> Any:
        decision = self.evaluate(proposal)
        if decision.decision != "ALLOW" or decision.permit is None:
            raise PermissionError(decision.reason)
        permit = decision.permit
        if permit.signature in self._used:
            raise PermissionError("permit_already_used")
        expected = hmac.new(self._secret, f"{permit.tool_name}:{permit.args_hash}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, permit.signature) or _digest(proposal.arguments) != permit.args_hash:
            raise PermissionError("permit_binding_mismatch")
        self._used.add(permit.signature)
        return function(**dict(proposal.arguments))


def protect(gate: SecurityGate, tool_name: str):
    """Decorate a function so every call is evaluated by a SecurityGate."""
    def decorator(function):
        @wraps(function)
        def guarded(**arguments):
            return gate.execute(Proposal(tool_name, arguments), function)
        return guarded
    return decorator
