import os
import time
import uuid
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from utils.logging import setup_logging
import structlog
from app.workflow import build_submission_response, execute_workflow

load_dotenv()
setup_logging()
logger = structlog.get_logger("server")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    logger.info("request_received", route="/", method="GET")
    return jsonify({
        "status": "online",
        "message": "Deep Research server is running.",
        "config": {
            "memgraph_uri": os.getenv("MEMGRAPH_URI", "bolt://localhost:7687"),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o")
        }
    })

@app.route("/run", methods=["POST"])
def run_submission():
    trace_id = f"run-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    logger.info("run_request_received", trace_id=trace_id, method=request.method)

    data = request.get_json(silent=True) or {}
    query = data.get("query")
    if not query:
        logger.warning("run_request_missing_query", trace_id=trace_id)
        return jsonify({
            "status": "error",
            "error_type": "VALIDATION_ERROR",
            "message": "Missing required field 'query' in JSON body.",
            "trace_id": trace_id
        }), 400

    try:
        started_at = time.time()
        final_state = execute_workflow(query)
        runtime_seconds = round(time.time() - started_at, 3)
        response_payload = build_submission_response(final_state, trace_id, runtime_seconds)
        logger.info("run_execution_completed_successfully", trace_id=trace_id, query=query)
        return jsonify(response_payload)
    except Exception as e:
        message = str(e)
        if "quota" in message.lower():
            error_type = "COMPASS_QUOTA_ERROR"
        elif "api_key" in message.lower() or "credentials" in message.lower():
            error_type = "COMPASS_AUTH_ERROR"
        else:
            error_type = "WORKFLOW_EXECUTION_ERROR"

        logger.error("run_execution_failed", trace_id=trace_id, query=query, error=message)
        return jsonify({
            "status": "error",
            "error_type": error_type,
            "message": message,
            "trace_id": trace_id
        }), 500

@app.route("/research", methods=["POST"])
def execute_research_legacy():
    data = request.get_json(silent=True) or {}
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing parameter 'query'."}), 400
    final_state = execute_workflow(query)
    return jsonify({
        "query": final_state.get("query"),
        "research_plan": final_state.get("research_plan"),
        "paper_shortlist": final_state.get("paper_shortlist"),
        "paper_summaries": final_state.get("paper_summaries"),
        "insight_synthesis": final_state.get("insight_synthesis"),
        "research_report": final_state.get("research_report"),
        "citation_source_list": final_state.get("citation_source_list")
    })

if __name__ == "__main__":
    logger.info("server_starting", host="0.0.0.0", port=8000)
    app.run(host="0.0.0.0", port=8000)
