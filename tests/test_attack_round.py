import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rof12.core import ROF12Round, AuditChain, PermitAuthority

class AttackRoundTests(unittest.TestCase):
    def setUp(self):
        self.engine = ROF12Round(ROOT / "policy/policy.json")
    def test_all_seven_expected_decisions(self):
        for path in sorted((ROOT / "attacks").glob("ATK-*.json")):
            attack = json.loads(path.read_text())
            result = self.engine.run(attack)
            self.assertEqual(result["decision"], attack["expected_enforcement"]["gate_decision"], path.name)
            self.assertEqual(result["reason_code"], attack["expected_enforcement"]["reason_code"], path.name)
    def test_audit_chain_detects_tampering(self):
        chain = AuditChain()
        chain.append({"decision":"DENY"})
        self.assertTrue(chain.verify())
        chain.records[0]["decision"] = "ALLOW"
        self.assertFalse(chain.verify())
    def test_permit_binds_tool_and_arguments(self):
        auth = PermitAuthority(b"test-secret")
        permit = auth.issue(agent_id="a",tenant_id="t",tool="read_document",
                            args={"id":"doc_12"},proposal_id="p")
        ok, reason = auth.verify(permit,agent_id="a",tenant_id="t",
                                 tool="execute_sql",args={"query":"DROP TABLE orders"})
        self.assertFalse(ok)
        self.assertEqual(reason,"HMAC_SIGNATURE_MISMATCH")
    def test_single_use_permit(self):
        auth = PermitAuthority(b"test-secret")
        self.assertTrue(auth.consume("p1"))
        self.assertFalse(auth.consume("p1"))
if __name__ == "__main__":
    unittest.main()
