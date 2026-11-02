from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "migrations" / "versions" / "0001_phase3_persistence_rls.py"


def test_phase3_schema_has_numeric_money_and_composite_foreign_keys():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "NUMERIC(12, 2)" in sql
    assert "FOREIGN KEY (tenant_id, order_id)" in sql
    assert "FLOAT" not in sql.upper()


def test_phase3_schema_enforces_rls_and_role_boundaries():
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in ("tenants", "orders", "order_balances", "refunds", "audit_events"):
        assert f"ALTER TABLE rof12.{table} ENABLE ROW LEVEL SECURITY" in sql
    assert "current_setting('app.tenant_id', true)" in sql
    assert "REVOKE INSERT, UPDATE, DELETE ON rof12.refunds, rof12.order_balances FROM rof12_app" in sql
    assert "GRANT INSERT ON rof12.refunds TO rof12_executor" in sql
    assert "GRANT UPDATE (refundable_balance) ON rof12.orders TO rof12_executor" in sql
    assert "GRANT SELECT, INSERT ON rof12.audit_events TO rof12_audit" in sql
    assert "REVOKE UPDATE, DELETE ON rof12.audit_events FROM rof12_audit" in sql


def test_core_security_tables_and_metadata_are_present():
    closure = (ROOT / "migrations" / "versions" / "0002_add_core_security_tables.py").read_text(encoding="utf-8")
    assert "CREATE TABLE rof12.users" in closure
    assert "CREATE TABLE rof12.memberships" in closure
    assert "CREATE TABLE rof12.provenance_records" in closure
    assert "FOREIGN KEY (tenant_id, user_id)" in closure
    assert "ALTER TABLE rof12.orders" in closure
    assert "REVOKE UPDATE, DELETE ON rof12.provenance_records" in closure

    from app.persistence.tables import metadata

    assert {"rof12.users", "rof12.memberships", "rof12.provenance_records"}.issubset(metadata.tables)
    assert {"rof12.documents", "rof12.document_fragments"}.issubset(metadata.tables)


def test_document_migration_is_tenant_isolated_and_append_only():
    migration = (ROOT / "migrations" / "versions" / "0003_add_isolated_documents.py").read_text(encoding="utf-8")
    assert "CREATE TABLE rof12.documents" in migration
    assert "CREATE TABLE rof12.document_fragments" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "current_setting('app.tenant_id', true)" in migration
    assert "REVOKE UPDATE, DELETE ON rof12.documents, rof12.document_fragments" in migration

