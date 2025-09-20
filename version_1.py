import os
import requests
from github import Github

# Load secrets from env
gh_token = os.getenv("GH_TOKEN")
repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("PR_NUMBER")

# Authenticate with GitHub
g = Github(gh_token)
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# 🔧 Get diff using GitHub REST API (since PyGithub doesn't provide .diff())
diff_url = pr.url + ".diff"
headers = {"Authorization": f"token {gh_token}"}
diff_response = requests.get(diff_url, headers=headers)

if diff_response.status_code == 200:
    diff_text = diff_response.text
else:
    diff_text = f"⚠️ Failed to fetch diff (status {diff_response.status_code})"

print("Fetched diff successfully!")

# 🧠 Send diff to Gemini API
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")
prompt = f"Review the following Pull Request diff and provide a concise code review:\n\n{diff_text}"
response = model.generate_content(prompt)

review_comment = response.text
print("Generated review:\n", review_comment)

# 💬 Post review as PR comment
pr.create_issue_comment(review_comment)
print("✅ Review posted successfully!")
