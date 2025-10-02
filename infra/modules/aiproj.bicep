targetScope = 'resourceGroup'

param instanceId string

param location string = resourceGroup().location

param modelName string 
param modelVersion string 
param deploymentName string
param capacity int 
param deploymentType string 
param researchmodelName string
param researchmodelVersion string
param bingsearch string
param aiFoundryName string
param aiFoundryProjectName string 
param bingsearchconnection string


var projectName = length('proj${instanceId}') > 20 ? substring('proj${instanceId}', 0, 20) : 'proj${instanceId}'
var keyVaultName = length('kv${instanceId}') > 20 ? substring('kv${instanceId}', 0, 20) : 'kv${instanceId}'


resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'AIServices'
  sku: {
    name: 'S0'
    tier: 'Standard'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundryName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }


  
  resource deploy 'deployments@2025-04-01-preview' = {
    name: deploymentName
    properties: {
      model: {
        format: 'OpenAI'
        name: modelName
        version: modelVersion
      }
    }
    sku: {
      name: deploymentType
      capacity: capacity
    }    
  }

  resource aiservice_o3_deep_research 'deployments@2025-06-01' = {
    name: researchmodelName
    sku: {
      name: 'GlobalStandard'
      capacity: 250
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: researchmodelName
        version: researchmodelVersion
      }
      versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
      currentCapacity: 250
      raiPolicyName: 'Microsoft.DefaultV2'
    }
  dependsOn: [
      deploy
    ]
}
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
name: aiFoundryProjectName
parent: aiFoundry
location: location
identity: {
  type: 'SystemAssigned'
}
properties: {}
}

resource keyVault 'Microsoft.KeyVault/vaults@2024-12-01-preview' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: 'standard'
      family: 'A'
    }
    accessPolicies: []  // (could add policies for hub identity after hub created)
    publicNetworkAccess: 'Enabled'
  }
}


resource bingAccount 'Microsoft.Bing/accounts@2020-06-10' = {
  name: bingsearch
  location: 'global'
  kind: 'Bing.Grounding'
  sku: {
    name: 'G1'
  }
  }

// Bing Search Connection for AI Foundry Hub
// Since AI Foundry Hub uses Cognitive Services, we'll create the connection using a direct approach

// Create a connection resource directly under the AI Foundry project
resource bingSearchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: bingsearchconnection
  parent: aiProject
  properties: {
    category: 'ApiKey'
    target: 'https://api.bing.microsoft.com/' 
    authType: 'ApiKey'
    isSharedToAll: true
    useWorkspaceManagedIdentity: false
    
    metadata: {
      ApiType: 'Azure'
      ResourceId: bingAccount.id
      SubscriptionKey: bingAccount.listKeys().key1
    }
    credentials: {
      key: bingAccount.listKeys().key1
    }
  }
}

// Output the connection information for reference
output bingConnectionName string = bingSearchConnection.name
output bingConnectionId string = bingSearchConnection.id

output projconnstring string = '${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${projectName}'
output aiagentmodelname string = deploymentName
output projectName string = aiProject.name
output BING_RESOURCE_NAME string = bingSearchConnection.name
output DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME string = researchmodelName
output MODEL_DEPLOYMENT_NAME string = modelName
output aiFoundryName string = aiFoundryName
output aiFoundryProjectName string = aiFoundryProjectName
