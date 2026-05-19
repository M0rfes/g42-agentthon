import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_github_model(model_name="gpt-4o"):
    """
    Returns a ChatOpenAI instance configured for GitHub Models.
    """
    print("=====>", os.getenv("GITHUB_TOKEN"))
    return ChatOpenAI(
        model=model_name,
        openai_api_key=os.getenv("GITHUB_TOKEN"),
        openai_api_base="https://models.inference.ai.azure.com",
    )


# Export a default model instance
default_model = get_github_model()
