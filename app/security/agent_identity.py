"""Server-side seam for mapping external agent identifiers to authority."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentBinding:
    agent_id: str
    user_id: str
    tenant_id: str
    capability_scope: frozenset[str]


def bind_agent(agent_id: str, user_id: str, tenant_id: str, capabilities: set[str]) -> AgentBinding:
    """Create validated metadata; tenant and capabilities remain server-owned."""
    if not agent_id or not user_id or not tenant_id or not capabilities:
        raise ValueError("agent binding requires identity, tenant and capabilities")
    return AgentBinding(agent_id, user_id, tenant_id, frozenset(capabilities))
