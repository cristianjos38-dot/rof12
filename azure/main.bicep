param location string = resourceGroup().location
param environmentName string = 'rof12'
@secure()
param postgresAdminPassword string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: { retentionInDays: 30 }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${environmentName}-postgres'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: 'rof12_owner'
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${environmentName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logAnalytics.properties.customerId, sharedKey: logAnalytics.listKeys().primarySharedKey }
    }
  }
}

resource api 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${environmentName}-api'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environment.id
    configuration: { ingress: { external: true, targetPort: 8000, transport: 'http' }, secrets: [] }
    template: {
      containers: [{
        name: 'api'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        env: [{ name: 'MODEL_MODE', value: 'mock' }]
        resources: { cpu: 0.5, memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${environmentName}-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    sku: { family: 'A', name: 'standard' }
  }
}

output apiName string = api.name
output postgresName string = postgres.name
output keyVaultName string = vault.name
