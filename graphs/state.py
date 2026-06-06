from typing import TypedDict, List, Dict, Any


class ResearchState(TypedDict):
    """
    State definition for the LangGraph Deep Research agent.
    Maintains all research context and directly maps to the 6 expected outputs for judges.
    """

    # Original user query
    query: str

    # ── 1. Research Plan ──────────────────────────────────────────────────────
    # Contains the elaborated points (favor/against) and refined search topics
    research_plan: Dict[str, Any]

    # ── 2. Paper Shortlist ────────────────────────────────────────────────────
    # List of promising papers/resources discovered from web searches
    paper_shortlist: List[Dict[str, Any]]

    # ── 3. Individual Paper Summaries ─────────────────────────────────────────
    # Summarized findings for each scraped document
    paper_summaries: List[Dict[str, Any]]

    # ── 4. Insight Synthesis ──────────────────────────────────────────────────
    # Synthesized notes and relationship maps (Vector + GraphRAG details)
    insight_synthesis: Dict[str, Any]

    # ── 5. Research Report ────────────────────────────────────────────────────
    # Final, publication-ready research report drafted by the agent
    research_report: str

    # ── 6. Citation or Source List ────────────────────────────────────────────
    # List of structured source links mapped to in-report citations
    citation_source_list: List[Dict[str, Any]]

    # Internal variables for tracking intermediate states
    enriched_query: str
    search_topics: List[str]
    scraped_data: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    agents_used: List[str]
    tools_used: List[str]
