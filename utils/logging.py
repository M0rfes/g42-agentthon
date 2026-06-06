import os
import sys
import time
import logging
from contextlib import contextmanager
import structlog
import tiktoken

def setup_logging():
    """
    Sets up structured logging. Outputs JSON inside Docker/Production
    and beautiful colored logs during local development.
    """
    # Root logging configuration
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Determine environment
    flask_env = (os.getenv("FLASK_ENV") or "development").lower()
    is_docker = os.path.exists("/.dockerenv") or flask_env != "development"

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_docker:
        # JSON logs for production/Docker environments
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.processors.JSONRenderer(),
        )
    else:
        # Beautiful console logs for local developer experience
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.dev.ConsoleRenderer(),
        )

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Setup initial logs configuration
setup_logging()
logger = structlog.get_logger("deep_research")

def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    """
    Counts the number of tokens in a text string using tiktoken.
    Defaults to gpt-4o's cl100k_base encoding if the model isn't recognized.
    """
    if not text:
        return 0
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(str(text)))

@contextmanager
def track_step(step_name: str, **extra_ctx):
    """
    A context manager to track an agent graph step or tool execution.
    Logs step start, step success/failure, execution duration, and token usage.
    
    Usage:
        with track_step("enrich_and_decompose", query=user_query) as metrics:
            # ... do processing ...
            metrics["input_tokens"] += count_tokens(prompt)
            metrics["output_tokens"] += count_tokens(response)
    """
    start_time = time.perf_counter()
    logger.info("step_start", step=step_name, **extra_ctx)
    
    # Initialize metrics structure that can be updated inside the block
    metrics = {"input_tokens": 0, "output_tokens": 0}
    
    try:
        yield metrics
        duration = time.perf_counter() - start_time
        logger.info(
            "step_success",
            step=step_name,
            duration_seconds=round(duration, 4),
            input_tokens=metrics["input_tokens"],
            output_tokens=metrics["output_tokens"],
            total_tokens=metrics["input_tokens"] + metrics["output_tokens"],
            **extra_ctx
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.error(
            "step_failed",
            step=step_name,
            error=str(e),
            duration_seconds=round(duration, 4),
            input_tokens=metrics["input_tokens"],
            output_tokens=metrics["output_tokens"],
            total_tokens=metrics["input_tokens"] + metrics["output_tokens"],
            **extra_ctx
        )
        raise
