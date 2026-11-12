# Azure deployment scaffold

The `azure/` and `azure.yaml` files define a Container App, PostgreSQL
Flexible Server, Log Analytics, and a Key Vault with RBAC. No password,
connection string, JWT key, or provider token is committed.

Before deployment, provision `postgresAdminPassword` through the azd/CI secret
store and replace the placeholder container image with the built ROF12 image.
The managed identity must receive only the required Key Vault and database
permissions.

```bash
azd auth login
azd env new rof12-staging
azd env set AZURE_LOCATION eastus
azd up
```

Trust boundary:

```text
Agent 365 / Foundry -> ROF12 API -> SecurityGate -> Container App
                                      |-> PostgreSQL Flexible Server (RLS)
                                      |-> Key Vault (secrets only)
```

`azd up` was not executed in local CI validation; cloud credentials and an
approved Azure subscription are required.
