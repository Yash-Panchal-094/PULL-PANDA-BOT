import os
import subprocess
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq

# Get API key from env
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ GROQ_API_KEY not found in environment variables!")

# Setup LLM
llm = ChatGroq(
    temperature=0,
    groq_api_key=api_key,
    model_name="mixtral-8x7b-32768"
)

# Prompt for code review
prompt = PromptTemplate(
    input_variables=["diff"],
    template="""
You are an AI code reviewer. Review the following Git diff and provide:
1. A summary of the changes
2. Potential bugs or issues
3. Suggestions for improvement

Diff:
{diff}
"""
)

review_chain = LLMChain(prompt=prompt, llm=llm)

# Get the diff from git
diff = subprocess.getoutput("git diff HEAD~1 HEAD")

if not diff.strip():
    print("⚠️ No diff found. Skipping review.")
else:
    review = review_chain.invoke({"diff": diff[:4000]})
    print("🤖 AI Review:\n", review["text"])
