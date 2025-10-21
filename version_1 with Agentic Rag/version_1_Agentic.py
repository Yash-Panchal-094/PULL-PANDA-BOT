# version_1_agentic.py (Updated for Agentic RAG - Stricter Prompt)
import os
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path
import time
import shutil

# LangChain Agent and Core Imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool
from langchain.schema import Document

# RAG Imports
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Import local RAG loader (MUST be compatible with the new flow)
# Note: REPO_DOWNLOAD_DIR is now imported from rag_loader
from rag_loader_agentic import build_index_for_repo, assemble_context, REPO_DOWNLOAD_DIR


# ------------------------------
# 1. Load API Keys & Config
# ------------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")

if not GITHUB_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Missing API keys in .env file")


# ------------------------------
# 2. GitHub Utilities
# ------------------------------

def get_pr_number_from_args(owner, repo, token, pr_arg=None):
    """Fetches the latest open PR if no number is provided, or uses the provided number."""
    if pr_arg and pr_arg.isdigit():
        pr_number = int(pr_arg)
        # Check if the specific PR exists and is open
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Authorization": f"token {token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return pr_number, response.json()["html_url"]
        else:
            raise Exception(f"PR #{pr_number} not found or is closed.")

    # Fetch the latest open PR
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&sort=created&direction=desc"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.json()}")

    prs = response.json()
    if not prs:
        raise Exception("⚠️ No open PRs found in this repository.")
    
    latest_pr = prs[0]
    return latest_pr["number"], latest_pr["html_url"]

def fetch_pr_diff(owner, repo, pr_number, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("❌ Error fetching diff:", response.status_code, response.text)
        return ""
    return response.text

def post_review_comment(owner, repo, pr_number, token, review_body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload)
    return response.json()


# ------------------------------
# 3. Agent Tools Implementation
# ------------------------------

def get_full_file_content(file_path: str) -> str:
    """
    Reads the full content of a specific file from the locally downloaded repository 
    directory. Input path must be relative to the repository root (e.g., 'src/config.py').
    """
    # Find the single top-level directory created by the zip extraction
    repo_root = next((p for p in REPO_DOWNLOAD_DIR.iterdir() if p.is_dir()), REPO_DOWNLOAD_DIR)
    
    # Clean the path and resolve relative to the repo root
    target_path = repo_root / file_path.lstrip('/')
    
    if not target_path.exists():
        # Check if the path might be in the root directory (no subdirectory)
        if repo_root != REPO_DOWNLOAD_DIR:
             target_path = REPO_DOWNLOAD_DIR / file_path.lstrip('/')
        
        if not target_path.exists():
            return f"ERROR: File not found at local path: {file_path}. The path must be relative to the repository root."
    
    try:
        # Limit the output size to prevent overwhelming the LLM
        content = target_path.read_text(encoding="utf-8", errors="ignore")
        return f"CONTENT OF {file_path} (Truncated at 4000 chars):\n{content[:4000]}"
    except Exception as e:
        return f"ERROR: Could not read file {file_path}. Reason: {str(e)}"

# Define the tools the agent can use
def setup_agent_tools(rag_vectorstore):
    # 1. The RAG Retriever Tool (for finding chunks relevant to the diff)
    rag_retriever = rag_vectorstore.as_retriever(search_kwargs={"k": 6})

    # Custom wrapper function to ensure the output is a clean string for the agent
    def retrieve_and_format_context(query: str) -> str:
        retrieved_documents = rag_retriever.get_relevant_documents(query)
        # Use the shared assemble_context function
        return assemble_context(retrieved_documents, char_limit=4000)

    rag_tool = Tool(
        name="project_context_search",
        func=retrieve_and_format_context,
        description=(
            "Useful for finding relevant code snippets from the existing codebase (e.g., related functions, "
            "configuration values, or file structure) based on a semantic query related to the DIFF."
        )
    )

    # 2. The Full File Lookup Tool (for viewing entire files)
    file_reader_tool = Tool(
        name="full_file_reader",
        func=get_full_file_content,
        description=(
            "Useful for reading the entire contents of a known file path (e.g., 'config.json', 'src/db.py') "
            "that is mentioned in the PR diff or suggested by the project_context_search tool. "
            "Input MUST be the exact relative file path string (e.g., 'path/to/file.ext')."
        )
    )

    return [rag_tool, file_reader_tool]

# ------------------------------
# 4. Main Logic
# ------------------------------
if __name__ == "__main__":
    try:
        start_time = time.time()
        
        if len(sys.argv) < 3:
            print("Usage: python version_1_Yash.py <owner> <repo> [pr_number]")
            sys.exit(1)

        owner, repo = sys.argv[1], sys.argv[2]
        pr_arg = sys.argv[3] if len(sys.argv) > 3 else None

        # 1. Load RAG index and ensure local repo files are available
        print("📦 Building/loading RAG index and preparing local files...")
        # We rely on the index being built already, but ensure files are downloaded for the Agent tool.
        # This function is sourced from rag_loader.py
        rag_vectorstore = build_index_for_repo(owner, repo, GITHUB_TOKEN, force_rebuild=False, download_if_missing=True)
        
        # 2. Setup Agent & Tools
        tools = setup_agent_tools(rag_vectorstore)
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, api_key=GROQ_API_KEY)

        # Inside version_1_Yash.py, update the agent_system_message:

        # 3. Create the Agent Prompt
        # >>>>> THE CRITICAL CHANGE IS HERE (Enforcing Code Snippets) <<<<<
        agent_system_message = (
            "You are PULL-PANDA, a highly experienced senior software engineer specialized in code review. "
            "Your primary mission is to identify **bugs, security issues, and architectural inconsistencies**. "
            "Provide a detailed, professional review. **Crucially, for every issue or suggestion, you MUST include:**\n"
            "1. The original faulty code line/snippet from the DIFF.\n"
            "2. A suggested corrected code snippet.\n"
            "Ensure there is absolutely **NO REPETITION** of suggestions or summary points."
            "Your final output MUST be structured EXACTLY as three non-redundant sections:\n"
            "### CRITICAL ISSUES (Bugs/Security)\n"
            "List severe bugs, providing original and suggested code. If none, state 'None found.'\n\n"
            "### SUGGESTIONS (Style/Efficiency)\n"
            "List stylistic or efficiency improvements, providing original and suggested code where applicable. If none, state 'None found.'\n\n"
            "### CONCISE SUMMARY\n"
            "Provide a final, one-paragraph evaluation of the PR's overall quality and acceptance status (e.g., 'Approved with minor fixes')."
        )

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", agent_system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "Please review the following PR diff:\n\n{diff}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    # ... rest of the file ...
        
        agent = create_tool_calling_agent(llm, tools, agent_prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


        # 4. Get target PR and diff
        pr_number, pr_url = get_pr_number_from_args(owner, repo, GITHUB_TOKEN, pr_arg)
        print(f"🔸 Found target PR: {pr_url}")

        diff_text = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
        if not diff_text:
            raise Exception("No diff fetched.")
        
        # 5. Run the Agent
        print("=== 🧠 AGENTIC AI REVIEW (Using Tools) ===")
        
        review_result = agent_executor.invoke({
            "diff": diff_text,
            "chat_history": []
        })
        
        review_text = review_result["output"]
        end_time = time.time()
        
        print("\n====================================")
        print("FINAL PULL-PANDA REVIEW")
        print("====================================")
        print(f"Review Generated in {end_time - start_time:.2f} seconds.")
        print("------------------------------------")
        print(review_text)
        print("------------------------------------")


        # 6. Post review comment on PR
        comment = post_review_comment(owner, repo, pr_number, GITHUB_TOKEN, review_text)
        if "html_url" in comment:
            print(f"✅ Review posted: {comment['html_url']}")
        else:
            print(f"⚠️ Failed to post review: {comment}")

    except Exception as e:
        print(f"❌ Critical Error: {e}")