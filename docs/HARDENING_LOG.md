# Hardening log

## Fase 0 — Higiene de CI

- Rama: `feat/hardening-grandes-ligas`.
- Añadido `.github/workflows/ci.yml` para `push` a `master` y pull requests,
  con Python 3.11 y 3.12, `MODEL_MODE=mock` y `make check`.
- `deploy-staging.yml` quedó únicamente bajo `workflow_dispatch`; no recibe
  secretos en el workflow de CI.
- Las dependencias de desarrollo ahora incluyen Ruff, mypy, coverage y
  pytest-cov. `pytest` se fijó en `>=9.0.3` por la alerta `PYSEC-2026-1845`.
- `make check` ejecuta Ruff, formato Ruff, compilación, mypy focalizado,
  `pip-audit --skip-editable` y pytest con cobertura mínima del 70%.

### Criterio de aceptación

Validado localmente el 2026-11-04 con Python 3.11 y `MODEL_MODE=mock`:

- Ruff: PASS.
- Ruff format: PASS.
- mypy estricto focalizado en los cuatro módulos requeridos: PASS.
- pip-audit: PASS; no se encontraron vulnerabilidades conocidas. El paquete
  editable local `rof12` se omite porque no está publicado en PyPI.
- pytest: **89 passed, 1 skipped, 0 failed**.
- Cobertura: **77.58%**, umbral 70% cumplido.

No se modificaron los contratos congelados de `app/domain/`. Las pruebas de
PostgreSQL vivo, RLS operacional y replay 7/7 quedan para la Fase 1.

## Fase 1 — cerrada localmente; CI pendiente

Se prepararon el servicio PostgreSQL 16 y el test `tests/security/test_rls_live.py`
para CI, además de `scripts/bench_gate.py`. La validación local no pudo levantar
Docker en este equipo. El benchmark determinista local sí se ejecutó con 1.000
decisiones en modo mock: promedio 0.0021 ms, p50 0.0021 ms y p95 0.0022 ms en
macOS 26.6.2 arm64, Python 3.11.15. El replay de ataque local pasó: 2
`QUARANTINE` y 5 `DENY`, con cadena de auditoría válida.

El criterio fue corregido para separar corpus: `demo.replay` exige 1 `ALLOW` y
6 `QUARANTINE`, mientras `scripts/run_attack_round.py` exige 2 `QUARANTINE`
y 5 `DENY`. La discrepancia quedó resuelta sin modificar el núcleo.
El test RLS vivo queda pendiente de la corrida CI porque Docker no está
disponible localmente.

La primera corrida del PR (`42714220252`) falló en `make check` porque el
Makefile fijaba `python3.11`, que no existe en el job Python 3.12. Se corrigió
para usar el intérprete seleccionado por CI. También se corrigió el assert del
replay, que contaba 7 rechazos aunque el corpus protegido esperado contiene 1
`ALLOW` y 6 `QUARANTINE`.

La segunda corrida (`42715440117`) confirmó que el intérprete ya era portable,
pero `pip-audit` encontró `setuptools 79.0.1` en los runners. Se fijó
`setuptools>=84.1.0` en el build system y se añadió una actualización explícita
antes de instalar el proyecto en CI.

La tercera corrida (`42715663232`) pasó auditoría y análisis estático, pero
falló al persistir eventos con el rol `rof12_app`: faltaba `USAGE` sobre las
secuencias PostgreSQL, produciendo `503` en las rutas de tareas. También mostró
que el test RLS consultaba el tenant equivocado en la sesión. Se añadió la
migración `0008_grant_sequence_usage` y se corrigió el test para mantener fija
la identidad de sesión al comprobar lecturas cruzadas.

## Fase 2 — puente MCP

Se añadió `rof12/mcp_server.py` con el SDK oficial MCP y dos herramientas:
`evaluate_proposal` y `request_permit`. Ambas reutilizan `SecurityGate`; no hay
ejecución de herramientas ni bypass de política. `scripts/mcp_smoke.py` verificó
`ALLOW` para `refund_service` y `DENY/UNKNOWN_TOOL` para una herramienta no
registrada. Se añadieron `docs/MCP.md` y `examples/mcp_client.py`. Las
dependencias MCP y OpenTelemetry quedaron declaradas en el paquete y
`pip-audit` local no reportó vulnerabilidades.

Se añadió `app.observability` con spans y contadores por decisión. El SDK API
queda no-op cuando no existe `OTEL_EXPORTER_OTLP_ENDPOINT`; con endpoint
configurado activa el exportador OTLP HTTP. La autenticación acepta únicamente
el claim opcional `agent_id`, mientras tenant, rol y membresía siguen siendo
resueltos en servidor. `docs/IDENTITY.md` documenta la costura futura con
Microsoft Entra Agent ID sin implementar Entra.

Se añadió el scaffold `azure/` + `azure.yaml` para Container Apps, PostgreSQL
Flexible Server, Key Vault y Log Analytics, además de `docs/DEPLOY_AZURE.md`.
No contiene secretos; `azd up` queda pendiente de una suscripción Azure
autorizada. `docs/A2A_DESIGN.md` documenta el límite de autoridad para futuras
integraciones A2A.

## Fase 5 — presentación y distribución

Se añadieron diagrama de arquitectura y encaje Agent 365/Foundry al README,
`CHANGELOG.md`, `CONTRIBUTING.md`, política de divulgación en `SECURITY.md`,
`docs/POLICIES.md` y `contrib/README.md` para marcar voz/n8n como adaptadores
experimentales. El paquete queda preparado para PyPI con versión `1.0.0`, pero
no se publicó ni se creó un release remoto: esta rama no está fusionada y no se
dispone de un token PyPI autorizado.

## Cierre — SBOM de release

`artifacts/sbom.json` se retiró del índice y quedó ignorado, conservándose en
disco para adjuntarlo a releases. `make sbom` lo regenera localmente y
`git check-ignore` confirmó la regla; no se reescribió el historial anterior.

## Cierre — MCP y VerityFlow

El adaptador MCP ahora comparte el resolvedor server-side entre
`evaluate_proposal` y `request_permit`: cuando hay conexión y capacidad
configuradas, ambos ejecutan VerityFlow y el SecurityGate reales; el fallback
sintético sigue siendo explícito. Se añadieron pruebas deterministas para una
propuesta permitida con permiso opaco y otra rechazada sin permiso.

## Cierre — identificación de Supabase

La configuración local permitió identificar el ref público
`hcuimdowcjwdjtmabkyy`. La consulta actual de `rof12.audit_events` no pudo
conectar y se registró como pendiente; no se afirmó que las siete decisiones
del CI vivan en Supabase. La evidencia histórica de staging sigue indicando
cuatro eventos (`ALLOW=2`, `DENY=1`, `QUARANTINE=1`).

## Cierre — gobernanza del PR

El PR #1 fue renombrado a `Hardening Fases 0–5: RLS, replay, MCP, evaluación
adversarial, producción y distribución` y continúa abierto contra `master`.

## Cierre — CI del PR

La corrida `43257673019` terminó verde en Python 3.11 y 3.12:
`100 passed, 1 skipped`. El único skip es la prueba de resiliencia que requiere
un Docker de PostgreSQL adicional; la prueba RLS viva se ejecutó mediante
`ROF12_LIVE_DB_URL`. Verify, Replay (`1 ALLOW + 6 QUARANTINE`) y corpus
adversarial (`5 DENY + 2 QUARANTINE`) terminaron correctamente.

## Fase 3 — endurecimiento de producción

Se endureció la imagen Docker con build multi-stage, usuario UID/GID 10001 y
digests fijados para Python y PostgreSQL. La API incorpora límite de cuerpo de
10 MiB, endpoint Prometheus `/metrics` e idempotencia concurrente por
`operation_id`; el test de dos hilos pasa con una sola ejecución. Se añadieron
Gitleaks pre-commit, Dependabot, generación CycloneDX (`make sbom`) y la guía
de backup/restore y migraciones en `docs/OPERATIONS.md`. La auditoría histórica
con `git log --all -p -S` solo encontró placeholders y credenciales
`*_dev_only` de CI/local, no secretos reales.

## Fase 4 — evaluación rigurosa

El corpus v2 suma 25 casos documentados: 7 v1 y 18 v2. El corpus legítimo
contiene 20 fixtures sintéticos y registra 0/20 falsos positivos (0% en este
laboratorio). Se añadieron propiedades Hypothesis para `Decimal`, expiración de
capacidades y manipulación de la cadena; el adaptador DevOps reutiliza el mismo
Gate con 1 caso permitido y 4 ataques denegados. La ruta MCP ahora intenta
resolver capacidad/pedido y ejecutar `VerityFlow` bajo RLS cuando recibe
`DATABASE_URL` y `ROF12_MCP_CAPABILITY_TOKEN`; sin ellos reporta
`synthetic_fallback` y no se presenta como verificación real. Validación local:
96 passed, 2 skipped, cobertura 75.04%.
