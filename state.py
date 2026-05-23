from typing import Annotated, TypedDict, List
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[List, add_messages]
    prd_path: str
    prd_content: str
    plan: str
    ask_allowed: bool
    output_dir: str
