import os
import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_groq import ChatGroq

load_dotenv()

# 🔑 Load secrets from GitHub Actions
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

repo_full = os.getenv("GITHUB_REPOSITORY")  # e.g., "Yash-Panchal-094/Text-Analyzer"
owner, repo = repo_full.split("/")
pr_number = os.getenv("PR_NUMBER")

if not (GITHUB_TOKEN and GROQ_API_KEY and pr_number):
    raise ValueError("❌ Missing required environment variables")

# --- GitHub API helpers ---
def fetch_pr_diff(owner, repo, pr_number, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    diff_url = response.json()["diff_url"]
    diff = requests.get(diff_url, headers=headers).text
    return diff

def post_review_comment(owner, repo, pr_number, token, review_body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}"}
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# --- LLM setup ---
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=GROQ_API_KEY
)
parser = StrOutputParser()

review_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior engineer reviewing GitHub PRs."),
    ("human", "Here is the PR diff:\n\n{diff}\n\nWrite a constructive review.")
])
review_chain = review_prompt | llm | parser

# --- Run bot ---
if __name__ == "__main__":
    diff = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
    review = review_chain.invoke({"diff": diff[:4000]})  # limit diff size if huge
    comment = post_review_comment(owner, repo, pr_number, GITHUB_TOKEN, review)
    print(f"✅ Review posted: {comment['html_url']}")
