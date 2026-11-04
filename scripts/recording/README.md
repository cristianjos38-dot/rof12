# ROF12 recording orchestration

These helpers only control the visible macOS UI and recording process. They do
not implement or modify SecurityGate, policy, permissions, audit logic, or
document processing.

Before recording, use synthetic fixtures only and label any simulated
question/answer as **SIMULATED** in the spoken script. The repository does not
contain a Gmail account, a real n8n workflow export, or a webhook URL; those
must be supplied by the operator without placing credentials in this tree.

```bash
# 1. Start the local deterministic runtime.
MODEL_MODE=mock uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. In another Terminal, verify the API and run the exact seven-vector demo.
curl -fsS http://127.0.0.1:8000/health/ready
python3.11 demo/run_video_demo.py --no-speech

# 3. Focus existing windows; URLs are operator-provided and never committed.
export ROF12_GITHUB_URL='https://github.com/cristianjos38-dot/rof12'
export ROF12_N8N_URL='https://<operator-n8n-host>/workflow/<operator-id>'
osascript scripts/recording/focus_windows.applescript "$ROF12_GITHUB_URL" "$ROF12_N8N_URL"

# 4. With the n8n canvas visible, trigger its button through Chrome automation.
osascript scripts/recording/trigger_n8n.applescript scripts/recording/trigger_n8n.js

# 5. Start 30 FPS recording. Stop only after the incident is resolved.
bash scripts/recording/record_screen.sh
# type: CONFIRM_INCIDENT
```

For human-paced rehearsal, use the dry run first and add `--send` only with the
intended field visibly focused:

```bash
python3.11 scripts/recording/type_human.py 'PREGUNTA SIMULADA: ¿qué está pasando con ese correo?' --seed 18
python3.11 scripts/recording/type_human.py 'PREGUNTA SIMULADA: ¿qué está pasando con ese correo?' --send
```

The local fallback node is checked separately with:

```bash
curl --connect-timeout 2 --max-time 3 http://100.93.233.116:11434/api/tags
```

It is an optional rehearsal fallback only. The canonical model remains
`muse-spark-1.3`; no `llama-3.1-70b-instruct` integration is present in this
repository.
