import json, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import make_assets
from rof12.audit import Audit
from rof12.gate import ALLOW, DENY, REQUIRE_APPROVAL, Gate, Proposal
from rof12.inspector import inspect_pdf
from rof12.tools import PermitError, Store, ToolRuntime

with open(os.path.join(ROOT, "policy", "policy.json"), encoding="utf-8") as policy_file:
    POLICY = json.load(policy_file)
TH = POLICY["document_risk"]


def refund(order, amount, **extra):
    return Proposal("TKT-1042", "support-agent-01", "refunds.create",
                    {"order_id": order, "amount": amount, **extra})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdfs = make_assets.main(self.tmp.name)
        self.store = Store()
        self.audit = Audit(os.path.join(self.tmp.name, "audit.jsonl"))
        self.gate = Gate(POLICY, self.store, self.audit)
        self.rt = ToolRuntime(self.store, self.gate.verify_permit)

    def tearDown(self):
        self.tmp.cleanup()


class TestInspector(Base):
    def test_hidden_pdf_is_critical_and_denied(self):
        r = inspect_pdf(self.pdfs["hidden"], TH)
        self.assertEqual((r.level, r.verdict), ("CRITICAL", DENY))
        techniques = {f for s in r.hidden_spans for f in s.flags}
        self.assertTrue({"white_text", "micro_font", "invisible_render_mode", "off_page"} <= techniques)
        self.assertTrue(r.metadata_hits)

    def test_clean_pdf_not_blocked_even_with_white_title_on_blue_band(self):
        r = inspect_pdf(self.pdfs["clean"], TH)
        self.assertEqual((r.level, r.verdict), ("LOW", ALLOW))
        self.assertEqual(r.hidden_spans, [])

    def test_visible_layer_identical_in_both(self):
        a, b = (inspect_pdf(self.pdfs[k], TH) for k in ("clean", "hidden"))
        self.assertEqual(a.visible_text, b.visible_text)


class TestGate(Base):
    def test_over_ceiling_is_denied_and_cannot_execute(self):
        p = refund("ORD-9001", 1850.0)
        d = self.gate.evaluate(p)
        self.assertEqual(d.decision, DENY)
        self.assertIn("REFUND_EXCEEDS_CEILING", d.codes)
        with self.assertRaises(PermitError) as e:
            self.gate.execute(self.rt, p, d.permit)
        self.assertEqual(e.exception.code, "NO_PERMIT")
        self.assertEqual(self.store.refunds, [])

    def test_invalid_capability_denied(self):
        d = self.gate.evaluate(Proposal("TKT-1042", "support-agent-01", "db.export_customers", {"destination": "x@y.z"}))
        self.assertEqual(d.decision, DENY)
        self.assertIn("CAPABILITY_NOT_GRANTED", d.codes)

    def test_other_customer_denied(self):
        d = self.gate.evaluate(refund("ORD-5555", 60.0))
        self.assertIn("CUSTOMER_SCOPE_MISMATCH", d.codes)

    def test_allow_executes_once_only(self):
        p = refund("ORD-7731", 45.0)
        d = self.gate.evaluate(p)
        self.assertEqual(d.decision, ALLOW)
        self.gate.execute(self.rt, p, d.permit)
        self.assertEqual(len(self.store.refunds), 1)
        with self.assertRaises(PermitError) as e:
            self.gate.execute(self.rt, p, d.permit)
        self.assertEqual(e.exception.code, "PERMIT_ALREADY_USED")

    def test_permit_bound_to_args_and_signature(self):
        p = refund("ORD-7731", 45.0)
        d = self.gate.evaluate(p)
        with self.assertRaises(PermitError) as e:
            self.rt.call(p.tool, {**p.args, "amount": 99.0}, d.permit)
        self.assertEqual(e.exception.code, "PERMIT_ARGS_MISMATCH")
        forged = dict(d.permit, uses=5)
        with self.assertRaises(PermitError) as e:
            self.rt.call(p.tool, p.args, forged)
        self.assertEqual(e.exception.code, "PERMIT_BAD_SIGNATURE")

    def test_hold_flow_with_tamper_and_revalidation(self):
        p = refund("ORD-7788", 320.0)
        d = self.gate.evaluate(p)
        self.assertEqual(d.decision, REQUIRE_APPROVAL)
        self.assertEqual(self.gate.resume(d.hold_id, p).codes, ["HOLD_NOT_APPROVED"])
        self.gate.decide_hold(d.hold_id, True, "tester")
        self.assertEqual(self.gate.resume(d.hold_id, refund("ORD-7788", 480.0)).codes, ["HOLD_BINDING_MISMATCH"])
        ok = self.gate.resume(d.hold_id, p)
        self.assertEqual(ok.decision, ALLOW)
        self.gate.execute(self.rt, p, ok.permit)
        self.assertEqual(self.gate.resume(d.hold_id, p).codes, ["HOLD_ALREADY_USED"])

    def test_revalidation_catches_changed_state(self):
        p = refund("ORD-7788", 320.0)
        d = self.gate.evaluate(p)
        self.gate.decide_hold(d.hold_id, True, "tester")
        self.store.orders["ORD-7788"]["refunded"] = 100.0   # alguien reembolso antes
        r = self.gate.resume(d.hold_id, p)
        self.assertEqual(r.decision, DENY)
        self.assertIn("ORDER_STATE_INVALID", r.codes)

    def test_tainted_provenance_denied(self):
        rep = inspect_pdf(self.pdfs["hidden"], TH)
        self.gate.evaluate_document(rep)
        p = Proposal("TKT-1042", "support-agent-01", "refunds.create",
                     {"order_id": "ORD-7731", "amount": 10.0}, derived_from=[rep.sha256])
        self.assertIn("TAINTED_PROVENANCE", self.gate.evaluate(p).codes)


class TestAudit(Base):
    def test_chain_valid_then_tamper_detected(self):
        self.gate.evaluate(refund("ORD-7731", 45.0))
        self.gate.evaluate(refund("ORD-9001", 1850.0))
        self.assertTrue(Audit.verify(self.audit.path)[0])
        with open(self.audit.path, encoding="utf-8") as audit_file:
            lines = audit_file.read().splitlines()
        rec = json.loads(lines[0]); rec["summary"] = "otra cosa"
        lines[0] = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with open(self.audit.path, "w", encoding="utf-8") as audit_file:
            audit_file.write("\n".join(lines) + "\n")
        self.assertFalse(Audit.verify(self.audit.path)[0])


if __name__ == "__main__":
    unittest.main()
