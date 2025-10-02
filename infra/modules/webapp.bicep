param location string
param appServiceName string
param appServerFarmName string
param projectEndpoint string
param storageAccountKey string
param researchmodelName string
param modelName string
param bingsearch string
param bingsearchConnection string

param storageAccountName string // Add storage account name parameter
param tags object

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServerFarmName
  location: location
  sku: {
    name: 'S1'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
  tags: tags
}

resource web 'Microsoft.Web/sites@2022-03-01' = {
  name: appServiceName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      ftpsState: 'Disabled'
    }
    httpsOnly: true
  }
  identity: {
    type: 'SystemAssigned'
  }

  resource appSettings 'config' = {
    name: 'appsettings'
    properties: {
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
      WEBSITES_PORT: '8000'
      AZURE_STORAGE_CONTAINER_NAME: 'research-summaries'
      AZURE_INIT_BLOB_NAME: 'research_summary_inprogress.md'
      AZURE_INIT_BLOB_ADD_TIMESTAMP: 'true'
      AZURE_OVERWRITE_PLACEHOLDER: 'false'
      RESEARCH_PYTHON: '/usr/bin/python3.11'
      STARTUP_COMMAND: 'gunicorn --bind 0.0.0.0:$PORT app:app'
      AZURE_STORAGE_ACCOUNT_NAME: storageAccountName // Use passed storage account name
      AZURE_STORAGE_ACCOUNT_KEY: storageAccountKey // Use passed storage account key
      PROJECT_ENDPOINT: projectEndpoint
      BING_RESOURCE_NAME: bingsearchConnection
      BING_RESOURCE_REGION: location
      DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME: researchmodelName
      MODEL_DEPLOYMENT_NAME: modelName
    }
  }

  resource logs 'config' = {
    name: 'logs'
    properties: {
      applicationLogs: {
        fileSystem: {
          level: 'Verbose'
        }
      }
      detailedErrorMessages: {
        enabled: true
      }
      failedRequestsTracing: {
        enabled: true
      }
      httpLogs: {
        fileSystem: {
          enabled: true
          retentionInDays: 1
          retentionInMb: 35
        }
      }
    }
  }
}

// RBAC Role Assignments for the Web App's Managed Identity

// Azure AI Developer role assignment
resource aiDeveloperRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, web.id, '64702f94-c441-49e6-a78b-ef80e0188fee')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee') // Azure AI Developer
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Contributor role assignment
resource blobDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, web.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cognitive Services User role assignment
resource cognitiveServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, web.id, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output WEB_URI string = 'https://${web.properties.defaultHostName}'
output WEB_PRINCIPAL_ID string = web.identity.principalId

