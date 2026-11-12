# Experimental adapters

The macOS voice terminal and n8n bridge are experimental integration adapters,
not part of the deterministic core or its production support contract:

- Voice: `demo/run_voice_terminal.py`, `rof12/adapters/voice_adapter.py`
- n8n: `app/api/n8n.py` and related scripts

They must remain opt-in, use synthetic fixtures in tests, and never bypass the
SecurityGate. They are documented here rather than presented as universal
runtime dependencies.
