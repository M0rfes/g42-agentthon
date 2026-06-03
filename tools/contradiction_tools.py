import os
import json
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from models.llm import get_langchain_llm
from models.index_manager import get_vector_index, get_property_graph_index
from tools.playwright_tools import web_search, scrape_page
from utils.logging import logger, track_step, count_tokens
from utils.metadata import get_prompt

class ContradictionResolution(BaseModel):
    verdict: str = Field(description="Must be CLAIM_A (Claim A is correct), CLAIM_B (Claim B is correct), RECONCILED (both claims are synthesized/reconciled), or UNRESOLVED")
    reconciled_fact: str = Field(description="A clear, consolidated statement of the factual truth that resolves the contradiction")
    resolution_explanation: str = Field(description="Comprehensive explanation detailing how the contradiction was resolved and citing the factual evidence")
    resolved_citations: list[str] = Field(description="List of URLs or document sources that provide evidence for this resolution")

@tool
def resolve_contradiction(claim_a: str, claim_b: str) -> str:
    """
    Resolve a contradiction between two competing claims (Claim A and Claim B) identified 
    during research. Searches LlamaIndex, Memgraph GraphRAG, and performs real-time Playwright web searches 
    to determine the absolute truth, returning a resolved factual synthesis with citations.
    """
    with track_step("resolve_contradiction", claim_a=claim_a, claim_b=claim_b) as metrics:
        logger.info("resolve_contradiction_start", claim_a=claim_a, claim_b=claim_b)
        
        # 1. Search internal indices first
        internal_context = ""
        try:
            vector_index = get_vector_index()
            # Retrieve relevant content for both claims
            retriever = vector_index.as_retriever(similarity_top_k=2)
            nodes_a = retriever.retrieve(claim_a)
            nodes_b = retriever.retrieve(claim_b)
            
            nodes = nodes_a + nodes_b
            if nodes:
                internal_context = "--- Internal Indexed Facts ---\n" + "\n\n".join([
                    f"Source: {n.node.metadata.get('url', 'Unknown')} | Title: {n.node.metadata.get('title', 'Unknown')}\nContent: {n.node.get_content()}"
                    for n in nodes
                ])
        except Exception as e:
            logger.warning("resolve_contradiction_internal_search_failed", error=str(e))
            
        # 2. Perform Playwright web searches for contradiction context
        external_context = ""
        try:
            # Craft a search query focusing on the conflict
            search_query = f"\"{claim_a}\" vs \"{claim_b}\" contradiction truth"
            logger.info("resolve_contradiction_external_search", query=search_query)
            
            # Execute tool call using .invoke() to preserve instrumentation/metrics
            search_results = web_search.invoke({"query": search_query})
            
            if isinstance(search_results, list) and len(search_results) > 0 and "error" not in search_results[0]:
                scraped_contents = []
                # Scrape top 2 results for deep factual verification
                for res in search_results[:2]:
                    url = res.get("url")
                    if url:
                        logger.info("resolve_contradiction_external_scrape", url=url)
                        text = scrape_page.invoke({"url": url})
                        if text and not text.startswith("Error scraping"):
                            scraped_contents.append(f"Source URL: {url}\nTitle: {res.get('title')}\nScraped Content:\n{text[:2000]}") # Cap to 2000 chars per page
                
                if scraped_contents:
                    external_context = "--- Web Search Fresh Evidence ---\n" + "\n\n".join(scraped_contents)
        except Exception as e:
            logger.warning("resolve_contradiction_external_search_failed", error=str(e))
            
        # 3. Feed unified evidence into GPT-4o with structured output
        system_prompt = get_prompt("contradiction_resolution")
        
        user_content = (
            f"Assertion A (Claim A): '{claim_a}'\n"
            f"Assertion B (Claim B): '{claim_b}'\n\n"
            f"{internal_context}\n\n"
            f"{external_context}\n"
        )
        
        try:
            llm = get_langchain_llm()
            structured_llm = llm.with_structured_output(ContradictionResolution)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            metrics["input_tokens"] += count_tokens(system_prompt + user_content)
            
            resolution = structured_llm.invoke(messages)
            
            result = {
                "verdict": resolution.verdict,
                "reconciled_fact": resolution.reconciled_fact,
                "resolution_explanation": resolution.resolution_explanation,
                "resolved_citations": resolution.resolved_citations
            }
            
            metrics["output_tokens"] += count_tokens(json.dumps(result))
            
            logger.info("resolve_contradiction_success", verdict=resolution.verdict)
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error("resolve_contradiction_failed", error=str(e))
            fallback = {
                "verdict": "UNRESOLVED",
                "reconciled_fact": "Could not resolve the contradiction due to an error.",
                "resolution_explanation": f"Execution error occurred: {str(e)}",
                "resolved_citations": []
            }
            return json.dumps(fallback, indent=2)
