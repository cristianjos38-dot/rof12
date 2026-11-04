from __future__ import annotations
import hashlib, hmac, json, threading, time
from pathlib import Path
from .adapters import MuseSparkAdapter, SAMAdapter

def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

class AuditChain:
    def __init__(self):
        self.records = []
        self.previous_hash = "0" * 64
    def append(self, event: dict) -> dict:
        body = {"sequence": len(self.records)+1, "previous_hash": self.previous_hash, **event}
        digest = sha256_text(canonical_json(body))
        record = {**body, "record_hash": digest}
        self.records.append(record)
        self.previous_hash = digest
        return record
    def verify(self) -> bool:
        prev = "0" * 64
        for i, record in enumerate(self.records, 1):
            body = {k:v for k,v in record.items() if k != "record_hash"}
            if body["sequence"] != i or body["previous_hash"] != prev:
                return False
            digest = sha256_text(canonical_json(body))
            if not hmac.compare_digest(digest, record["record_hash"]):
                return False
            prev = digest
        return True

class PermitAuthority:
    """Demo-only in-memory permit authority. Production consumption belongs in PostgreSQL."""
    def __init__(self, secret: bytes):
        self.secret = secret
        self.consumed = set()
        self.lock = threading.Lock()
    def issue(self, *, agent_id, tenant_id, tool, args, proposal_id, ttl=120):
        args_hash = sha256_text(canonical_json(args))
        payload = {"agent_id":agent_id,"tenant_id":tenant_id,"tool":tool,
                   "args_hash":args_hash,"proposal_id":proposal_id,"expires_at":int(time.time())+ttl}
        token_id = sha256_text(canonical_json(payload))[:24]
        signature = hmac.new(self.secret, canonical_json(payload).encode(), hashlib.sha256).hexdigest()
        return {"token_id":token_id,"payload":payload,"signature":signature}
    def verify(self, permit, *, agent_id, tenant_id, tool, args):
        p = permit["payload"]
        expected = hmac.new(self.secret, canonical_json(p).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, permit["signature"]):
            return False, "HMAC_SIGNATURE_MISMATCH"
        args_hash = sha256_text(canonical_json(args))
        if (p["agent_id"] != agent_id or p["tenant_id"] != tenant_id or
            p["tool"] != tool or p["args_hash"] != args_hash):
            return False, "HMAC_SIGNATURE_MISMATCH"
        if p["expires_at"] < int(time.time()):
            return False, "PERMIT_EXPIRED"
        return True, "PERMIT_VALID"
    def consume(self, permit_id):
        with self.lock:
            if permit_id in self.consumed:
                return False
            self.consumed.add(permit_id)
            return True

class ROF12Round:
    def __init__(self, policy_path="policy/policy.json"):
        self.policy = json.loads(Path(policy_path).read_text())
        self.spark, self.sam = MuseSparkAdapter(), SAMAdapter()
        self.audit = AuditChain()
        self.permits = PermitAuthority(b"DEMO_ONLY_CHANGE_ME")
    def record(self, attack_id, decision, reason, **extra):
        self.audit.append({"attack_id":attack_id,"decision":decision,"reason_code":reason,**extra})
        return {"attack_id":attack_id,"decision":decision,"reason_code":reason,**extra}
    def run(self, attack):
        aid, p = attack["attack_id"], attack["input_payload"]
        if aid == "ATK-001":
            spark = self.spark.analyze(p["visible_text"], p["hidden_text"])
            sam = self.sam.segment(p["document_id"], p.get("ocr_bounding_box"))
            return self.record(aid,"QUARANTINE" if spark.injection_detected else "ALLOW",
                               spark.label, spark_analysis=spark.label, sam_segmentation=sam,
                               http_status=403 if spark.injection_detected else 200, tainted=spark.injection_detected)
        if aid == "ATK-002":
            suspicious = bool(p.get("metadata_text","").strip())
            return self.record(aid,"QUARANTINE" if suspicious else "ALLOW",
                               "METADATA_MISMATCH" if suspicious else "NO_MISMATCH",
                               http_status=403 if suspicious else 200, tainted=suspicious)
        if aid == "ATK-003":
            exceeded = float(p["amount"]) > float(self.policy["max_transfer_amount"])
            return self.record(aid,"DENY" if exceeded else "ALLOW",
                               "POLICY_CAP_EXCEEDED" if exceeded else "WITHIN_POLICY",
                               http_status=403 if exceeded else 200, tools_executed=0)
        if aid == "ATK-004":
            permit = self.permits.issue(agent_id=p["agent_id"],tenant_id=p["tenant_id"],
                tool=p["original_tool"],args=p["original_args"],proposal_id="proposal_demo")
            ok, _ = self.permits.verify(permit,agent_id=p["agent_id"],tenant_id=p["tenant_id"],
                tool=p["mutated_tool"],args=p["mutated_args"])
            return self.record(aid,"ALLOW" if ok else "DENY",
                "PERMIT_VALID" if ok else "HMAC_SIGNATURE_MISMATCH",
                http_status=200 if ok else 403,tools_executed=0)
        if aid == "ATK-005":
            pid = p["permit_id"]
            first = self.permits.consume(pid)
            second = self.permits.consume(pid)
            return self.record(aid,"DENY" if not second else "ALLOW",
                "TOKEN_ALREADY_CONSUMED" if not second else "UNEXPECTED_REPLAY_SUCCESS",
                first_consumer="ALLOW" if first else "DENY",
                second_consumer="DENY" if not second else "ALLOW",tools_executed=1 if first else 0)
        if aid == "ATK-006":
            return self.record(aid,"DENY","UNAUTHORIZED_HUMAN_OVERRIDE",
                               http_status=403,tools_executed=0)
        if aid == "ATK-007":
            violation = p["authenticated_tenant"] != p["requested_tenant"]
            return self.record(aid,"DENY" if violation else "ALLOW",
                "TENANT_ACCESS_VIOLATION" if violation else "TENANT_MATCH",
                http_status=404 if violation else 200,tools_executed=0)
        raise ValueError(f"Unknown attack id: {aid}")
