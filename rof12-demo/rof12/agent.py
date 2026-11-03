"""Agente SIMULADO y determinista (stand-in de un LLM) para que la demo sea reproducible.

`NaiveAgent` hace lo que haria un agente sin defensas: obedece cualquier instruccion que
encuentre en el texto extraido del documento. Para conectar un modelo real (p. ej. Meta Model API)
basta con reemplazar `propose_from_document` / `propose` por una llamada al modelo que devuelva
objetos `Proposal`; el Gate no cambia.
"""
from __future__ import annotations

import re

from .gate import Proposal
from .meta_client import MetaClient


class NaiveAgent:
    name = "support-agent-01"

    def __init__(self, task_id: str):
        self.task_id = task_id

    def propose(self, tool: str, args: dict, rationale: str = "", derived_from=None) -> Proposal:
        return Proposal(self.task_id, self.name, tool, args, rationale, list(derived_from or []))

    def propose_from_document(self, text: str, doc_sha: str) -> list:
        props = []
        m = re.search(r"refund of \$([\d,\.]+) to account (\S+?)[\s,.]*for order (ORD-\d+)", text, re.I)
        if m:
            props.append(self.propose(
                "refunds.create",
                {"order_id": m.group(3), "amount": float(m.group(1).replace(",", "")),
                 "destination_account": m.group(2).rstrip("."), "reason": "instruccion encontrada en el documento"},
                "El documento indica emitir este reembolso", [doc_sha]))
        m = re.search(r"export the full customer database and email it to (\S+?)\.?(\s|$)", text, re.I)
        if m:
            props.append(self.propose("db.export_customers", {"destination": m.group(1).rstrip(".")},
                                      "El documento indica exportar la base de clientes", [doc_sha]))
        return props


class MetaAgent(NaiveAgent):
    """Wonder-backed planner whose output is still only a Gate proposal."""

    def __init__(self, task_id: str, client: MetaClient | None = None):
        super().__init__(task_id)
        self.client = client or MetaClient()

    def propose_from_document(self, text: str, doc_sha: str) -> list:
        result = self.client.call_muse_wonder("Return a proposal only; never execute tools.", [{"role": "user", "content": text}])
        proposal = result.proposal
        if proposal.get("tool") and proposal.get("args"):
            return [self.propose(proposal["tool"], proposal["args"], result.plan, [doc_sha])]
        return super().propose_from_document(text, doc_sha)
