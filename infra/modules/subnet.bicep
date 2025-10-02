param location string
param tags object
param appServiceName string

param forceUpdateTag string = utcNow()



var vnetName = '${appServiceName}vnet'
var vnetAddressPrefix = '10.0.0.0/16'
var subnetName = '${appServiceName}sn'
var subnetAddressPrefix = '10.0.0.0/24'


resource vnet 'Microsoft.Network/virtualNetworks@2020-06-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: subnetName
        properties: {
          addressPrefix: subnetAddressPrefix
          networkSecurityGroup: {
            id: resourceId('Microsoft.Network/networkSecurityGroups', '${appServiceName}nsg')
          }
          serviceEndpoints: [
            {
              service: 'Microsoft.CognitiveServices'
              locations: [
                '*'
              ]
            }
          ]
          delegations: [
            {
              name: 'delegation'
              id: resourceId('Microsoft.Network/virtualNetworks/subnets/delegations', vnetName, subnetName, 'delegation')
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
    ]
    
  }
  tags: tags
}   

// add resource for nsg
resource nsg 'Microsoft.Network/networkSecurityGroups@2020-06-01' = {
  name: '${appServiceName}nsg'
  location: location
  properties: {
    securityRules: [
      
    ]
  }
}

/*
resource subnet 'Microsoft.Network/virtualNetworks/subnets@2020-06-01' = {
  name: subnetName
  parent: vnet
  properties: {
    addressPrefix: subnetAddressPrefix
    networkSecurityGroup: {
      id: resourceId('Microsoft.Network/networkSecurityGroups', nsg.name)}

    serviceEndpoints: [
      {
        service: 'Microsoft.CognitiveServices'
        locations: [
          '*'
        ]
      }
    ]
    delegations: [
      {
        name: 'delegation'
        id: resourceId('Microsoft.Network/virtualNetworks/subnets/delegations', vnetName, subnetName, 'delegation')
        properties: {
          serviceName: 'Microsoft.Web/serverFarms'
        }
        
      }
    
    ]
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Disabled'

  }
  
}
*/










