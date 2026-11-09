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
