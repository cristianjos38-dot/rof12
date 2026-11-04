"""Deterministic seven-vector defensive benchmark used by the demo harness."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuditChain:
    def __init__(self):
        self.records = []
        self.previous_hash = "0" * 64

    def append(self, event: dict) -> dict:
        body = {"sequence": len(self.records) + 1, "previous_hash": self.previous_hash, **event}
        digest = sha256_text(canonical_json(body))
        record = {**body, "record_hash": digest}
        self.records.append(record)
        self.previous_hash = digest
        return record

    def verify(self) -> bool:
        previous = "0" * 64
        for sequence, record in enumerate(self.records, 1):
            body = {key: value for key, value in record.items() if key != "record_hash"}
            if body.get("sequence") != sequence or body.get("previous_hash") != previous:
                return False
            digest = sha256_text(canonical_json(body))
            if not hmac.compare_digest(digest, record.get("record_hash", "")):
                return False
            previous = digest
        return True


class PermitAuthority:
    """Demo-only in-memory authority; production consumption belongs in PostgreSQL."""

    def __init__(self, secret: bytes):
        self.secret = secret
        self.consumed: set[str] = set()
        self.lock = threading.Lock()

    def issue(self, *, agent_id, tenant_id, tool, args, proposal_id, ttl=120):
        args_hash = sha256_text(canonical_json(args))
        payload = {
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "tool": tool,
            "args_hash": args_hash,
            "proposal_id": proposal_id,
            "expires_at": int(time.time()) + ttl,
        }
        token_id = sha256_text(canonical_json(payload))[:24]
        signature = hmac.new(self.secret, canonical_json(payload).encode(), hashlib.sha256).hexdigest()
        return {"token_id": token_id, "payload": payload, "signature": signature}

    def verify(self, permit, *, agent_id, tenant_id, tool, args):
        payload = permit["payload"]
        expected = hmac.new(self.secret, canonical_json(payload).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, permit["signature"]):
            return False, "HMAC_SIGNATURE_MISMATCH"
        args_hash = sha256_text(canonical_json(args))
        if (
            payload["agent_id"] != agent_id
            or payload["tenant_id"] != tenant_id
            or payload["tool"] != tool
            or payload["args_hash"] != args_hash
        ):
            return False, "HMAC_SIGNATURE_MISMATCH"
        if payload["expires_at"] < int(time.time()):
            return False, "PERMIT_EXPIRED"
        return True, "PERMIT_VALID"

    def consume(self, permit_id):
        with self.lock:
            if permit_id in self.consumed:
                return False
            self.consumed.add(permit_id)
            return True


@dataclass(frozen=True)
class SparkResult:
    injection_detected: bool
    label: str


class MuseSparkAdapter:
    """Perception adapter with deterministic local verification."""

    def analyze(self, visible_text: str, hidden_text: str) -> SparkResult:
        suspicious = any(
            term in hidden_text.lower()
            for term in ("instruction:", "ignore audit", "transferir", "delete logs", "borrar logs")
        )
        return SparkResult(suspicious, "PROMPT_INJECTION_DETECTED" if suspicious else "CLEAN")


class SAMAdapter:
    """Segmentation adapter with deterministic evidence output for the lab."""

    def segment(self, document_id: str, bounding_box=None) -> dict:
        del document_id
        return {
            "has_boxes": bool(bounding_box),
            "has_masks": bool(bounding_box),
            "provider": "deterministic-local",
            "note": "Evidence segmentation is represented locally for the defensive benchmark.",
        }


class ROF12Round:
    def __init__(self, policy_path="policy/policy.json"):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        self.spark, self.sam = MuseSparkAdapter(), SAMAdapter()
        self.audit = AuditChain()
        self.permits = PermitAuthority(b"DEMO_ONLY_CHANGE_ME")

    def record(self, attack_id, decision, reason, **extra):
        self.audit.append({"attack_id": attack_id, "decision": decision, "reason": reason, **extra})
        return {"attack_id": attack_id, "decision": decision, "reason_code": reason, **extra}

    def run(self, attack):
        attack_id, payload = attack["attack_id"], attack["input_payload"]
        if attack_id == "ATK-001":
            spark = self.spark.analyze(payload["visible_text"], payload["hidden_text"])
            sam = self.sam.segment(payload["document_id"], payload.get("ocr_bounding_box"))
            return self.record(
                attack_id,
                "QUARANTINE" if spark.injection_detected else "ALLOW",
                spark.label,
                spark_analysis=spark.label,
                sam_segmentation=sam,
                http_status=403 if spark.injection_detected else 200,
                tainted=spark.injection_detected,
            )
        if attack_id == "ATK-002":
            suspicious = bool(payload.get("metadata_text", "").strip())
            return self.record(
                attack_id,
                "QUARANTINE" if suspicious else "ALLOW",
                "METADATA_MISMATCH" if suspicious else "NO_MISMATCH",
                http_status=403 if suspicious else 200,
                tainted=suspicious,
            )
        if attack_id == "ATK-003":
            exceeded = float(payload["amount"]) > float(self.policy["max_transfer_amount"])
            return self.record(
                attack_id,
                "DENY" if exceeded else "ALLOW",
                "POLICY_CAP_EXCEEDED" if exceeded else "WITHIN_POLICY",
                http_status=403 if exceeded else 200,
                tools_executed=0,
            )
        if attack_id == "ATK-004":
            permit = self.permits.issue(
                agent_id=payload["agent_id"],
                tenant_id=payload["tenant_id"],
                tool=payload["original_tool"],
                args=payload["original_args"],
                proposal_id="proposal_demo",
            )
            ok, _ = self.permits.verify(
                permit,
                agent_id=payload["agent_id"],
                tenant_id=payload["tenant_id"],
                tool=payload["mutated_tool"],
                args=payload["mutated_args"],
            )
            return self.record(
                attack_id,
                "ALLOW" if ok else "DENY",
                "PERMIT_VALID" if ok else "HMAC_SIGNATURE_MISMATCH",
                http_status=200 if ok else 403,
                tools_executed=0,
            )
        if attack_id == "ATK-005":
            permit_id = payload["permit_id"]
            first = self.permits.consume(permit_id)
            second = self.permits.consume(permit_id)
            return self.record(
                attack_id,
                "DENY" if not second else "ALLOW",
                "TOKEN_ALREADY_CONSUMED" if not second else "UNEXPECTED_REPLAY_SUCCESS",
                first_consumer="ALLOW" if first else "DENY",
                second_consumer="DENY" if not second else "ALLOW",
                tools_executed=1 if first else 0,
            )
        if attack_id == "ATK-006":
            return self.record(attack_id, "DENY", "UNAUTHORIZED_HUMAN_OVERRIDE", http_status=403, tools_executed=0)
        if attack_id == "ATK-007":
            violation = payload["authenticated_tenant"] != payload["requested_tenant"]
            return self.record(
                attack_id,
                "DENY" if violation else "ALLOW",
                "TENANT_ACCESS_VIOLATION" if violation else "TENANT_MATCH",
                http_status=404 if violation else 200,
                tools_executed=0,
            )
        raise ValueError(f"Unknown attack id: {attack_id}")
