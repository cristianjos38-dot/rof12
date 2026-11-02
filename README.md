# ROF12 — Secure Runtime for Intelligent Agents

ROF12 es un runtime local orientado a agentes inteligentes con autoridad del servidor, aislamiento multi-tenant, decisiones default-deny, procedencia trazable y ejecución financiera con precisión exacta.

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

El `perception-worker` está configurado con aislamiento Docker; su ejecución en un daemon Docker real sigue pendiente de validación en este entorno.

## Requisitos previos

- Docker Desktop con el daemon iniciado.
- Python 3.12 recomendado (el código declara compatibilidad desde Python 3.9).
- PostgreSQL 16 mediante Docker Compose.

## Instalación y demo local

```bash
python3 -m pip install -e '.[dev]'
docker compose up -d postgres
make migrate
make seed
MODEL_MODE=mock make check
docker compose up -d rof12
```

La API queda disponible en `http://localhost:8000`; el healthcheck es `GET /health`. El endpoint protegido de demostración es `GET /tasks/context` y requiere Bearer JWT más `X-Tenant-ID`.

Para generar un token de laboratorio:

```bash
python3 scripts/dev_token.py user_001
```

Los claims del token son únicamente `sub`, `iss`, `aud`, `exp` e `iat`. El tenant y el rol se resuelven contra PostgreSQL.

## Verificación rápida para jueces

```bash
make check
MODEL_MODE=mock python3 -m pytest
python3 -m alembic upgrade head --sql > /tmp/rof12-schema.sql
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

