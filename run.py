import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from utils.logging import setup_logging
import structlog
from graphs.orchestrator import create_research_graph

load_dotenv()
setup_logging()
logger = structlog.get_logger("server")

app = Flask(__name__)

# Compile the research graph globally at server startup
research_graph = create_research_graph()

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

@app.route("/research", methods=["POST", "GET"])
def execute_research():
    logger.info("research_request_received", method=request.method)
    
    # 1. Retrieve the query from JSON body or URL parameters
    query = None
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        query = data.get("query")
    else:
        query = request.args.get("query")
        
    if not query:
        logger.warning("research_request_missing_query")
        return jsonify({
            "error": "Missing parameter 'query'. Please provide a search query to execute research."
        }), 400
        
    logger.info("research_execution_started", query=query)
    
    # 2. Initialize the ResearchState
    initial_state = {
        "query": query,
        "research_plan": {},
        "paper_shortlist": [],
        "paper_summaries": [],
        "insight_synthesis": {},
        "research_report": "",
        "citation_source_list": [],
        "enriched_query": "",
        "search_topics": [],
        "scraped_data": [],
        "contradictions": []
    }
    
    try:
        # 3. Run the compiled LangGraph workflow
        final_state = research_graph.invoke(initial_state)
        
        logger.info("research_execution_completed_successfully", query=query)
        
        # 4. Map and return the 6 expected outputs required by judges
        return jsonify({
            "query": final_state.get("query"),
            "research_plan": final_state.get("research_plan"),
            "paper_shortlist": final_state.get("paper_shortlist"),
            "paper_summaries": final_state.get("paper_summaries"),
            "insight_synthesis": final_state.get("insight_synthesis"),
            "research_report": final_state.get("research_report"),
            "citation_source_list": final_state.get("citation_source_list")
        })
        
    except Exception as e:
        logger.error("research_execution_failed", query=query, error=str(e))
        return jsonify({
            "error": "An internal error occurred during graph execution.",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    logger.info("server_starting", host="0.0.0.0", port=8000)
    app.run(host="0.0.0.0", port=8000)
