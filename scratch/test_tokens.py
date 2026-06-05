import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")
model_name = os.getenv("OPENAI_MODEL", "Meta-Llama-3.1-8B-Instruct")

print(f"Model: {model_name}")

try:
    llm = ChatOpenAI(
        model=model_name,
        api_key=github_token,
        base_url="https://models.inference.ai.azure.com",
        temperature=0,
        extra_body={"max_tokens": 100}
    )
    res = llm.invoke("Write a 50-word story about a developer.")
    print(f"Content: {res.content}")
    print(f"Usage: {res.response_metadata.get('token_usage')}")
    print(f"Finish Reason: {res.response_metadata.get('finish_reason')}")
except Exception as e:
    print(f"Error: {e}")
