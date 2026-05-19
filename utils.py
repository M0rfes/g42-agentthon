import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("harness")


def log_token_usage(step_name: str, usage: dict):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "step": step_name,
        "tokens": usage,
    }
    logger.info(json.dumps(log_entry))
