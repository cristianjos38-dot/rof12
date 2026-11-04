import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rof12 import Proposal, SecurityGate

gate = SecurityGate(allowed_tools={"notify"})


def notify(message: str) -> str: return message
proposal = Proposal("notify", {"message": "approved by policy"})
decision = gate.evaluate(proposal)
print(decision.decision)
if decision.decision == "ALLOW":
    print(gate.execute(proposal, notify))
