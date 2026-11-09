# ROF12 agent identity seam

ROF12 accepts an optional `agent_id` JWT claim as an identifier for an external
agent, including a future Microsoft Entra Agent ID integration. It is not a
tenant, role, or capability claim. The server resolves `sub`, tenant, active
membership, role, and capability scope from its own authority store. A binding
is represented by `app.security.agent_identity.AgentBinding` and must match the
authenticated user and tenant before any policy evaluation.

This repository does not implement Entra or validate Entra keys. Provider
federation and JWKS configuration remain deployment responsibilities.
