-- Apply only after Alembic has created the rof12 tables.
GRANT USAGE ON SCHEMA rof12 TO rof12_app, rof12_executor, rof12_audit;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA rof12 TO rof12_app;
REVOKE INSERT, UPDATE, DELETE ON TABLE rof12.refunds, rof12.order_balances FROM rof12_app;
GRANT SELECT ON ALL TABLES IN SCHEMA rof12 TO rof12_executor;
GRANT INSERT ON TABLE rof12.refunds TO rof12_executor;
GRANT UPDATE (refundable_balance) ON TABLE rof12.orders TO rof12_executor;
GRANT SELECT, INSERT ON TABLE rof12.audit_events TO rof12_audit;
REVOKE UPDATE, DELETE ON TABLE rof12.audit_events FROM rof12_audit;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rof12 TO rof12_app, rof12_executor, rof12_audit;
