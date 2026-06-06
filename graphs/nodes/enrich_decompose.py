import os
from typing import List
from pydantic import BaseModel, Field
from models.llm import get_langchain_llm
from graphs.state import ResearchState
from utils.logging import logger, track_step, count_tokens
from utils.metadata import get_prompt

# ── Pydantic Output Schemas ──────────────────────────────────────────────────


class InitialPlan(BaseModel):
    enriched_query: str = Field(
        description="Detailed elaboration of the query outlining arguments/viewpoints in favor and against (point and counter-point)"
    )
    initial_search_topics: List[str] = Field(
        description="Initial list of 3-5 specific, distinct sub-queries or search terms to collect raw research material"
    )


class CritiquePlan(BaseModel):
    gaps: List[str] = Field(
        description="List of identified gaps, missing arguments, ignored counter-perspectives, or omitted search themes"
    )
    critique_rationale: str = Field(
        description="Detailed critique rationale analyzing the blind spots of the initial plan"
    )


class FinalPlan(BaseModel):
    refined_enriched_query: str = Field(
        description="Critique-refined, completely balanced, and comprehensive elaborated query"
    )
    refined_search_topics: List[str] = Field(
        description="Finalized list of 4-6 precise search topics/queries, incorporating the critique insights"
    )


# ── Node Function ─────────────────────────────────────────────────────────────


def enrich_decompose(state: ResearchState) -> ResearchState:
    """
    Agent node that enriches the user query and decomposes it into search topics
    using a full single-pass Generate and Critique pattern.
    """
    query = state["query"]

    with track_step("enrich_decompose", query=query) as metrics:
        logger.info("enrich_decompose_node_start", query=query)

        # Initialize LangChain LLM
        llm = get_langchain_llm()

        # 1. INITIAL GENERATION STEP
        init_system = get_prompt("enrich_decompose_init")
        init_user = f"Original user research query: '{query}'"

        logger.info("enrich_decompose_generate_initial")
        metrics["input_tokens"] += count_tokens(init_system + init_user)

        init_llm = llm.with_structured_output(InitialPlan)
        init_plan = init_llm.invoke(
            [
                {"role": "system", "content": init_system},
                {"role": "user", "content": init_user},
            ]
        )

        logger.info(
            "enrich_decompose_initial_generated",
            topics_count=len(init_plan.initial_search_topics),
        )
        metrics["output_tokens"] += count_tokens(
            init_plan.enriched_query + str(init_plan.initial_search_topics)
        )

        # 2. CRITIQUE STEP
        critique_system = get_prompt("enrich_decompose_critique")
        critique_user = (
            f"Target Query: '{query}'\n\n"
            f"Initial Enriched Query (Points/Counter-Points):\n{init_plan.enriched_query}\n\n"
            f"Initial Search Topics:\n"
            + "\n".join([f"- {t}" for t in init_plan.initial_search_topics])
        )

        logger.info("enrich_decompose_critique_plan")
        metrics["input_tokens"] += count_tokens(critique_system + critique_user)

        critique_llm = llm.with_structured_output(CritiquePlan)
        critique = critique_llm.invoke(
            [
                {"role": "system", "content": critique_system},
                {"role": "user", "content": critique_user},
            ]
        )

        logger.info(
            "enrich_decompose_critique_completed", gaps_found=len(critique.gaps)
        )
        metrics["output_tokens"] += count_tokens(
            critique.critique_rationale + str(critique.gaps)
        )

        # 3. REFINEMENT & FINALIZATION STEP
        refine_system = get_prompt("enrich_decompose_refine")
        refine_user = (
            f"Target Query: '{query}'\n\n"
            f"Initial Enriched Query:\n{init_plan.enriched_query}\n"
            f"Initial Search Topics:\n"
            + "\n".join([f"- {t}" for t in init_plan.initial_search_topics])
            + "\n\n"
            f"Critique Gaps Omitted:\n"
            + "\n".join([f"- {g}" for g in critique.gaps])
            + "\n"
            f"Critique Rationale:\n{critique.critique_rationale}"
        )

        logger.info("enrich_decompose_refine_plan")
        metrics["input_tokens"] += count_tokens(refine_system + refine_user)

        refine_llm = llm.with_structured_output(FinalPlan)
        final_plan = refine_llm.invoke(
            [
                {"role": "system", "content": refine_system},
                {"role": "user", "content": refine_user},
            ]
        )

        logger.info(
            "enrich_decompose_refinement_success",
            final_topics_count=len(final_plan.refined_search_topics),
        )
        metrics["output_tokens"] += count_tokens(
            final_plan.refined_enriched_query + str(final_plan.refined_search_topics)
        )

        # Construct the detailed Research Plan output
        research_plan = {
            "elaborated_query": final_plan.refined_enriched_query,
            "search_topics": final_plan.refined_search_topics,
            "critique": {
                "gaps": critique.gaps,
                "rationale": critique.critique_rationale,
            },
        }

        # Return state update dictionary matching the ResearchState schema
        state_update = {
            "query": query,
            "research_plan": research_plan,
            "paper_shortlist": state.get("paper_shortlist", []),
            "paper_summaries": state.get("paper_summaries", []),
            "insight_synthesis": state.get("insight_synthesis", {}),
            "research_report": state.get("research_report", ""),
            "citation_source_list": state.get("citation_source_list", []),
            "enriched_query": final_plan.refined_enriched_query,
            "search_topics": final_plan.refined_search_topics,
            "scraped_data": state.get("scraped_data", []),
            "contradictions": state.get("contradictions", []),
            "agents_used": state.get("agents_used", []) + ["Planner"],
        }

        return state_update
