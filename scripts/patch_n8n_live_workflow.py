#!/usr/bin/env python3
"""Patch the live n8n workflow with the ROF12 inspection gate."""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests

WORKFLOW_ID = "kQ3IZRYrxdsLdmVd"
BASE_URL = "http://100.109.127.88:5678"
ARTIFACT = Path("artifacts/workflow_import_ready.json")
OLLAMA_BASE_URL = "http://100.93.233.116:11434"
OLLAMA_CREDENTIAL_ID = "nFNZLUVaBD7e2KYq"
OLLAMA_CREDENTIAL_NAME = "Ollama account"
ROF12_N8N_URL = "http://100.122.213.76:8012/v1/n8n/inspect-email"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def node(nodes, name=None, types=()):
    for item in nodes:
        if name and item.get("name", "").casefold() == name.casefold():
            return item
        if types and item.get("type") in types:
            return item
    return None


def extract_node(nodes):
    return node(nodes, "Extract from File") or node(nodes, "Extract From File") or next(
        (item for item in nodes if "extract" in f"{item.get('name', '')} {item.get('type', '')}".casefold()), None
    )


def normalise_nodes(nodes):
    """Apply the PDF/fallback settings without changing node identities."""
    gmail = node(nodes, "Gmail Trigger")
    if gmail:
        params = gmail.setdefault("parameters", {})
        params["simple"] = False
        params.setdefault("filters", {})["q"] = "to:gsgs01382@gmail.com has:attachment filename:pdf"
        params.setdefault("options", {})["downloadAttachments"] = True
    extract = extract_node(nodes)
    if extract:
        extract.setdefault("parameters", {})["operation"] = "pdf"
        extract["parameters"]["binaryPropertyName"] = "attachment_0"
        extract["continueOnFail"] = True
        extract["onError"] = "continueRegularOutput"
    return gmail, extract


def edge(name, index=0):
    return {"node": name, "type": "main", "index": index}


def patch(workflow: dict[str, Any]) -> dict[str, Any]:
    if isinstance(workflow, list):
        if len(workflow) != 1:
            raise RuntimeError("El export debe contener exactamente un workflow")
        workflow = workflow[0]
    result = copy.deepcopy(workflow)
    nodes = result.setdefault("nodes", [])
    connections = result.setdefault("connections", {})
    extract = extract_node(nodes)
    agent = node(nodes, "AI Agent")
    if not extract or not agent:
        raise RuntimeError("No se encontraron Extract from File y AI Agent")
    gmail, extract = normalise_nodes(nodes)

    fallback = node(nodes, "Preparar contenido para ROF12")
    if not fallback:
        x, y = extract.get("position", [0, 0])
        fallback = {"parameters": {
            "mode": "runOnceForEachItem",
            "jsCode": "const text = $json.text || $json.textPlain || $json.snippet || $json.body || 'Factura sin contenido legible';\nconst sender = $(\"Gmail Trigger\").item.json.from?.value?.[0]?.address || $(\"Gmail Trigger\").item.json.from || 'remitente_desconocido';\nconst subject = $(\"Gmail Trigger\").item.json.subject || 'Sin Asunto';\nreturn { json: { sender, subject, document_text: text, tenant_id: 'tenant_001', agent_id: 'gmail_invoicing_agent' } };",
        }, "id": str(uuid.uuid4()), "name": "Preparar contenido para ROF12", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x + 220, y + 180]}
        nodes.append(fallback)

    gate = node(nodes, "ROF12 SecurityGate")
    if not gate:
        x, y = extract.get("position", [0, 0])
        gate = {"parameters": {
            "method": "POST", "url": ROF12_N8N_URL,
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ { sender: $json.sender || \"remitente_desconocido\", subject: $json.subject || \"Sin Asunto\", document_text: $json.document_text || \"Factura sin contenido legible\", tenant_id: \"tenant_001\", agent_id: \"gmail_invoicing_agent\" } }}",
        }, "id": str(uuid.uuid4()), "name": "ROF12 SecurityGate", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [x + 280, y]}
        nodes.append(gate)
    gate.setdefault("parameters", {}).update({
        "method": "POST", "url": ROF12_N8N_URL, "sendBody": True, "specifyBody": "json",
        "jsonBody": '={{ { sender: $json.sender || "remitente_desconocido", subject: $json.subject || "Sin Asunto", document_text: $json.document_text || "Factura sin contenido legible", tenant_id: "tenant_001", agent_id: "gmail_invoicing_agent" } }}',
    })

    branch = node(nodes, "¿Es Seguro?")
    if not branch:
        x, y = gate.get("position", [0, 0])
        branch = {"parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.is_safe }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}], "combinator": "and"}}, "id": str(uuid.uuid4()), "name": "¿Es Seguro?", "type": "n8n-nodes-base.if", "typeVersion": 2, "position": [x + 280, y]}
        nodes.append(branch)

    blocker = node(nodes, "Ataque Bloqueado por ROF12")
    if not blocker:
        x, y = branch.get("position", [0, 0])
        blocker = {"parameters": {"jsCode": 'throw new Error("ROF12: ataque bloqueado antes del AI Agent");'}, "id": str(uuid.uuid4()), "name": "Ataque Bloqueado por ROF12", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x + 280, y + 180]}
        nodes.append(blocker)

    ollama = node(nodes, "Ollama Chat Model")
    if ollama:
        ollama["credentials"] = {"ollamaApi": {"id": OLLAMA_CREDENTIAL_ID, "name": OLLAMA_CREDENTIAL_NAME}}
        ollama.setdefault("parameters", {})["baseUrl"] = OLLAMA_BASE_URL
    if agent:
        agent.setdefault("parameters", {})["text"] = "=Analiza el siguiente contenido extraído del documento PDF y genera un resumen claro para el operador:\n\nRemitente: {{ $json.sender }}\nAsunto: {{ $json.subject }}\n\nContenido del PDF:\n{{ $json.document_text }}"

    connections[extract["name"]] = {"main": [[edge(fallback["name"])]]}
    connections[fallback["name"]] = {"main": [[edge(gate["name"])]]}
    connections[gate["name"]] = {"main": [[edge(branch["name"])]]}
    connections[branch["name"]] = {"main": [[edge(agent["name"])], [edge(blocker["name"])]]}
    result["id"] = result.get("id") or WORKFLOW_ID
    result["active"] = True
    return result


def save(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=os.getenv("N8N_BASE_URL", BASE_URL))
    parser.add_argument("--workflow-id", default=WORKFLOW_ID)
    parser.add_argument("--env-file", default=".env.staging")
    parser.add_argument("--input-workflow", type=Path)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--no-activate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env(Path(args.env_file))
    api_key = args.api_key or os.getenv("N8N_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    basic = None
    if os.getenv("N8N_BASIC_AUTH_USER") and os.getenv("N8N_BASIC_AUTH_PASSWORD"):
        basic = (os.environ["N8N_BASIC_AUTH_USER"], os.environ["N8N_BASIC_AUTH_PASSWORD"])
    url = f"{args.base_url.rstrip('/')}/api/v1/workflows/{args.workflow_id}"
    try:
        response = requests.get(url, headers=headers, auth=basic, timeout=20)
        response.raise_for_status()
        workflow = response.json()
    except requests.RequestException as exc:
        if not args.input_workflow or not args.input_workflow.exists():
            diagnostic = {"workflowId": args.workflow_id, "error": str(exc), "message": "Importa un export local o configura N8N_API_KEY."}
            save(diagnostic, args.artifact)
            print(f"[FAIL] n8n no respondió; usa la importación de {args.artifact} en Chrome", file=sys.stderr)
            return 2
        workflow = json.loads(args.input_workflow.read_text(encoding="utf-8"))
        print(f"[WARN] n8n no respondió; usando export local {args.input_workflow}")

    patched = patch(workflow)
    save(patched, args.artifact)
    print(f"[PASS] Respaldo guardado en {args.artifact}")
    if args.dry_run:
        return 0
    payload = {key: patched[key] for key in ("name", "nodes", "connections", "settings", "staticData", "active") if key in patched}
    updated = requests.put(url, headers=headers, auth=basic, json=payload, timeout=30)
    updated.raise_for_status()
    if not args.no_activate:
        activation = requests.post(f"{url}/activate", headers=headers, auth=basic, timeout=20)
        if activation.status_code >= 400:
            print(f"[WARN] Activación explícita HTTP {activation.status_code}; PUT incluyó active=true")
    print(f"[PASS] Flujo actualizado en n8n live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
