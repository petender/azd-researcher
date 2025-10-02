import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from dotenv import load_dotenv
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage
from azure.identity.aio import DefaultAzureCredential

# Async blob client
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
from azure.core.exceptions import ResourceExistsError

# Load environment variables from .env file
load_dotenv()

# Ensure console output is UTF-8 (avoids UnicodeEncodeError on Windows consoles)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
                sys.stdout.buffer.write(b'\n')
                sys.stdout.buffer.flush()
                return
        except Exception:
            pass
        print(text.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))


# Global counter for intermediate files
intermediate_file_counter = 0


async def upload_text_to_blob(content: str, container_name: str, blob_name: str) -> None:
    """
    Upload the given text content to Azure Blob Storage asynchronously.
    Accepts either AZURE_STORAGE_CONNECTION_STRING or (AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY).
    """
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

    if not conn_str:
        if account_name and account_key:
            conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        else:
            print("Azure Storage credentials not found in environment. Skipping upload.")
            return

    blob_service_client = BlobServiceClient.from_connection_string(conn_str)

    async with blob_service_client:
        container_client = blob_service_client.get_container_client(container_name)
        try:
            await container_client.create_container()
        except ResourceExistsError:
            # container already exists
            pass
        except Exception:
            # Some services may raise different exceptions when container exists; ignore common 'already exists' errors
            pass

        blob_client = container_client.get_blob_client(blob_name)
        data = content.encode("utf-8")
        content_settings = ContentSettings(content_type="text/markdown; charset=utf-8")
        await blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
        print(f"Uploaded '{blob_name}' to container '{container_name}'.")


def create_research_summary(
    message: ThreadMessage,
    filename: str = "research_summary.md",
    title: str = "Deep Research Summary",
    is_intermediate: bool = False,
) -> Tuple[str, str]:
    """
    Build markdown summary content in-memory and return (filename, content).
    Does NOT write to local filesystem.
    """
    if not message:
        print("No message content provided, cannot create research summary.")
        return "", ""

    header = f"# {title}\n\n"
    if is_intermediate:
        header += f"*Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}*\n\n---\n\n"

    text_summary = "\n\n".join([t.text.value.strip() for t in message.text_messages]) if message.text_messages else ""

    references = ""
    if message.url_citation_annotations:
        references = "\n\n## References\n"
        seen_urls = set()
        for ann in message.url_citation_annotations:
            url = ann.url_citation.url
            title_ann = ann.url_citation.title or url
            if url not in seen_urls:
                references += f"- [{title_ann}]({url})\n"
                seen_urls.add(url)

    content = header + text_summary + references
    print(f"{'Intermediate' if is_intermediate else 'Final'} research summary generated for '{filename}'.")
    return filename, content


async def fetch_and_save_agent_response(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
    save_intermediate: bool = True,
    container_name: Optional[str] = None,
    blob_folder: Optional[str] = None,
    intermediate_files: Optional[List[Tuple[str, str]]] = None,
) -> Optional[str]:
    """
    Poll for the last agent message in the thread. If new, optionally generate in-memory
    intermediate content and upload to blob storage under the given folder (blob_folder).
    Returns updated last_message_id.
    """
    global intermediate_file_counter
    response = await agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )

    if not response or response.id == last_message_id:
        return last_message_id

    safe_print("\nAgent response:")
    safe_print("\n".join(t.text.value for t in response.text_messages))

    # Print citation annotations (if any)
    for ann in response.url_citation_annotations:
        safe_print(f"URL Citation: [{ann.url_citation.title}]({ann.url_citation.url})")

    # Save intermediate response in-memory and upload if requested
    if save_intermediate and response.text_messages:
        intermediate_file_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        intermediate_filename = f"research_step_{intermediate_file_counter:02d}_{timestamp}.md"

        filename, content = create_research_summary(
            response,
            filename=intermediate_filename,
            title=f"Research Step {intermediate_file_counter}",
            is_intermediate=True,
        )

        if intermediate_files is not None:
            intermediate_files.append((filename, content))

        # Upload to blob if container specified; put inside blob_folder if provided
        if container_name:
            try:
                blob_name = f"{blob_folder}/{intermediate_filename}" if blob_folder else intermediate_filename
                await upload_text_to_blob(content, container_name, blob_name)
            except Exception as ex:
                print(f"Failed to upload intermediate file '{intermediate_filename}': {ex}")

    return response.id


async def create_consolidated_summary(
    intermediate_files: List[Tuple[str, str]],
    container_name: Optional[str] = None,
    blob_folder: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Create a final consolidated summary from all intermediate contents and optionally upload to blob under blob_folder."""
    if not intermediate_files:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    consolidated_filename = f"consolidated_research_summary_{timestamp}.md"

    parts: List[str] = []
    parts.append("# Consolidated Deep Research Summary\n\n")
    parts.append(f"*Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}*\n\n")
    parts.append("This document consolidates all research steps performed during the deep research process.\n\n")
    parts.append("---\n\n")

    # Table of contents
    parts.append("## Table of Contents\n\n")
    for i, (filename, _) in enumerate(intermediate_files, 1):
        step_name = Path(filename).stem.replace("_", " ").title()
        anchor = step_name.lower().replace(" ", "-")
        parts.append(f"{i}. [{step_name}](#{anchor})\n")
    parts.append("\n---\n\n")

    # Include content from each intermediate (remove their top-level title to avoid duplication)
    for filename, filecontent in intermediate_files:
        step_title = Path(filename).stem.replace("_", " ").title()
        parts.append(f"## {step_title}\n\n")
        lines = filecontent.split("\n")
        if lines and lines[0].startswith("#"):
            body = "\n".join(lines[1:]).strip()
        else:
            body = filecontent
        parts.append(body + "\n\n---\n\n")

    consolidated_content = "".join(parts)
    print(f"Consolidated research summary generated as '{consolidated_filename}' (in-memory).")

    # Upload consolidated summary if requested
    if container_name:
        try:
            blob_name = f"{blob_folder}/{consolidated_filename}" if blob_folder else consolidated_filename
            await upload_text_to_blob(consolidated_content, container_name, blob_name)
        except Exception as ex:
            print(f"Failed to upload consolidated summary '{consolidated_filename}': {ex}")

    return consolidated_filename, consolidated_content


def get_default_research_content() -> str:
    """Return the default research content if no custom content is provided."""
    return (
        "The Researcher Agent is a deep reasoning AI assistant designed to automate the synthesis of external industry research on IT skills for AI Transformation and internal Microsoft product strategy and marketing insights. Its primary function is to generate insights for the leadership team that highlight key trends in IT Skills and Learning & Development—sourced from organizations like IDC, Forrester, Gartner, Deloitte, and WEF and learning platforms like LinkedIn Learning and Coursera—and contextualize them against Microsoft's evolving product strategy to strengthen WWL's strategy. Its goal is expose skilling barriers that are preventing our customers from being more successful with our products more quickly. To clarify, I want you to: "
        "1. Provide other reputable resources to provide us with more insights for our research, apart from the ones listed earlier as an example. "
        "2. Analyze how different industry sectors - sometimes referred to as verticals - are faring with the demand "
        "3. Analyze how these skills align with Microsoft's current product strategy and marketing initiatives. "
        "4. Analyze how the Microsoft skilling offering compares to our main competitors such as AWS and Google. "
        "5. Focusing on the Voice of the Customer, what suggestions would you have for the leadership team to improve our skilling offerings? "
        "6. Summarize your findings in a concise report that can be shared with the leadership team. The leadership team is most interested in strategies they should stop, start and continue. "
        "7. Provide citations for all sources used in your research, including links to relevant articles, reports, and studies. "
        "8. Ensure that your report is well-structured, easy to read, and visually appealing, with appropriate headings, bullet points, and visuals where necessary. "
        "don't prompt for any additional information or clarification, just start the research process."
    )


async def run_research(research_content: str) -> None:
    """
    Run the deep research process with the provided research content.
    This function contains the main research logic, separated from argument parsing.
    """
    global intermediate_file_counter
    intermediate_file_counter = 0  # Reset counter
    intermediate_files: List[Tuple[str, str]] = []  # Track intermediate files as (filename, content) tuples

    # Use async context managers for credential and project client to ensure sessions are closed
    async with DefaultAzureCredential() as credential:
        async with AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=credential) as project_client:

            bing_connection = await project_client.connections.get(name=os.environ["BING_RESOURCE_NAME"])

            # Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
            deep_research_tool = DeepResearchTool(
                bing_grounding_connection_id=bing_connection.id,
                deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
            )

            # Blob settings
            container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "research-summaries")
            init_blob_name = os.getenv("AZURE_INIT_BLOB_NAME", "research_summary_inprogress.md")

            # Create a run-specific folder (virtual folder) using UTC timestamp to keep run outputs grouped
            run_folder = f"research_run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

            # Optionally append a timestamp to the placeholder name (local filename); the blob path will include the run_folder
            if os.getenv("AZURE_INIT_BLOB_ADD_TIMESTAMP", "false").lower() in ("1", "true", "yes"):
                init_blob_name = f"{Path(init_blob_name).stem}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"

            placeholder_content = (
                f"# Research Summary (In progress)\n\n"
                f"This placeholder was created on {datetime.now(timezone.utc).isoformat()}Z to reserve a blob for the researcher run.\n\n"
                f"Run folder: {run_folder}\n\n"
                f"You can overwrite this blob when the run completes.\n"
            )

            overwrite_placeholder = os.getenv("AZURE_OVERWRITE_PLACEHOLDER", "false").lower() in ("1", "true", "yes")
            placeholder_blob_name = init_blob_name if overwrite_placeholder else None

            agents_client = project_client.agents

            # Create placeholder blob before running researcher (best-effort) inside the run_folder
            try:
                placeholder_blob_path = f"{run_folder}/{init_blob_name}"
                await upload_text_to_blob(placeholder_content, container_name, placeholder_blob_path)
                print(f"Placeholder blob created: {placeholder_blob_path} in container {container_name}")
            except Exception as ex:
                print(f"Failed to create placeholder blob: {ex}")

            # Create a new agent that has the Deep Research tool attached.
            agent = await agents_client.create_agent(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                name="Agent530",
                instructions="You are a helpful Agent that assists in researching topics as requested by the user.",
                tools=deep_research_tool.definitions,
            )
            print(f"Created agent, ID: {agent.id}")

            # Create thread for communication
            thread = await agents_client.threads.create()
            print(f"Created thread, ID: {thread.id}")

            # Create message to thread
            message = await agents_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=(
                    "The Researcher Agent is a deep reasoning AI assistant designed to automate the synthesis of external industry research on IT skills for AI Transformation and internal Microsoft product strategy and marketing insights. Its primary function is to generate insights for the leadership team that highlight key trends in IT Skills and Learning &Development—sourced from organizations like IDC, Forrester, Gartner, Deloitte, and WEF and learning platforms like LinkedIn Learning and Coursera—and contextualize them against Microsoft’s evolving product strategy to strengthen WWL's strategy. Its goal is expose skilling barriers that are preventing our customers from being more successful with our products more quickly. To clarify, I want you to:  "
                    "1. Provide other reputable resources to provide us with more insights for our research, apart from the ones listed earlier as an example. "
                    "2. Analyze how different industry sectors - sometimes referred to as verticals - are faring with the demand"
                    "3. Analyze how these skills align with Microsoft’s current product strategy and marketing initiatives."
                    "4. Analyze how the Microsoft skilling offering compares to our main competitors such as AWS and Google."
                    "5. Focusing on the Voice of the Customer, what suggestions would you have for the leadership team to improve our skilling offerings?"
                    "6. Summarize your findings in a concise report that can be shared with the leadership team. The leadership team is most interested in strategies they should stop, start and continue. "
                    "7. Provide citations for all sources used in your research, including links to relevant articles, reports, and studies. "
                    "8. Ensure that your report is well-structured, easy to read, and visually appealing, with appropriate headings, bullet points, and visuals where necessary. "
                    "don't prompt for any additional information or clarification, just start the research process."
                ),
            )
            print(f"Created message, ID: {message.id}")

            print("Start processing the message... this may take a few minutes to finish. Be patient!")
            # Poll the run as long as run status is queued or in progress
            run = await agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
            last_message_id: Optional[str] = None

            while run.status in ("queued", "in_progress"):
                await asyncio.sleep(1)
                run = await agents_client.runs.get(thread_id=thread.id, run_id=run.id)

                previous_last_message_id = last_message_id
                last_message_id = await fetch_and_save_agent_response(
                    thread_id=thread.id,
                    agents_client=agents_client,
                    last_message_id=last_message_id,
                    save_intermediate=True,
                    container_name=container_name,
                    blob_folder=run_folder,
                    intermediate_files=intermediate_files,
                )

                # Print run status
                print(f"Run status: {run.status}")

            print(f"Run finished with status: {run.status}, ID: {run.id}")

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")

            # Fetch the final message from the agent in the thread and create a research summary
            final_message = await agents_client.messages.get_last_message_by_role(
                thread_id=thread.id, role=MessageRole.AGENT
            )
            if final_message:
                # Create final summary in-memory
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                final_filename = f"final_research_summary_{timestamp}.md"
                filename, content = create_research_summary(
                    final_message,
                    filename=final_filename,
                    title="Final Deep Research Summary",
                    is_intermediate=False,
                )

                # If overwrite placeholder was requested, reuse that blob name; otherwise create a timestamped name in run_folder
                if placeholder_blob_name:
                    blob_name = f"{run_folder}/{placeholder_blob_name}"
                else:
                    base_name = Path(filename).stem if filename else "research_summary"
                    blob_name = f"{run_folder}/{base_name}_{timestamp}.md"

                try:
                    await upload_text_to_blob(content, container_name, blob_name)
                except Exception as ex:
                    print(f"Failed to upload final summary to Azure Blob Storage: {ex}")

                # Create consolidated summary and upload if there are intermediate files
                if intermediate_files:
                    try:
                        await create_consolidated_summary(intermediate_files, container_name=container_name, blob_folder=run_folder)
                    except Exception as ex:
                        print(f"Failed to create/upload consolidated summary: {ex}")

            # Clean-up and delete the agent once the run is finished.
            # NOTE: Comment out this line if you plan to reuse the agent later.
            await agents_client.delete_agent(agent.id)
            print("Deleted agent")


async def main() -> None:
    """Main entry point - handles command line arguments and calls run_research."""
    research_content = get_default_research_content()
    
    # Check if research content was provided as a command line argument
    if len(sys.argv) > 1:
        # Join all arguments after the script name as research content
        research_content = " ".join(sys.argv[1:])
        print(f"Using provided research content: {research_content[:100]}{'...' if len(research_content) > 100 else ''}")
    else:
        print("Using default research content.")
    
    await run_research(research_content)


if __name__ == "__main__":
    asyncio.run(main())
