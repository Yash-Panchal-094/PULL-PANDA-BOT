import os
import google.generativeai as genai
from github import Github

# 🔑 Configure Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")  # or gemini-1.5-pro for better quality

# 🔑 GitHub authentication
app_id = os.environ["APP_ID"]
installation_id = os.environ["INSTALLATION_ID"]
private_key = os.environ["PRIVATE_KEY"]

# Personal Access Token (or GitHub App token if you're signing JWT)
gh_token = os.environ["GH_TOKEN"]
g = Github(gh_token)
repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
pr_number = int(os.environ["PR_NUMBER"])
pr = repo.get_pull(pr_number)

# Extract PR diff
diff = pr.diff()

# Ask Gemini for a review
prompt = f"Review the following GitHub Pull Request diff and provide feedback:\n\n{diff[:4000]}"
response = model.generate_content(prompt)

review_text = response.text if response and response.text else "⚠️ No review generated."

# Post comment on PR
pr.create_issue_comment(review_text)
print("✅ Review posted successfully.")
