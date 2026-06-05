import json
import os

_METADATA_PATH = os.path.join(os.path.dirname(__file__), "..", "metadata.json")

def _load_metadata() -> dict:
    with open(_METADATA_PATH, "r") as f:
        return json.load(f)

_metadata = _load_metadata()

def get_prompt(key: str) -> str:
    """Return a system prompt by key from metadata.json."""
    return _metadata["prompts"][key]
