# ROF12 staging: Supabase y Cloudflare

Esta guía configura infraestructura; no cambia contratos ni lógica comercial. No contiene secretos ni valores reales.

## Variables y roles

Configure `DATABASE_URL` con el pooler de Supabase usando exclusivamente `rof12_app`. Configure `DATABASE_OWNER_URL` solo para Alembic y seed; nunca se inyecta en el contenedor API. No use el superusuario `postgres` para la aplicación.

Para Transaction Pooler establezca `DATABASE_PREPARE_THRESHOLD=none`, que hace que Psycopg use `prepare_threshold=None`. Para Session Pooler puede omitirse.

Configure en el entorno de staging: `APP_ENV=staging`, `DATABASE_URL=postgresql+psycopg://rof12_app.hcuimdowcjwdjtmabkyy:<password>@<pooler>:6543/postgres`, `DATABASE_OWNER_URL=postgresql+psycopg://rof12_owner.hcuimdowcjwdjtmabkyy:<password>@<session-pooler>:5432/postgres`, `DATABASE_PREPARE_THRESHOLD=none`, `JWT_ISSUER=https://hcuimdowcjwdjtmabkyy.supabase.co/auth/v1`, `JWT_AUDIENCE=authenticated`, `JWT_ALGORITHM=<provider-algorithm>` y `JWT_PUBLIC_KEY=<injected-from-secret-manager>`. El proyecto Supabase de staging verificado en esta sesión publica una clave ES256.

`JWT_PUBLIC_KEY` se inyecta como secreto. El verificador conserva la lista cerrada de claims (`sub`, `iss`, `aud`, `exp`, `iat`); tenant y roles continúan resolviéndose desde la base de datos.

En Supabase, mantenga las tablas en el esquema `rof12`, habilite RLS y no exponga `rof12` en los esquemas públicos de PostgREST. ROF12 usa conexión PostgreSQL directa/pooler y no depende de PostgREST. La creación de roles puede requerir una conexión administrativa directa y debe ejecutarse una sola vez, fuera del contenedor API.

## Migración, seed y smoke test

Ejecute con secretos exportados, sin escribirlos en archivos versionados:

```bash
export DATABASE_URL='postgresql+psycopg://rof12_app.hcuimdowcjwdjtmabkyy:<password>@<pooler>:6543/postgres'
export DATABASE_OWNER_URL='postgresql+psycopg://rof12_owner.hcuimdowcjwdjtmabkyy:<password>@<session-pooler>:5432/postgres'
export DATABASE_PREPARE_THRESHOLD=none
alembic upgrade head
DATABASE_OWNER_URL="$DATABASE_OWNER_URL" make seed
export STAGING_BASE_URL='https://staging.example.invalid'
make smoke-staging
```

## Cloudflare

Configure el hostname con TLS **Full (strict)**, WAF administrado y rate limiting por IP/identidad para escritura y `/v1/security/*`. Configure Cloudflare Access delante de `/ui/*` y `/v1/security/*`; el backend sigue validando JWT y rol. Para una demostración temporal puede usarse `cloudflared tunnel --url http://localhost:8000`; nunca se commitea su token.

## Evidencia de reparación Fase 17

El router de tareas persiste cada evaluación del Security Gate mediante `SQLAlchemyAuditRepository` dentro de una transacción con `app.tenant_id` fijado localmente. El smoke acepta `--url` o `STAGING_BASE_URL`, prueba un caso ALLOW y un payload adversarial que produce DENY, y verifica la cadena en PostgreSQL cuando recibe `DATABASE_OWNER_URL`.

El proyecto identificado por configuración local tiene ref `hcuimdowcjwdjtmabkyy`. La consulta de auditoría ejecutada en esta sesión no pudo conectar (`OperationalError`), por lo que el conteo actual no se certifica aquí. La evidencia histórica documenta `audit_events_count=4` con `ALLOW=2`, `DENY=1` y `QUARANTINE=1`; no se debe interpretar como evidencia de siete eventos en Supabase. El hostname ngrok no pudo validarse en esta sesión porque el cliente carece de authtoken (`ERR_NGROK_4018`), por lo que `docs/BUILD_STATE.md` conserva `CURRENT_PHASE: 16`.
