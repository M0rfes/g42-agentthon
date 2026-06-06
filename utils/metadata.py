import json
import os

_METADATA_PATH = os.path.join(os.path.dirname(__file__), "..", "metadata.json")

def _load_metadata() -> dict:
    with open(_METADATA_PATH, "r") as f:
        return json.load(f)

_metadata = _load_metadata()

def get_prompt(key: str) -> str:
    """Return a system prompt by key from metadata.json."""
    try:
        return _metadata["prompts"][key]
    except KeyError as e:
        raise KeyError(f"Prompt key '{key}' not found in metadata.json under 'prompts'.") from e
