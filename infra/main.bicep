targetScope = 'subscription'

@minLength(1)
@maxLength(10)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string


@description('Resource group name')
param resourceGroupName string = ''

@minLength(1)
@description('Primary location for all resources')
param location string

param modelName string = 'gpt-4o'
param modelVersion string = '2024-11-20'
param researchmodelName string = 'o3-deep-research'
param researchmodelVersion string = '2025-06-26'
param capacity int = 50 // 1000 K TPM = 1 M TPM
param deploymentType string = 'GlobalStandard'
param bingsearch string = 'deepresearchbingsearch'
param bingsearchconnection string = 'bing-grounding-connection'

var abbrs = loadJsonContent('./abbreviations.json')
var uniqueSuffix = substring(uniqueString(subscription().id, environmentName), 1, 5)
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Tags that should be applied to all resources.
// 
// Note that 'azd-service-name' tags should be applied separately to service host resources.
// Example usage:
//   tags: union(tags, { 'azd-service-name': <service name in azure.yaml> })
var tags = {
  'azd-env-name': environmentName
  'SecurityControl': 'Ignore'
}

@description('App Service resource name')
param appServiceName string = ''
@description('AppServerFarm service resource name')
param appServerFarmName string = ''
param aiFoundryName string = ''
param aiFoundryProjectName string = ''

var names = {
  resourceGroupName: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  appServiceName: !empty(appServiceName) ? appServiceName : '${abbrs.webSitesAppService}${environmentName}-${uniqueSuffix}'
  appServerFarmName: !empty(appServerFarmName) ? appServerFarmName :'${abbrs.webServerFarms}${environmentName}-${uniqueSuffix}'
  aiFoundryName: !empty(aiFoundryName) ? aiFoundryName : '${abbrs.aifoundryservices}${environmentName}-${uniqueSuffix}'
  aiFoundryProjectName: !empty(aiFoundryProjectName) ? aiFoundryProjectName : '${abbrs.aifoundryproject}${environmentName}-${uniqueSuffix}'
}


resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module m_storage 'modules/storage.bicep' = {
  name: '${environmentName}storage'
  scope: rg
  params: {
    environmentName: environmentName
    
  }
}

module m_appService 'modules/webapp.bicep' = {
  name: '${environmentName}appService'
  scope: rg
  
  params: {
    location: location
    appServiceName: names.appServiceName
    appServerFarmName: names.appServerFarmName
    storageAccountName: m_storage.outputs.storageAccountName // Pass storage account name
    tags: tags
    projectEndpoint: 'https://${m_aiproj.outputs.aiFoundryName}.services.ai.azure.com/api/projects/${m_aiproj.outputs.aiFoundryProjectName}'
    storageAccountKey: m_storage.outputs.storageAccountKey // Pass storage account key
    researchmodelName: researchmodelName
    modelName: modelName
    bingsearch: bingsearch
    bingsearchConnection: bingsearchconnection
  }
}

module m_aiproj 'modules/aiproj.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    instanceId: 'aiproj${resourceToken}'
    modelName: modelName
    modelVersion: modelVersion
    researchmodelName: researchmodelName
    researchmodelVersion: researchmodelVersion
    deploymentName: modelName
    capacity: capacity
    deploymentType: deploymentType
    location: location
    bingsearch: bingsearch
    aiFoundryName: names.aiFoundryName
    aiFoundryProjectName: names.aiFoundryProjectName
    bingsearchconnection: bingsearchconnection

  }
}



// Add outputs from the deployment here, if needed.
//
// This allows the outputs to be referenced by other bicep deployments in the deployment pipeline,
// or by the local machine as a way to reference created resources in Azure for local development.
// Secrets should not be added here.
//
// Outputs are automatically saved in the local azd environment .env file.
// To see these outputs, run `azd env get-values`,  or `azd env get-values --output json` for json output.

output AZURE_STORAGE_ACCOUNT_NAME string = m_storage.outputs.storageAccountName
@secure()
//output AZURE_STORAGE_ACCOUNT_KEY string = m_storage.outputs.storageAccountKey
output APP_SERVICE_NAME string = names.appServiceName
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_AI_AGENT_PROJECT_CONNECTION_STRING string = m_aiproj.outputs.projconnstring
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = m_aiproj.outputs.aiagentmodelname
output BING_RESOURCE_NAME string = m_aiproj.outputs.BING_RESOURCE_NAME
output DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME string = m_aiproj.outputs.DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME
output MODEL_DEPLOYMENT_NAME string = m_aiproj.outputs.MODEL_DEPLOYMENT_NAME
output PROJECT_NAME string = m_aiproj.outputs.projectName
output AI_SERVICE_NAME string = m_aiproj.outputs.aiFoundryName
output PROJECT_ENDPOINT string = 'https://${m_aiproj.outputs.aiFoundryName}.services.ai.azure.com/api/projects/${m_aiproj.outputs.projectName}'
output AZURE_STORAGE_ACCOUNT_KEY string = m_storage.outputs.storageAccountKey
