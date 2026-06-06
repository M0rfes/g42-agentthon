import os
import json
import urllib.parse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from models.llm import get_langchain_llm
from graphs.state import ResearchState
from tools.llamaindex_tools import fact_checker
from tools.contradiction_tools import resolve_contradiction
from utils.logging import logger, track_step, count_tokens
from utils.metadata import get_prompt

# ── Citation URL Validation ───────────────────────────────────────────────────

_FAKE_URL_PATTERNS = [
    "example.com",
    "example.org",
    "example.net",
    "localhost",
    "127.0.0.1",
    "placeholder",
    "your-url",
    "insert-url",
    "graphrag-context",
    "no-url",
    "n/a",
]


def _is_valid_citation_url(url: str) -> bool:
    """Returns False if the URL is a known placeholder or fake URL."""
    if not url or not url.startswith("http"):
        return False
    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in _FAKE_URL_PATTERNS)

def _fix_citation_urls(
    citations: List[Dict], paper_summaries: List[Dict], scraped_data: List[Dict]
) -> List[Dict]:
    """
    Validates citation URLs and attempts to substitute real source URLs
    from paper_summaries or scraped_data when a placeholder/fake URL is detected.
    Citations with unfixable URLs are dropped.
    """
    # Build lookup: title -> url from real scraped sources
    title_to_url: Dict[str, str] = {}
    for source in (paper_summaries or []) + (scraped_data or []):
        title = source.get("title", "").lower().strip()
        url = source.get("url", "")
        if title and _is_valid_citation_url(url):
            title_to_url[title] = url

    fixed: List[Dict] = []
    for c in citations:
        url = c.get("url", "")
        title = c.get("title", "")

        if _is_valid_citation_url(url):
            fixed.append(c)
            continue

        # Attempt title-based substitution
        matched_url = title_to_url.get(title.lower().strip())
        if not matched_url:
            # Fuzzy: check if any known title is a substring of the citation title
            for known_title, known_url in title_to_url.items():
                if known_title in title.lower() or title.lower() in known_title:
                    matched_url = known_url
                    break

        if matched_url:
            logger.warning(
                "report_writer_citation_url_fixed",
                original_url=url,
                substituted_url=matched_url,
                title=title,
            )
            fixed.append({**c, "url": matched_url})
        else:
            logger.warning(
                "report_writer_citation_url_dropped",
                url=url,
                title=title,
                reason="Placeholder/fake URL and no matching real source found",
            )
    return fixed


# ── Pydantic Output Schemas ──────────────────────────────────────────────────


class Citation(BaseModel):
    id: str = Field(
        description="Unique citation identifier used in the text, e.g., [1]"
    )
    title: str = Field(description="Title of the cited paper or article")
    url: str = Field(description="Absolute URL of the cited source")


class InitialDraftResult(BaseModel):
    draft_content: str = Field(
        description="Full markdown draft of the research report with in-text citation keys like [1], [2]"
    )
    citations: List[Citation] = Field(
        description="List of all sources cited in the draft report"
    )


class CritiqueResult(BaseModel):
    factual_assertions: List[str] = Field(
        description="List of 3-4 specific factual claims or stats from the draft to run through the fact-checker"
    )
    structural_critique: str = Field(
        description="Stylistic, flow, and coverage critique of the draft report"
    )


class FinalReportResult(BaseModel):
    research_report: str = Field(
        description="Refined, publication-grade markdown research report incorporating critique and fact-checking feedback"
    )
    citation_source_list: List[Citation] = Field(
        description="Finalized and ordered list of citation sources"
    )


# ── Node Function ─────────────────────────────────────────────────────────────


def report_writer(state: ResearchState) -> ResearchState:
    """
    Agent node that drafts a comprehensive research report using a Generate, Critique,
    Fact-check, and Refine loop. Utilizes fact_checker and resolve_contradiction tools to verify claims.
    """
    query = state["query"]
    paper_summaries = state.get("paper_summaries", [])
    scraped_data = state.get("scraped_data", [])
    insight_synthesis = state.get("insight_synthesis", {})

    with track_step("report_writer", query=query) as metrics:
        logger.info(
            "report_writer_node_start", query=query, papers_count=len(paper_summaries)
        )

        used_tools = set()

        # Initialize LangChain LLM
        llm = get_langchain_llm()

        # Compile contextual inputs for the prompts
        paper_context = ""
        for idx, p in enumerate(paper_summaries, 1):
            paper_context += (
                f"[{idx}] Title: {p.get('title', 'Unknown')}\n"
                f"URL: {p.get('url', '')}\n"
                f"Summary: {p.get('summary', '')}\n"
                f"Relevance Score: {p.get('relevance_score', 0.0)}\n\n"
            )

        synthesis_context = (
            f"Executive Summary: {insight_synthesis.get('executive_summary', '')}\n\n"
            f"Key Themes:\n"
            + "\n".join([f"- {t}" for t in insight_synthesis.get("key_themes", [])])
            + "\n\n"
            f"Empirical Findings:\n"
            + "\n".join(
                [f"- {f}" for f in insight_synthesis.get("empirical_findings", [])]
            )
            + "\n\n"
            f"GraphRAG Relationships:\n"
            + "\n".join(
                [
                    f"- {r}"
                    for r in insight_synthesis.get("entities_and_relationships", [])
                ]
            )
        )

        # 1. INITIAL GENERATION STEP
        logger.info("report_writer_initial_draft_start")

        draft_system = get_prompt("report_writer_draft")

        draft_user = (
            f"Research Subject: '{query}'\n\n"
            f"--- Paper Shortlist & Summaries ---\n{paper_context}\n\n"
            f"--- Synthesized Insights ---\n{synthesis_context}\n"
        )

        metrics["input_tokens"] += count_tokens(draft_system + draft_user)

        try:
            draft_llm = llm.with_structured_output(InitialDraftResult)
            initial_draft = draft_llm.invoke(
                [
                    {"role": "system", "content": draft_system},
                    {"role": "user", "content": draft_user},
                ]
            )
            logger.info("report_writer_initial_draft_success")
            metrics["output_tokens"] += count_tokens(
                initial_draft.draft_content + str(initial_draft.citations)
            )
        except Exception as e:
            logger.error("report_writer_initial_draft_failed", error=str(e))
            # Fallback draft if structured generation fails
            initial_draft = InitialDraftResult(
                draft_content=f"# Research Report: {query}\n\nInitial draft could not be generated due to: {str(e)}",
                citations=[],
            )

        # 2. CRITIQUE STEP
        logger.info("report_writer_critique_start")

        critique_system = get_prompt("report_writer_critique")

        critique_user = (
            f"Draft Report:\n{initial_draft.draft_content}\n\n"
            f"Available Citations:\n"
            + "\n".join(
                [f"{c.id}: {c.title} ({c.url})" for c in initial_draft.citations]
            )
        )

        metrics["input_tokens"] += count_tokens(critique_system + critique_user)

        try:
            critique_llm = llm.with_structured_output(CritiqueResult)
            critique = critique_llm.invoke(
                [
                    {"role": "system", "content": critique_system},
                    {"role": "user", "content": critique_user},
                ]
            )
            logger.info(
                "report_writer_critique_success",
                assertions_to_check=len(critique.factual_assertions),
            )
            metrics["output_tokens"] += count_tokens(
                critique.structural_critique + str(critique.factual_assertions)
            )
        except Exception as e:
            logger.error("report_writer_critique_failed", error=str(e))
            critique = CritiqueResult(
                factual_assertions=[],
                structural_critique=f"Peer review critique failed: {str(e)}",
            )

        # 3. FACT-CHECKING & CONTRADICTION RESOLUTION STEP
        logger.info("report_writer_fact_checking_start")
        fact_check_feedback = []
        contradictions_resolved = []

        for claim in critique.factual_assertions:
            logger.info("report_writer_verifying_claim", claim=claim)
            try:
                # Execute fact checker tool using standard tool invocation
                used_tools.add("FactChecker")
                fc_result_str = fact_checker.invoke({"claim": claim})
                fc_result = json.loads(fc_result_str)

                status = fc_result.get("verification_status", "UNVERIFIED")
                explanation = fc_result.get("explanation", "")
                citations = fc_result.get("supporting_citations", [])

                logger.info("report_writer_claim_verified", claim=claim, status=status)
                fact_check_feedback.append(
                    {
                        "claim": claim,
                        "status": status,
                        "explanation": explanation,
                        "citations": citations,
                    }
                )

                # If a claim is REFUTED, attempt to find a contradiction or resolve it
                if status == "REFUTED":
                    logger.warning("report_writer_refuted_claim_found", claim=claim)
                    # Look up alternative claim from database to resolve
                    used_tools.add("ContradictionResolver")
                    alternative_query = f"alternative facts regarding {claim}"

                    resolve_res_str = resolve_contradiction.invoke(
                        {"claim_a": claim, "claim_b": f"The claim that: {explanation}"}
                    )
                    resolve_res = json.loads(resolve_res_str)

                    contradictions_resolved.append(
                        {
                            "original_claim": claim,
                            "reconciled_fact": resolve_res.get("reconciled_fact", ""),
                            "resolution_explanation": resolve_res.get(
                                "resolution_explanation", ""
                            ),
                            "resolved_citations": resolve_res.get(
                                "resolved_citations", []
                            ),
                        }
                    )
            except Exception as e:
                logger.error(
                    "report_writer_fact_check_claim_failed", claim=claim, error=str(e)
                )

        # 4. REFINEMENT & FINALIZATION STEP
        logger.info("report_writer_refinement_start")

        refine_system = get_prompt("report_writer_refine")

        fact_check_text = "--- Fact Checking Results ---\n"
        if fact_check_feedback:
            for item in fact_check_feedback:
                fact_check_text += (
                    f"Claim: '{item['claim']}'\n"
                    f"Verdict: {item['status']}\n"
                    f"Explanation: {item['explanation']}\n"
                    f"Supporting Citations: {item['citations']}\n\n"
                )
        else:
            fact_check_text += "No claims were fact-checked.\n"

        contradiction_text = "--- Resolved Contradictions ---\n"
        if contradictions_resolved:
            for item in contradictions_resolved:
                contradiction_text += (
                    f"Refuted Claim: '{item['original_claim']}'\n"
                    f"Reconciled Fact: {item['reconciled_fact']}\n"
                    f"Explanation: {item['resolution_explanation']}\n"
                    f"Resolved Citations: {item['resolved_citations']}\n\n"
                )
        else:
            contradiction_text += "No contradictions needed resolution.\n"

        refine_user = (
            f"Original Draft:\n{initial_draft.draft_content}\n\n"
            f"Peer Critique:\n{critique.structural_critique}\n\n"
            f"{fact_check_text}\n"
            f"{contradiction_text}\n"
            f"Original Citations List:\n"
            + "\n".join(
                [f"{c.id}: {c.title} ({c.url})" for c in initial_draft.citations]
            )
        )

        metrics["input_tokens"] += count_tokens(refine_system + refine_user)

        try:
            refine_llm = llm.with_structured_output(FinalReportResult)
            final_report = refine_llm.invoke(
                [
                    {"role": "system", "content": refine_system},
                    {"role": "user", "content": refine_user},
                ]
            )
            logger.info("report_writer_refinement_success")

            # Map Pydantic Citation list to standard dictionary list for State
            citation_list = [
                {"id": c.id, "title": c.title, "url": c.url}
                for c in final_report.citation_source_list
            ]

            # Fix or drop any placeholder/fake URLs produced by the LLM
            citation_list = _fix_citation_urls(
                citation_list, paper_summaries, scraped_data
            )

            # If the model returned an empty list (or all were dropped), apply fallback
            if not citation_list:
                logger.warning("report_writer_empty_citation_list_applying_fallback")
                candidate_citations = [
                    {"id": c.id, "title": c.title, "url": c.url}
                    for c in initial_draft.citations
                ]
                candidate_citations = _fix_citation_urls(
                    candidate_citations, paper_summaries, scraped_data
                )
                if candidate_citations:
                    citation_list = candidate_citations
                else:
                    # Last resort: pull real URLs directly from scraped sources
                    for idx, p in enumerate(paper_summaries, 1):
                        url = p.get("url", "")
                        if _is_valid_citation_url(url):
                            citation_list.append(
                                {
                                    "id": f"[{idx}]",
                                    "title": p.get("title", "Unknown Source"),
                                    "url": url,
                                }
                            )

            metrics["output_tokens"] += count_tokens(
                final_report.research_report + str(citation_list)
            )

            return {
                **state,
                "research_report": final_report.research_report,
                "citation_source_list": citation_list,
                "agents_used": state.get("agents_used", []) + ["Writer"],
                "tools_used": list(set(state.get("tools_used", []) + list(used_tools))),
            }
        except Exception as e:
            logger.error("report_writer_refinement_failed", error=str(e))
            # Fallback: use initial draft citations, sanitized
            citation_list = [
                {"id": c.id, "title": c.title, "url": c.url}
                for c in initial_draft.citations
            ]
            citation_list = _fix_citation_urls(
                citation_list, paper_summaries, scraped_data
            )
            return {
                **state,
                "research_report": initial_draft.draft_content,
                "citation_source_list": citation_list,
                "agents_used": state.get("agents_used", []) + ["Writer"],
                "tools_used": list(set(state.get("tools_used", []) + list(used_tools))),
            }
