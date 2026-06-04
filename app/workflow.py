import os
from functools import lru_cache
from graphs.orchestrator import create_research_graph


@lru_cache(maxsize=1)
def _graph():
    return create_research_graph()


def _initial_state(query: str) -> dict:
    return {
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
        "contradictions": [],
    }


def execute_workflow(query: str) -> dict:
    return _graph().invoke(_initial_state(query))


def build_submission_response(final_state: dict, trace_id: str, runtime_seconds: float) -> dict:
    report = final_state.get("research_report") or ""
    summary = report[:1000] if isinstance(report, str) else str(report)
    return {
        "status": "success",
        "use_case_id": os.getenv("USE_CASE_ID", "16"),
        "result": {
            "summary": summary,
            "recommendations": final_state.get("search_topics", []),
            "artifacts": final_state.get("citation_source_list", []),
        },
        "agents_used": ["Planner", "Researcher", "Evaluator"],
        "trace_id": trace_id,
        "runtime_seconds": runtime_seconds,
    }


def run_query(query: str, trace_id: str, runtime_seconds: float) -> dict:
    final_state = execute_workflow(query)
    return build_submission_response(final_state, trace_id, runtime_seconds)
