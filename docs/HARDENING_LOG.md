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
