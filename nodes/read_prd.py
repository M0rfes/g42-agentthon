import os
from state import State


def read_prd_node(state: State):
    prd_path = state["prd_path"]
    if not os.path.exists(prd_path):
        raise FileNotFoundError(f"PRD file not found at: {prd_path}")

    with open(prd_path, "r") as f:
        content = f.read()

    return {"prd_content": content}
