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
        "agents_used": [],
        "tools_used": [],
    }


def execute_workflow(query: str) -> dict:
    return _graph().invoke(_initial_state(query))


def build_submission_response(
    final_state: dict, trace_id: str, runtime_seconds: float
) -> dict:
    report = final_state.get("research_report") or ""
    summary = report[:1000] if isinstance(report, str) else str(report)
    return {
        "status": "success",
        "use_case_id": os.getenv("USE_CASE_ID", "16"),
        "result": {
            "summary": summary,
            "research_plan": final_state.get("research_plan"),
            "paper_shortlist": final_state.get("paper_shortlist"),
            "paper_summaries": final_state.get("paper_summaries"),
            "insight_synthesis": final_state.get("insight_synthesis"),
            "research_report": report,
            "citation_source_list": final_state.get("citation_source_list"),
            "recommendations": final_state.get("search_topics", []),
            "artifacts": final_state.get("citation_source_list", []),
        },
        "agents_used": final_state.get("agents_used", []),
        "tools_used": final_state.get("tools_used", []),
        "trace_id": trace_id,
        "runtime_seconds": runtime_seconds,
    }
