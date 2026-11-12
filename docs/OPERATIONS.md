# Production operations

## Secrets and dependencies

Gitleaks runs as a pre-commit hook and Dependabot monitors pip and GitHub
Actions. Generate the local SBOM with `make sbom`; the output is an ignored
artifact and must be attached to a release, never committed with secrets.

## Backup and restore

Use PostgreSQL's standard tools against the owner-controlled database:

```bash
pg_dump --format=custom "$DATABASE_OWNER_URL" > rof12.dump
pg_restore --clean --if-exists --dbname "$DATABASE_OWNER_URL" rof12.dump
```

Restore into an isolated database first, run migrations, verify the audit chain,
then promote. RLS and role grants must be checked after restore.

## Migrations

CI validates the Alembic graph and applies `upgrade head`. Destructive
downgrades require a disposable database and an explicit operator review; no
production downgrade is automatic.
