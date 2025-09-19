import requests
import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_groq import ChatGroq

# ------------------------------
# 1. Load API Keys
# ------------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")

if not GITHUB_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Missing API keys in .env file")

# ------------------------------
# 2. Fetch Latest PR Number
# ------------------------------
def get_latest_pr(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&sort=created&direction=desc"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.json()}")

    prs = response.json()
    if not prs:
        raise Exception("⚠️ No open PRs found in this repository.")

    latest_pr = prs[0]  # most recent PR
    return latest_pr["number"], latest_pr["html_url"]

# ------------------------------
# 3. Fetch PR Diff
# ------------------------------
def fetch_pr_diff(owner, repo, pr_number, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"   # ✅ Force GitHub to return diff
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Error fetching diff:", response.status_code, response.text)
        return ""

    diff = response.text

    # Debugging info
    print("📏 Diff length:", len(diff))
    if len(diff) < 50:
        print("⚠️ Warning: Diff seems too small, check if PR actually has changes.")

    # Optional: save diff locally for inspection
    with open("latest_pr.diff", "w", encoding="utf-8") as f:
        f.write(diff)

    return diff


# ------------------------------
# 4. Post Review Comment
# ------------------------------
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
# 5. Groq AI Reviewer
# ------------------------------
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=GROQ_API_KEY)
parser = StrOutputParser()

review_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior software engineer reviewing a GitHub Pull Request."),
    ("human", "Here is the diff of the PR:\n\n{diff}\n\nPlease provide a review.")
])
review_chain = review_prompt | llm | parser

# ------------------------------
# 6. Main Logic
# ------------------------------
import sys

if __name__ == "__main__":
    try:
        # --- Get owner & repo from command-line arguments ---
        if len(sys.argv) < 3:
            print("⚠️ Usage: python version_1.py <owner> <repo>")
            sys.exit(1)

        owner = sys.argv[1]   # e.g. "Yash-Panchal-094"
        repo = sys.argv[2]    # e.g. "Text-Analyzer"

        pr_number, pr_url = get_latest_pr(owner, repo, GITHUB_TOKEN)
        print(f"✅ Found latest PR: {pr_url}")

        diff_text = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
        print("✅ Diff fetched. Sending to AI reviewer...")

        review = review_chain.invoke({"diff": diff_text[:4000]})
        print("=== AI REVIEW RESULT ===")
        print(review)
        print("========================")

        comment = post_review_comment(owner, repo, pr_number, GITHUB_TOKEN, review)
        print(f"✅ Review posted: {comment['html_url']}")

    except Exception as e:
        print("Error:", str(e))

