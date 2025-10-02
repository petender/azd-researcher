# AZD-Researcher with Azure AI Foundry Agent Service, Bing Search Grounding and OpenAI Deep-Research LLM 

This repo contains a demo scenario for Azure AI Foundry Agent Service, using the OpenAI deep-research LLM and Bing Search Grounding service. 

This demo scenario is one of the several demos available in the Open Source [Trainer-Demo-Deploy](https://aka.ms/trainer-demo-deploy) catalog. 

Once the Azure resources got deployed, you can trigger the Research process from a Python Flask web application. Select any of the suggested business cases to research, or rewrite with your own use case. 

From there, the full research process include the intermediate Bing Search Grounding reasoning steps are written to individual MarkDown files, which can be downloaded from the web page, as well as getting stored in the deployed Azure Blob Storage Account.

**OpenAI's description of Deep Research LLM:**

*Deep research is OpenAI's next agent that can do work for you independently—you give it a prompt, and ChatGPT will find, analyze, and synthesize hundreds of online sources to create a comprehensive report at the level of a research analyst. Powered by a version of the upcoming OpenAI o3 model that’s optimized for web browsing and data analysis, it leverages reasoning to search, interpret, and analyze massive amounts of text, images, and PDFs on the internet, pivoting as needed in reaction to information it encounters.*

*The ability to synthesize knowledge is a prerequisite for creating new knowledge. For this reason, deep research marks a significant step toward our broader goal of developing AGI, which we have long envisioned as capable of producing novel scientific research.*

*Deep research is built for people who do intensive knowledge work in areas like finance, science, policy, and engineering and need thorough, precise, and reliable research. It can be equally useful for discerning shoppers looking for hyper-personalized recommendations on purchases that typically require careful research, like cars, appliances, and furniture. Every output is fully documented, with clear citations and a summary of its thinking, making it easy to reference and verify the information. It is particularly effective at finding niche, non-intuitive information that would require browsing numerous websites. Deep research frees up valuable time by allowing you to offload and expedite complex, time-intensive web research with just one query.*

*Deep research independently discovers, reasons about, and consolidates insights from across the web. To accomplish this, it was trained on real-world tasks requiring browser and Python tool use, using the same reinforcement learning methods behind OpenAI o1, our first reasoning model. While o1 demonstrates impressive capabilities in coding, math, and other technical domains, many real-world challenges demand extensive context and information gathering from diverse online sources. Deep research builds on these reasoning capabilities to bridge that gap, allowing it to take on the types of problems people face in work and everyday life.*

<div style="background: lightgreen; 
            font-size: 14px; 
            color: black;
            padding: 5px; 
            border: 1px solid lightgray; 
            margin: 5px;">

**Note:** The OpenAI Researcher Large Language Model is considered a more expensive LLM. Each Research Trigger is estimated as a $10 charge on Azure Cognitive Services, and a $1 charge on Azure Bing Search service. Take this charge into account when using this demo scenario!! 
</div>

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



 