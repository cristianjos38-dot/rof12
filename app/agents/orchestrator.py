from dataclasses import dataclass

from app.agents.prompts import build_prompt
from app.domain.contracts import ToolRequest


@dataclass(frozen=True)
class ReadOnlyContext:
    tenant_id: str
    allowed_order_ids: tuple
    reconciled_facts: tuple = ()

    def as_prompt_context(self) -> dict:
        return {"tenant_id": self.tenant_id, "allowed_order_ids": self.allowed_order_ids, "reconciled_facts": self.reconciled_facts}


class WonderOrchestrator:
    def __init__(self, router):
        self.router = router

    def prompt(self, user_request: str, context: ReadOnlyContext, document_id: str = "none", document_text: str = "") -> str:
        return build_prompt(user_request, document_id, document_text)

    def propose(self, proposal: dict) -> ToolRequest:
        """The only output surface is the frozen, strict ToolRequest schema."""
        return ToolRequest.model_validate(proposal)
