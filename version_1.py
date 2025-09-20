import os
import jwt
import time
import requests
from github import Github, Auth
from google import genai
from google.genai.types import Content, Part

# ====== Load secrets ======
APP_ID = os.environ["APP_ID"]
INSTALLATION_ID = os.environ["INSTALLATION_ID"]
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# ====== Step 1: Create JWT for App authentication ======
def generate_jwt(app_id, private_key):
    payload = {
        "iat": int(time.time()) - 60,
        "exp": int(time.time()) + (10 * 60),
        "iss": app_id
    }
    return jwt.encode(payload, private_key, algorithm="RS256")

jwt_token = generate_jwt(APP_ID, PRIVATE_KEY)

# ====== Step 2: Exchange JWT for installation access token ======
url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
headers = {"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"}
response = requests.post(url, headers=headers)
if response.status_code != 201:
    raise Exception(f"Failed to get installation token: {response.text}")

installation_token = response.json()["token"]

# ====== Step 3: Authenticate GitHub with installation token ======
g = Github(auth=Auth.Token(installation_token))
repo_name = os.environ["GITHUB_REPOSITORY"]
pr_number = int(os.environ["PR_NUMBER"])

repo = g.get_repo(repo_name)
pr = repo.get_pull(pr_number)

# ====== Step 4: Get diff of PR ======
diff_url = pr.url + ".diff"
diff_headers = {"Authorization": f"token {installation_token}"}
diff_response = requests.get(diff_url, headers=diff_headers)

if diff_response.status_code != 200:
    raise Exception(f"Failed to fetch diff: {diff_response.text}")

diff = diff_response.text[:4000]  # limit size

# ====== Step 5: Use Gemini for review ======
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = f"""You are a code review assistant.
Analyze the following GitHub PR diff and provide constructive feedback:

{diff}
"""

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents=[Content(parts=[Part.from_text(prompt)])],
)

review = response.text.strip()

# ====== Step 6: Post review as comment ======
pr.create_issue_comment(f"🤖 **AI Code Review (Gemini):**\n\n{review}")

print("✅ Review posted successfully!")
