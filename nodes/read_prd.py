import os
import json
from state import State


def read_prd_node(state: State):
    prd_path = state["prd_path"]
    if not os.path.exists(prd_path):
        raise FileNotFoundError(f"PRD file not found at: {prd_path}")

    with open(prd_path, "r") as f:
        content = f.read()

    with open("metadata.json", "r") as f:
        metadata = json.load(f)

    return {
        "prd_content": content,
        "output_dir": metadata.get("output_dir", "./output"),
    }
