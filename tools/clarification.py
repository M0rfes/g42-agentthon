from langchain_core.tools import tool


@tool
def ask_clarification(question: str):
    """Ask the user for clarification regarding the PRD."""
    print(f"\n[AGENT]: {question}")
    answer = input("[USER]: ")
    return answer
