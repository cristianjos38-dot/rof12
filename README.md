# ROF12 — Runtime de Ejecución Segura y Freno Universal para Agentes de IA

ROF12 es un runtime agnóstico a la industria para ejecutar agentes con autoridad limitada, verificable y revocable. El reembolso es el primer caso de prueba demostrable; el núcleo de Capacidades atómicas, Taint Tracking, VerityFlow, Policy Engine Default-Deny, Security Gate y Audit Chain se aplica de la misma forma a DevOps, Finanzas, Legal y APIs operativas.

## Estado para evaluación

| Fase | Estado | Evidencia principal |
|---|---|---|
| F0 | Completada | Scaffold, configuración, healthcheck y pruebas locales |
| F1 | Completada | Contratos Pydantic estrictos y `MODEL_MODE=mock` |
| F2 | Completada | Gate de reembolsos, límites, aprobación, cuarentena e idempotencia |
| F3 | Completada | PostgreSQL, Alembic, RLS, FKs compuestas y roles G5 |
| F4 | Completada | JWT cerrado, `AuthContext`, membresías activas y provenance tainted |
| F5 | Completada | Ingesta documental aislada, SHA-256, storage seguro y RLS |
| F6 | Completada | Inspección PDF, OCR intercambiable, análisis visual y risk analyzer neutral |
| F7 | Completada | Capabilities hash-only, consumo atómico, expiración y revocación |
| F8 | Completada | VerityFlow V1–V6 determinista y financiero con `Decimal` |
| F9 | Completada | Policy Engine puro, default-deny y taint-aware |
| F10 | Completada | Holds, Kill Switch y cadena de auditoría criptográfica |
| F11 | Completada | Security Gate, permisos internos y ejecución transaccional |
| F12 | Completada | Router Meta multi-modo, orquestador read-only, prompts aislados y Budget Guard |
| F13 | Completada | API FastAPI v1, observabilidad, rate limiting y administración de seguridad |
| F14 | Completada | Panel server-rendered seguro con Jinja2, HTMX local y aislamiento por tenant |
| F15 | Completada | Laboratorio adversarial, cobertura T-01–T-11 y quality gates reproducibles |
| F16 | En congelación | Replay Baseline vs Protected, arranque Docker limpio y entrega reproducible |

El `perception-worker` está configurado con aislamiento Docker; su ejecución en un daemon Docker real sigue pendiente de validación en este entorno.

## Requisitos previos

- Docker Desktop con el daemon iniciado.
- Python 3.11+ (Docker usa Python 3.12).
- PostgreSQL 16 mediante Docker Compose.

## Instalación y demo local

```bash
cp .env.example .env
mkdir -p secrets
printf 'lab-password\n' > secrets/db_password.txt
python3.11 -m pip install -e '.[dev]'
docker compose up -d --build
docker compose exec api alembic upgrade head
make seed
curl -fsS localhost:8000/health/ready
```

La API queda disponible en `http://localhost:8000`; `/health/ready` solo responde correctamente cuando PostgreSQL está disponible. El endpoint protegido de demostración es `GET /tasks/context` y requiere Bearer JWT más `X-Tenant-ID`.

Para ejecutar el replay comparativo con los mismos siete fixtures y registrar la tabla en PostgreSQL:

```bash
DATABASE_OWNER_URL=postgresql+psycopg://rof12_owner:rof12_owner_dev_only@localhost:5433/rof12 \
  python3.11 -m demo.replay
```

Para preparar una grabación con seed idempotente, healthcheck, UI autenticada y
salida legible Baseline vs Protected:

```bash
export DATABASE_OWNER_URL='<owner pooler URL>'
export DATABASE_URL='<app transaction-pooler URL>'
export DEMO_JWT="$(python3.11 scripts/dev_token.py user_001)"
make prep-demo
```

Use `python3.11 demo/run_demonstration.py --json` cuando se necesite salida
machine-readable; el modo predeterminado muestra `[BASELINE: VULNERABLE]` y
`[PROTECTED: BLOCKED]` para la grabación.

El modo Baseline usa únicamente un almacén ficticio en memoria y no importa `app`, no lee secretos ROF12 ni accede a rutas de almacenamiento protegidas. El modo Protected usa la percepción local de ROF12. La salida se consulta después de insertar y leer `rof12.demo_results`; no contiene resultados codificados manualmente.

Para generar un token de laboratorio:

```bash
python3.11 scripts/dev_token.py user_001
```

Los claims del token son únicamente `sub`, `iss`, `aud`, `exp` e `iat`. El tenant y el rol se resuelven contra PostgreSQL.

## Verificación rápida para jueces

```bash
make check
MODEL_MODE=mock python3.11 -m pytest
python3.11 -m alembic upgrade head --sql > /tmp/rof12-schema.sql
git status --short
```

`make check` compila la aplicación y ejecuta toda la suite sin APIs externas. La prueba de integración PostgreSQL requiere que Docker esté activo; `make seed` es idempotente y carga `tenant_001/user_001/order_1042` y el tenant aislado `tenant_002/user_002/order_9999`.

## Seguridad y publicación

- Los contratos de entrada usan `extra="forbid"` y no aceptan identidad declarada por el agente.
- El dinero usa `Decimal` en Python y `NUMERIC(12,2)` en PostgreSQL.
- Las tablas tenant-aware tienen RLS con `app.tenant_id` y claves foráneas compuestas.
- `.env`, `secrets/`, claves privadas y caches están excluidos por `.gitignore`.
- Las credenciales presentes en Compose/init son valores de laboratorio locales (`dev_only`/`*_dev`), nunca credenciales de producción.
- `MODEL_MODE=mock` evita dependencias externas durante las pruebas.

## Declaración de alcance

El historial público preparado para esta entrega contiene el baseline construido para ROF12 durante la semana del evento: F0–F5, contratos congelados en `contracts-frozen-1.0`, persistencia segura, autenticación, procedencia e ingesta documental. No se incorpora historial anterior ajeno al proyecto en este repositorio.

## Configuración del remoto público

Este checkout no tiene remoto configurado. Después de crear un repositorio vacío en GitHub o GitLab, configurar el destino y publicar únicamente el historial actual:

```bash
git remote add origin https://github.com/cristianjos38-dot/rof12.git
git push -u origin master --tags
```

El remoto canónico publicado es `https://github.com/cristianjos38-dot/rof12.git`; el remoto anterior se conserva localmente como `backup-gsgs01382-stack`. Verificar antes con:

```bash
git remote -v
git log --oneline --decorate --max-count=8
```

## Staging con Supabase y Cloudflare

La configuración de staging usa `rof12_app` para la API, `rof12_owner` únicamente para migraciones/seed y `DATABASE_PREPARE_THRESHOLD=none` cuando se utiliza Transaction Pooler. JWT se valida con `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ALGORITHM=RS256` y `JWT_PUBLIC_KEY`, siempre inyectados como secretos. Consulte [docs/SUPABASE_STAGING.md](docs/SUPABASE_STAGING.md).

Con las variables configuradas de forma segura, la validación reproducible es:

```bash
alembic upgrade head
DATABASE_OWNER_URL="$DATABASE_OWNER_URL" make seed
make smoke-staging
```

El workflow `.github/workflows/deploy-staging.yml` ejecuta checks, migraciones, seed y smoke test usando GitHub Environment `staging`. Cloudflare debe configurarse con TLS Full (strict), WAF, rate limiting y Access para `/ui/*` y `/v1/security/*`; ningún token de Cloudflare se almacena en el repositorio.

