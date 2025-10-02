# AZD-Researcher with Azure AI Foundry Agent Service, Bing Search Grounding and OpenAI Deep-Research LLM 

This repo contains a demo scenario for Azure AI Foundry Agent Service, using the OpenAI deep-research LLM and Bing Search Grounding service. 

This demo scenario is one of the several demos available in the Open Source [Trainer-Demo-Deploy](https://aka.ms/trainer-demo-deploy) catalog. 

Once the Azure resources got deployed, you can trigger the Research process from a Python Flask web application. Select any of the suggested business cases to research, or rewrite with your own use case. 

From there, the full research process include the intermediate Bing Search Grounding reasoning steps are written to individual MarkDown files, which can be downloaded from the web page, as well as getting stored in the deployed Azure Blob Storage Account.

## ⬇️ Installation
- [Azure Developer CLI - AZD](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
    - When installing AZD, the above the following tools will be installed on your machine as well, if not already installed:
        - [GitHub CLI](https://cli.github.com)
        - [Bicep CLI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/install)
    - You need Owner or Contributor access permissions to an Azure Subscription to  deploy the scenario.

## 🚀 Cloning this demo scenario in 4 steps:

1. Create a new folder on your machine.
```
mkdir tdd-azd-researcher
```
2. Next, navigate to the new folder.
```
cd tdd-azd-researcher
```
3. Next, run `azd init` to initialize the deployment.
```
azd init -t petender/tdd-azd-researcher
```
4. Run the scenario deployment. Provide a short name for the azd environment; you will get asked for your Azure subscription and Azure Resource Region. 
```
azd up
```

Note: Not all resources in this scenario are available across all Azure regions. If deployment fails because of this, create a new azd environment, select a different region for the resources and run 'azd up'' again.

5. Wait for the deployment of both the Azure resources and corresponding Web Application to complete successfully.

6. Navigate to the deployed Web App URL to kick off the Research process.

7. Clean up the scenario when no longer needed
```
azd down --purge --force
```



 