[comment]: <> (please keep all comment items at the top of the markdown file)
[comment]: <> (please do not change the ***, as well as <div> placeholders for Note and Tip layout)
[comment]: <> (please keep the ### 1. and 2. titles as is for consistency across all demoguides)
[comment]: <> (section 1 provides a bullet list of resources + clarifying screenshots of the key resources details)
[comment]: <> (section 2 provides summarized step-by-step instructions on what to demo)


[comment]: <> (this is the section for the Note: item; please do not make any changes here)
***
### Azure AI Foundry Agent Service with Bing Search Grounding and OpenAI Deep Research LLM

This scenario deploys an Azure AI Foundry Project architecture, using Azure AI Foundry Agent Service, OpenAI Deep-Research LLM and Bing Search Grounding. The research web app offers 2 predefined use cases to perform research on, but you can also provide your own description for the use case. Once the process kicks off, it shows real-time processing logs on the web app, as well as saving each iteration of the research reasoning in an individual Markdown file. 

Once the research Agent task completes, it compiles a summary MarkDown document with the observations and results of the research. 

All process and summary files can be downloaded from the webapp, but are also stored in an Azure Storage Account Blob Storage.

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/DeepResearcherArchitecture.png" alt="AI Foundry Agent Service with Bing Search and OpenAI Deep-Researcher LLM Architecture Diagram" style="width:70%;">
<br></br>

<div style="background: lightgreen; 
            font-size: 14px; 
            color: black;
            padding: 5px; 
            border: 1px solid lightgray; 
            margin: 5px;">

**Note:** Below demo steps should be used **as a guideline** for doing your own demos. Please consider contributing to add additional demo steps.
</div>

<div style="background: purple; 
            font-size: 14px; 
            color: white;
            padding: 5px; 
            border: 1px solid lightgray; 
            margin: 5px;">

**Tip:** Start from any of the 2 predefined use cases as an example, but also consider adding your own use cases as alternative, or ask input from your learners. 
</div>

[comment]: <> (this is the section for the Tip: item; consider adding a Tip, or remove the section between <div> and </div> if there is no tip)

***
### 1. What Resources are getting deployed

The following resources are getting deployed:

* RG-<azd-env-name> : The Resource Group using the AZD env name you specified
* aif-%uniquestring% : Azure AI Foundry Service Resource
* aifp-%uniquestring% : Azure AI Foundry Project with Agent Service 
* kvaiproj%uniquestring%: Key Vault Resource
* storage%uniquestring%: Storage Account which is required by AI Foundry
* app-%uniquestring%: App Service hosting the Python Flask web app
* deepresearchbingresearch: Bing Search Grounding Service
* plan-%uniquestring%: App Service Plan for the web app (S1 Sku)

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/ResourceGroup_Overview.png" alt="AI Foundry Researcher Resource Group" style="width:70%;">
<br></br>


### 2. What can I demo from this scenario after deployment

#### Azure AI Foundry Resources
1. Assuming you already walked the learner through the foundational concepts of Azure AI Foundry, the demo starts from navigating to the Foundry Resources in the [Azure AI Foundry portal](https://ai.azure.com/AllResources) and **selecting the aifp-%uniquestring% Foundry Project**.

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/AIFoundry_Project.png" alt="AI Foundry Project" style="width:70%;">
<br></br>

1. Navigate to the **Agents** section in the left menu, and select **Agent<000>**.

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/AIFoundry_Agent.png" alt="AI Foundry Agent" style="width:70%;">
<br></br>

Note: this Agent is NOT the one being used by the Deep_Research, but a required component in the Bicep template for Agent Service. 

1. Navigate to the deployed Azure App Service within the Researcher RG, and open the URL.

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/WebApp_HomePage.png" alt="Research Web App" style="width:70%;">
<br></br>

There are 2 prebuilt scenarios, **Technology Trends** and **Market Research**. You can modify either of them, or even completely overwrite the text box with your own research project details. 

Once done, click the **Start Research** button.

1. After about 30-60 seconds, the real-time log starts filling (the black box), showing different output information related to the actual research in progress. There will be citations from Bing Search webresults, as well as more detailed "In Progress" updates for research tasks taking more time.

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/Research_Running.png" alt="Research In Progress" style="width:70%;">
<br></br>

1. Researcher goes through different iterations, ranging from 1 to sometimes more than 80, depending on the level of detail described in the use case. For each iteration, a **markdown** file is created in Azure Blob Storage, and downloadable from the Web Page itself for review. 

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/MarkDown_Iterations.png" alt="Research Iteration result in MarkDown" style="width:70%;">
<br></br>

Opening a MarkDown file, shows you the details of the Step and what it is Researching on:

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/MarkDown_Iterations_Details.png" alt="Research Iteration result in MarkDown" style="width:70%;">
<br></br>

<div style="background: purple; 
            font-size: 14px; 
            color: white;
            padding: 5px; 
            border: 1px solid lightgray; 
            margin: 5px;">

**Tip:** While the Research process is ongoing, navigate back to the **AI Foundry Portal**, and check the **Agent Threads Status**  
</div>

1. From the AI Foundry Agents blade, notice a **new Agent<000>** got added to the list, identified by **deep_research** tool.  Select the **My threads** tab, which shows the different Thread IDs for each research step:

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/AIFoundry_Agent_Threads.png" alt="AI Foundry Agent Threads" style="width:70%;">
<br></br>

The initial "User Message", holding the full description of the use case you selected/provided, as well as the "Agent Response" messages are all linked to the same Thread ID. It's each Agent Response message we capture in the Iteration/Step MarkDown file.

1. Switch back to the Web App, and wait for the **Research process status** showing **Completed**. Below the logging view, notice 2 additional MarkDown files:

- consolidated_research_summary_<date_time>.md
- final_research_summary_<date_time>.md

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/Research_Completed.png" alt="Research Process Completed" style="width:70%;">
<br></br>

1. The **Consolidated Research Summary** is exactly what you can expect, a consolidation of all the Research Steps performed, including the synthesis of the research, as well as any additional Bing Search web URLs used as a source. 

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/Consolidated_Research.png" alt="Consolidated Research" style="width:70%;">
<br></br>

1. The **Final Research Summary** is a detailed report about the research, compiled using the GPT 4o Large Language Model which got deployed as part of the scenario. 

<img src="https://raw.githubusercontent.com/petender/azd-researcher/refs/heads/main/demoguide/Final_Deep_Research.png" alt="Final Research Summary Report" style="width:70%;">
<br></br>

1. One last time, navigate back to the **AI Foundry Agent Service**, and notice the **Agent<000>** which showed up during the Research process, is no longer there, neither are the Threads. Know that the Agent deletion is not happening automatically, but rather triggered from the Python Agent SDK 

```
# Delete the agent when done
project_client.agents.delete_agent(agent.id)
```

[comment]: <> (this is the closing section of the demo steps. Please do not change anything here to keep the layout consistant with the other demoguides.)
<br></br>
***
<div style="background: lightgray; 
            font-size: 14px; 
            color: black;
            padding: 5px; 
            border: 1px solid lightgray; 
            margin: 5px;">

**Note:** This is the end of the current demo guide instructions.
</div>




