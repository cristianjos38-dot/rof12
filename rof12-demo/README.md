# ROF12 — Demos de seguridad para agentes de IA

Tres demos ejecutables en terminal que muestran el mismo principio desde tres ángulos:

> **Una propuesta del agente no es un permiso.** ROF12 inspecciona lo que el agente lee,
> evalúa lo que propone y solo ejecuta con un permiso acotado, firmado y auditable.

Todo corre en local con **Python 3.10+ y solo la librería estándar** (sin `pip install`).

## Ejecutar

```bash
cd rof12-demo
python3 make_assets.py            # genera los PDFs (run_demo lo hace solo si faltan)
python3 run_demo.py               # las 3 demos seguidas
python3 run_demo.py 1             # solo una (1, 2 o 3)
python3 run_demo.py all --step    # pausa con Enter entre pasos (para grabar o presentar)
python3 run_demo.py 3 --interactive   # tú apruebas/rechazas el hold en vivo
python3 run_demo.py audit --tamper-test   # verifica la cadena y prueba que detecta manipulación
python3 -m unittest discover -s tests -v  # 12 pruebas
```

Opciones útiles para grabación: `--fast` (sin retardos), `--delay 0.25` (más lento), `--no-color`,
`--force-color` (colores aunque rediriges la salida).

## Qué muestra cada demo

### DEMO 01 — The Hidden Instruction · *adversarial input*
`assets/invoice_hidden.pdf` se ve como una factura normal de $45. Por dentro lleva instrucciones
ocultas con 4 técnicas: **texto blanco de 1pt**, **render mode invisible (Tr 3)**, **texto fuera de página**
y una instrucción en **metadatos**. El script enseña:
1. Lo que ve el humano vs. lo que lee un extractor estándar (`pdftotext`, `pypdf`).
2. Capa 1 estructura (JS, OpenAction, Launch…) · Capa 2 ocultamiento · Capa 3 patrones de inyección · Capa 4 score → `CRITICAL`.
3. Decisión `DENY` + cuarentena del documento.
4. Contrafactual: qué habría propuesto un agente ingenuo sin ROF12.
5. Defensa en profundidad: aunque el documento se colara, sus propuestas quedan **contaminadas** (`TAINTED_PROVENANCE`).
6. Control: la factura limpia (con encabezado blanco sobre banda azul) **no** se bloquea → sin falsos positivos obvios.

### DEMO 02 — The Unauthorized Action · *execution blocked*
Tres propuestas, tres `DENY`, cero ejecuciones:
- **A**: reembolso de $1,850 (techo autorizado $500) → `REFUND_EXCEEDS_CEILING`; además se intenta ejecutar sin permit → `NO_PERMIT`.
- **B**: `db.export_customers` (capacidad `never_grant`) → `CAPABILITY_NOT_GRANTED`.
- **C**: reembolso pequeño de **otro cliente** → `CUSTOMER_SCOPE_MISMATCH` (monto bajo el auto-allow, pero fuera de alcance).

### DEMO 03 — The Controlled Execution · *authorized workflow*
- **ALLOW**: reembolso de $45 → permit acotado (tool, tarea, hash de argumentos, 1 uso, expira) → ejecución → replay bloqueado.
- **REQUIRE_APPROVAL**: reembolso de $320 → `hold_id` ligado al hash de la propuesta → aprobación humana.
- **Manipulación**: el agente cambia $320 → $480 tras la aprobación → `HOLD_BINDING_MISMATCH`.
- **Revalidación**: se reevalúan *todas* las reglas con estado fresco → `ALLOW` → ejecución. Reusar el hold → `HOLD_ALREADY_USED`.
- Registro de auditoría con cadena de hashes, verificado al final.

## Estructura

```
run_demo.py            CLI de las demos
make_assets.py         genera los PDFs (limpio y con instrucciones ocultas)
policy/policy.json     grants, techos de reembolso, TTLs, umbrales de riesgo
rof12/inspector.py     parser PDF + detección de ocultamiento + patrones + score
rof12/gate.py          reglas, ALLOW/DENY/REQUIRE_APPROVAL, permits HMAC, holds, revalidación
rof12/tools.py         herramientas simuladas; el runtime exige permit válido
rof12/agent.py         agente SIMULADO (determinista) — punto de enganche para un LLM real
rof12/audit.py         log JSONL con cadena de hashes
rof12/demos.py · ui.py guiones y salida de terminal
tests/test_rof12.py    12 pruebas
out/audit.jsonl        se regenera en cada corrida
```

## Cambiar la política
Edita `policy/policy.json`: por ejemplo `refunds.auto_allow_max` (100), `refunds.approval_max` (500),
`grants.TKT-1042.allowed_tools`, o los umbrales `document_risk`. Las demos reflejan el cambio sin tocar código.

## Honestidad técnica (qué NO es esto todavía)
- El **agente es simulado** y determinista para que la demo sea reproducible. Para usar un modelo real
  (p. ej. Meta Model API) reemplaza `NaiveAgent` por una llamada que devuelva objetos `Proposal`; el Gate no cambia.
- Las herramientas y la base de datos son **en memoria**. En producción serían FastAPI + PostgreSQL.
- El inspector PDF es heurístico y propio: no interpreta fuentes CID, XObjects, object streams ni
  transformaciones `cm`; los reporta como `coverage_gaps`. No sustituye un análisis forense completo.
- Los patrones de inyección son reglas (EN/ES); un atacante creativo puede evadirlas. Por eso existe la
  capa de **procedencia + permisos**: aunque la detección falle, el agente no puede ejecutar fuera de su grant.
- La clave HMAC de los permits se genera por proceso; en producción va en un gestor de secretos.
