# ROF12 staging: Supabase y Cloudflare

Esta guía configura infraestructura; no cambia contratos ni lógica comercial. No contiene secretos ni valores reales.

## Variables y roles

Configure `DATABASE_URL` con el pooler de Supabase usando exclusivamente `rof12_app`. Configure `DATABASE_OWNER_URL` solo para Alembic y seed; nunca se inyecta en el contenedor API. No use el superusuario `postgres` para la aplicación.

Para Transaction Pooler establezca `DATABASE_PREPARE_THRESHOLD=none`, que hace que Psycopg use `prepare_threshold=None`. Para Session Pooler puede omitirse.

Configure en el entorno de staging: `APP_ENV=staging`, `DATABASE_URL=postgresql+psycopg://rof12_app.<ref>:<password>@<pooler>:6543/postgres`, `DATABASE_OWNER_URL=postgresql+psycopg://rof12_owner.<ref>:<password>@<session-pooler>:5432/postgres`, `DATABASE_PREPARE_THRESHOLD=none`, `JWT_ISSUER=https://<ref>.supabase.co/auth/v1`, `JWT_AUDIENCE=authenticated`, `JWT_ALGORITHM=RS256` y `JWT_PUBLIC_KEY=<injected-from-secret-manager>`.

`JWT_PUBLIC_KEY` se inyecta como secreto. El verificador conserva la lista cerrada de claims (`sub`, `iss`, `aud`, `exp`, `iat`); tenant y roles continúan resolviéndose desde la base de datos.

En Supabase, mantenga las tablas en el esquema `rof12`, habilite RLS y no exponga `rof12` en los esquemas públicos de PostgREST. ROF12 usa conexión PostgreSQL directa/pooler y no depende de PostgREST. La creación de roles puede requerir una conexión administrativa directa y debe ejecutarse una sola vez, fuera del contenedor API.

## Migración, seed y smoke test

Ejecute con secretos exportados, sin escribirlos en archivos versionados:

```bash
export DATABASE_URL='postgresql+psycopg://rof12_app.<ref>:<password>@<pooler>:6543/postgres'
export DATABASE_OWNER_URL='postgresql+psycopg://rof12_owner.<ref>:<password>@<session-pooler>:5432/postgres'
export DATABASE_PREPARE_THRESHOLD=none
alembic upgrade head
DATABASE_OWNER_URL="$DATABASE_OWNER_URL" make seed
export STAGING_BASE_URL='https://staging.example.invalid'
make smoke-staging
```

## Cloudflare

Configure el hostname con TLS **Full (strict)**, WAF administrado y rate limiting por IP/identidad para escritura y `/v1/security/*`. Configure Cloudflare Access delante de `/ui/*` y `/v1/security/*`; el backend sigue validando JWT y rol. Para una demostración temporal puede usarse `cloudflared tunnel --url http://localhost:8000`; nunca se commitea su token.
