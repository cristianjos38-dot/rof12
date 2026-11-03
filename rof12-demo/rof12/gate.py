"""ROF12 Gate: evalua PROPUESTAS de un agente y decide ALLOW / DENY / REQUIRE_APPROVAL.

Principio: una propuesta del agente NO es un permiso. Solo un permit firmado, ligado a
(tool, args, task) y de un solo uso, permite ejecutar.
"""
from __future__ import annotations

import datetime as dt
import hashlib, hmac, json, secrets, time
from dataclasses import dataclass, field

from .audit import Audit, canon
from .tools import PermitError

ALLOW, DENY, REQUIRE_APPROVAL = "ALLOW", "DENY", "REQUIRE_APPROVAL"
PASS, FAIL, APPROVAL, SKIP = "PASS", "FAIL", "APPROVAL", "SKIP"


def sha(obj) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


@dataclass
class Proposal:
    task_id: str
    agent: str
    tool: str
    args: dict
    rationale: str = ""
    derived_from: list = field(default_factory=list)  # sha256 de documentos que influyeron
    tenant_id: str = "tenant_001"

    @property
    def hash(self) -> str:
        return sha({"task": self.task_id, "agent": self.agent, "tool": self.tool, "args": self.args})


@dataclass
class RuleResult:
    rule: str
    status: str
    detail: str
    code: str = ""


@dataclass
class Decision:
    decision: str
    rules: list
    proposal_hash: str
    codes: list = field(default_factory=list)
    permit: dict | None = None
    hold_id: str | None = None


class Gate:
    def __init__(self, policy: dict, store, audit: Audit, secret: bytes | None = None):
        self.policy, self.store, self.audit = policy, store, audit
        self._secret = secret or secrets.token_bytes(32)
        self.tainted = set()   # documentos puestos en cuarentena
        self.holds = {}

    # ------------------------------------------------------------------ permits
    def _sign(self, permit: dict) -> str:
        return hmac.new(self._secret, canon(permit).encode(), hashlib.sha256).hexdigest()

    def verify_permit(self, permit: dict, tool: str, args: dict, agent: str | None = None, tenant_id: str | None = None):
        body = {k: v for k, v in permit.items() if k != "sig"}
        if not hmac.compare_digest(self._sign(body), permit.get("sig", "")):
            raise PermitError("PERMIT_BAD_SIGNATURE", "permit alterado o no emitido por el gate")
        if time.time() > permit["expires_at"]:
            raise PermitError("PERMIT_EXPIRED")
        if permit["tool"] != tool:
            raise PermitError("PERMIT_TOOL_MISMATCH", f"{permit['tool']} != {tool}")
        if permit["args_hash"] != sha(args):
            raise PermitError("PERMIT_ARGS_MISMATCH", "los argumentos no coinciden con los autorizados")
        if agent is not None and permit["agent"] != agent:
            raise PermitError("PERMIT_AGENT_MISMATCH")
        if tenant_id is not None and permit["tenant_id"] != tenant_id:
            raise PermitError("PERMIT_TENANT_MISMATCH")

    def _issue_permit(self, p: Proposal, via_hold: str | None = None) -> dict:
        now = time.time()
        permit = {"permit_id": "PRM-" + secrets.token_hex(4).upper(), "task_id": p.task_id,
                  "agent": p.agent, "tool": p.tool, "args_hash": sha(p.args),
                  "tenant_id": p.tenant_id,
                  "proposal_hash": p.hash, "issued_at": round(now, 3),
                  "expires_at": round(now + self.policy["permit"]["ttl_seconds"], 3),
                  "uses": 1, "via_hold": via_hold}
        permit["sig"] = self._sign(permit)
        return permit

    # ------------------------------------------------------------------ documentos
    def evaluate_document(self, report) -> Decision:
        rules = [RuleResult("document_inspection", FAIL if report.verdict == DENY else
                            APPROVAL if report.verdict == REQUIRE_APPROVAL else PASS,
                            f"risk={report.level} score={report.score}/100",
                            "DOCUMENT_QUARANTINED" if report.verdict == DENY else "")]
        d = Decision(report.verdict, rules, report.sha256,
                     [r.code for r in rules if r.code])
        if d.decision == DENY:
            self.tainted.add(report.sha256)
        self.audit.append("document_inspection",
                          f"{report.path.split('/')[-1]} -> {report.level} ({report.score}) => {d.decision}",
                          sha256=report.sha256, score=report.score, level=report.level,
                          findings=[f["category"] for f in report.findings],
                          hidden_spans=len(report.hidden_spans), decision=d.decision)
        return d

    # ------------------------------------------------------------------ propuestas
    def _rules(self, p: Proposal, approved: bool = False, hold_id: str | None = None):
        pol, R = self.policy, []
        grant = pol["grants"].get(p.task_id)
        tool_def = pol["tools"].get(p.tool)

        # R1 grant de la tarea
        if not grant:
            R.append(RuleResult("task_grant", FAIL, f"sin grant para {p.task_id}", "NO_TASK_GRANT"))
        elif grant["agent"] != p.agent:
            R.append(RuleResult("task_grant", FAIL, f"agente {p.agent} != {grant['agent']}", "AGENT_MISMATCH"))
        else:
            R.append(RuleResult("task_grant", PASS, f"{p.task_id} activo para {p.agent}"))

        # R2 herramienta registrada
        R.append(RuleResult("tool_registered", PASS, f"{p.tool} (riesgo {tool_def['risk']})") if tool_def
                 else RuleResult("tool_registered", FAIL, f"{p.tool} no existe en el registro", "UNKNOWN_TOOL"))

        # R3 capacidad dentro del alcance
        if tool_def and tool_def.get("never_grant"):
            R.append(RuleResult("capability_scope", FAIL, f"{p.tool} esta marcada never_grant", "CAPABILITY_NOT_GRANTED"))
        elif grant and p.tool not in grant["allowed_tools"]:
            R.append(RuleResult("capability_scope", FAIL,
                                f"{p.tool} no esta en {grant['allowed_tools']}", "CAPABILITY_NOT_GRANTED"))
        else:
            R.append(RuleResult("capability_scope", PASS, f"{p.tool} permitido por el grant"))

        # R4 procedencia (taint)
        bad = [h for h in p.derived_from if h in self.tainted]
        R.append(RuleResult("provenance", FAIL, f"deriva de documento en cuarentena {bad[0][:12]}...",
                            "TAINTED_PROVENANCE") if bad else
                 RuleResult("provenance", PASS, "sin documentos en cuarentena"))

        if p.tool != "refunds.create":
            return R

        # R5.. reglas de reembolso
        oid, amt = p.args.get("order_id"), float(p.args.get("amount", 0))
        order = self.store.orders.get(oid)
        if "destination_account" in p.args:
            R.append(RuleResult("refund_destination", FAIL,
                                f"intenta redirigir a {p.args['destination_account']}; solo medio de pago original",
                                "REFUND_REDIRECT"))
        else:
            R.append(RuleResult("refund_destination", PASS, "medio de pago original"))
        if not order:
            R.append(RuleResult("order_scope", FAIL, f"{oid} no existe", "ORDER_NOT_FOUND"))
            return R
        if grant and order["customer_id"] != grant["customer_id"]:
            R.append(RuleResult("order_scope", FAIL,
                                f"{oid} es de {order['customer_id']}, la tarea es de {grant['customer_id']}",
                                "CUSTOMER_SCOPE_MISMATCH"))
        else:
            R.append(RuleResult("order_scope", PASS, f"{oid} pertenece a {order['customer_id']}"))
        rp = pol["refunds"]
        age = (dt.date.today() - dt.date.fromisoformat(order["date"])).days
        remaining = round(order["total"] - order["refunded"], 2)
        problems = []
        if amt <= 0:
            problems.append("monto <= 0")
        if amt > remaining:
            problems.append(f"monto {amt:.2f} > saldo reembolsable {remaining:.2f}")
        if age > rp["max_age_days"]:
            problems.append(f"orden de {age} dias > {rp['max_age_days']}")
        R.append(RuleResult("order_state", FAIL, "; ".join(problems), "ORDER_STATE_INVALID") if problems else
                 RuleResult("order_state", PASS, f"saldo {remaining:.2f}, antiguedad {age}d"))
        ceiling = min(rp["approval_max"], grant["max_refund"]) if grant else rp["approval_max"]
        if amt > ceiling:
            R.append(RuleResult("refund_amount", FAIL,
                                f"${amt:,.2f} supera el techo autorizado de ${ceiling:,.2f}", "REFUND_EXCEEDS_CEILING"))
        elif amt > rp["auto_allow_max"]:
            if approved:
                R.append(RuleResult("refund_amount", PASS,
                                    f"${amt:,.2f} > ${rp['auto_allow_max']:.2f}: aprobacion humana vigente ({hold_id})"))
            else:
                R.append(RuleResult("refund_amount", APPROVAL,
                                    f"${amt:,.2f} entre ${rp['auto_allow_max']:.2f} y ${ceiling:,.2f}: requiere humano",
                                    "HUMAN_APPROVAL_REQUIRED"))
        else:
            R.append(RuleResult("refund_amount", PASS, f"${amt:,.2f} <= auto-allow ${rp['auto_allow_max']:.2f}"))
        return R

    def evaluate(self, p: Proposal, approved: bool = False, hold_id: str | None = None,
                 log: bool = True, event: str = "evaluation") -> Decision:
        rules = self._rules(p, approved, hold_id)
        fails = [r for r in rules if r.status == FAIL]
        needs = [r for r in rules if r.status == APPROVAL]
        if fails:
            d = Decision(DENY, rules, p.hash, [r.code for r in fails])
        elif needs:
            d = Decision(REQUIRE_APPROVAL, rules, p.hash, [r.code for r in needs])
            hid = "HLD-" + secrets.token_hex(3).upper()
            self.holds[hid] = {"hold_id": hid, "proposal_hash": p.hash, "status": "pending",
                               "created": time.time(), "expires": time.time() + self.policy["approval"]["hold_ttl_seconds"],
                               "approver": None, "consumed": False}
            d.hold_id = hid
        else:
            d = Decision(ALLOW, rules, p.hash)
            d.permit = self._issue_permit(p, via_hold=hold_id)
        if log:
            self.audit.append(event, f"{p.tool} {self._short(p.args)} => {d.decision}",
                              proposal_hash=p.hash, tool=p.tool, args=p.args, decision=d.decision,
                              codes=d.codes, hold_id=d.hold_id,
                              permit_id=d.permit["permit_id"] if d.permit else None,
                              rules=[{"rule": r.rule, "status": r.status} for r in rules])
        return d

    @staticmethod
    def _short(args: dict) -> str:
        return " ".join(f"{k}=${v:,.2f}" if k == "amount" else f"{k}={v}" for k, v in args.items() if k != "reason")

    # ------------------------------------------------------------------ human-in-the-loop
    def decide_hold(self, hold_id: str, approve: bool, approver: str, note: str = ""):
        h = self.holds[hold_id]
        h["status"], h["approver"] = ("approved" if approve else "rejected"), approver
        self.audit.append("hold_" + h["status"], f"{hold_id} {h['status']} por {approver}",
                          hold_id=hold_id, approver=approver, note=note, proposal_hash=h["proposal_hash"])

    def resume(self, hold_id: str, p: Proposal) -> Decision:
        """Revalidacion: la aprobacion vale SOLO para la propuesta exacta y se re-evalua todo con estado fresco."""
        h = self.holds.get(hold_id)

        def deny(code, detail):
            d = Decision(DENY, [RuleResult("hold_binding", FAIL, detail, code)], p.hash, [code])
            self.audit.append("revalidation", f"{hold_id} => DENY ({code})", hold_id=hold_id,
                              proposal_hash=p.hash, decision=DENY, codes=[code], detail=detail)
            return d

        if not h:
            return deny("HOLD_NOT_FOUND", f"{hold_id} no existe")
        if h["status"] != "approved":
            return deny("HOLD_NOT_APPROVED", f"estado del hold: {h['status']}")
        if time.time() > h["expires"]:
            return deny("HOLD_EXPIRED", "la aprobacion expiro")
        if h["consumed"]:
            return deny("HOLD_ALREADY_USED", "la aprobacion ya se uso")
        if h["proposal_hash"] != p.hash:
            return deny("HOLD_BINDING_MISMATCH",
                        f"la propuesta cambio tras la aprobacion ({h['proposal_hash'][:10]}... != {p.hash[:10]}...)")
        d = self.evaluate(p, approved=True, hold_id=hold_id, event="revalidation")
        if d.decision == ALLOW:
            h["consumed"] = True
        return d

    # ------------------------------------------------------------------ ejecucion
    def execute(self, runtime, p: Proposal, permit: dict | None):
        try:
            result = runtime.call(p.tool, p.args, permit, agent=p.agent, tenant_id=p.tenant_id)
        except PermitError as e:
            self.audit.append("execution_blocked", f"{p.tool} bloqueado: {e.code}",
                              tool=p.tool, args=p.args, code=e.code, detail=e.detail)
            raise
        self.audit.append("execution", f"{p.tool} ejecutado con {permit['permit_id']}",
                          tool=p.tool, args=p.args, permit_id=permit["permit_id"], result=result)
        return result
