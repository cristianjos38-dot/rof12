-- Local development bootstrap only. Production credentials must be provisioned by a secret manager.
CREATE ROLE rof12_owner LOGIN PASSWORD 'rof12_owner_dev' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE rof12_app LOGIN PASSWORD 'rof12_app_dev' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE rof12_executor LOGIN PASSWORD 'rof12_executor_dev' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE rof12_audit LOGIN PASSWORD 'rof12_audit_dev' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER DATABASE rof12 SET search_path = rof12, public;
GRANT CONNECT ON DATABASE rof12 TO rof12_owner, rof12_app, rof12_executor, rof12_audit;
GRANT CREATE ON DATABASE rof12 TO rof12_owner;

