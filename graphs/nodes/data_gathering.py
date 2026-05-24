import os
import concurrent.futures
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from models.llm import get_langchain_llm
from graphs.state import ResearchState
from tools.playwright_tools import web_search, scrape_page
from utils.logging import logger, track_step, count_tokens

# ── Pydantic Output Schemas ──────────────────────────────────────────────────

class PaperSummary(BaseModel):
    title: str = Field(description="Title of the paper or webpage")
    url: str = Field(description="Absolute URL of the resource")
    summary: str = Field(description="A concise summary of key findings, data points, points in favor and against, and assertions")
    relevance_score: float = Field(description="Relevance rating from 0.0 to 1.0 explaining how useful this resource is to the core query")

# ── Node Function ─────────────────────────────────────────────────────────────

def data_gathering(state: ResearchState) -> ResearchState:
    """
    Agent node that gathers research material by running parallel web searches,
    deduplicating links, scraping content with Playwright, and generating paper summaries in parallel.
    """
    query = state["query"]
    research_plan = state.get("research_plan", {})
    search_topics = research_plan.get("search_topics", [])
    
    # Fallback to internal search topics if plan is empty
    if not search_topics:
        search_topics = state.get("search_topics", [query])
        
    with track_step("data_gathering", query=query, topics_count=len(search_topics)) as metrics:
        logger.info("data_gathering_node_start", query=query, topics=search_topics)
        
        # 1. PARALLEL WEB SEARCH STEP
        logger.info("data_gathering_parallel_search_start", count=len(search_topics))
        
        def run_single_search(topic: str) -> List[Dict[str, Any]]:
            try:
                # Call web_search tool using .invoke() to preserve telemetry
                return web_search.invoke({"query": topic, "max_results": 3})
            except Exception as e:
                logger.error("data_gathering_single_search_failed", topic=topic, error=str(e))
                return []
                
        # Perform parallel searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(search_topics), 5)) as executor:
            all_search_results = list(executor.map(run_single_search, search_topics))
            
        # 2. CONSOLIDATION & DEDUPLICATION STEP
        seen_urls = set()
        shortlist = []
        for results in all_search_results:
            if not results:
                continue
            for res in results:
                url = res.get("url")
                # Deduplicate by URL and skip error results
                if url and url not in seen_urls and "error" not in res:
                    seen_urls.add(url)
                    shortlist.append({
                        "title": res.get("title", "Unknown"),
                        "url": url,
                        "snippet": res.get("snippet", "")
                    })
                    
        logger.info("data_gathering_shortlist_consolidated", unique_urls_found=len(shortlist))
        
        # If no results found, return gracefully
        if not shortlist:
            logger.warning("data_gathering_no_results_found")
            return {
                **state,
                "paper_shortlist": [],
                "paper_summaries": [],
                "scraped_data": []
            }
            
        # 3. PARALLEL WEB SCRAPING STEP
        # Cap to top N most promising resources to balance tokens and speed
        max_scrape = 5
        target_shortlist = shortlist[:max_scrape]
        logger.info("data_gathering_parallel_scrape_start", count=len(target_shortlist))
        
        def run_single_scrape(item: Dict[str, Any]) -> Dict[str, Any]:
            url = item["url"]
            try:
                # Call scrape_page tool using .invoke() to preserve telemetry
                text = scrape_page.invoke({"url": url})
                return {
                    "url": url,
                    "title": item["title"],
                    "text": text
                }
            except Exception as e:
                logger.error("data_gathering_single_scrape_failed", url=url, error=str(e))
                return {
                    "url": url,
                    "title": item["title"],
                    "text": f"Error: {str(e)}"
                }
                
        # Perform parallel scrapes
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(target_shortlist), 5)) as executor:
            scraped_payloads = list(executor.map(run_single_scrape, target_shortlist))
            
        # 4. PARALLEL SUMMARIZATION STEP
        successful_scrapes = [s for s in scraped_payloads if not s["text"].startswith("Error")]
        logger.info(
            "data_gathering_parallel_summarization_start", 
            successful_count=len(successful_scrapes)
        )
        
        def run_single_summary(scraped: Dict[str, Any]) -> Dict[str, Any]:
            url = scraped["url"]
            title = scraped["title"]
            text = scraped["text"]
            
            system_prompt = (
                "You are an expert scientific research summarizer. Your job is to inspect the scraped content "
                "of a webpage/resource and produce a structured, high-fidelity summary detailing key arguments, "
                "empirical findings, points in favor or against, and assign a precise relevance score (0.0 to 1.0) "
                "assessing how useful this resource is to our core query."
            )
            user_prompt = (
                f"Core Research Query: '{query}'\n\n"
                f"Resource Title: {title}\n"
                f"Resource URL: {url}\n\n"
                f"Scraped Text Content:\n{text[:4000]}" # Cap context payload
            )
            
            try:
                llm = get_langchain_llm()
                structured_llm = llm.with_structured_output(PaperSummary)
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # Increment token tracking metrics locally inside node execution
                input_toks = count_tokens(system_prompt + user_prompt)
                
                evaluation = structured_llm.invoke(messages)
                
                output_toks = count_tokens(evaluation.summary)
                
                return {
                    "summary_data": {
                        "title": evaluation.title,
                        "url": evaluation.url,
                        "summary": evaluation.summary,
                        "relevance_score": evaluation.relevance_score
                    },
                    "input_tokens": input_toks,
                    "output_tokens": output_toks
                }
            except Exception as e:
                logger.error("data_gathering_single_summary_failed", url=url, error=str(e))
                return None
                
        # Perform parallel summarizations
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(successful_scrapes), 5)) as executor:
            summary_results = list(executor.map(run_single_summary, successful_scrapes))
            
        # Filter successful summaries and aggregate token metrics
        paper_summaries = []
        for res in summary_results:
            if res:
                paper_summaries.append(res["summary_data"])
                metrics["input_tokens"] += res["input_tokens"]
                metrics["output_tokens"] += res["output_tokens"]
                
        logger.info(
            "data_gathering_node_success",
            shortlist_count=len(shortlist),
            summaries_count=len(paper_summaries),
            scraped_count=len(successful_scrapes)
        )
        
        # Return the updated state
        state_update = {
            **state,
            "paper_shortlist": shortlist,
            "paper_summaries": paper_summaries,
            "scraped_data": successful_scrapes
        }
        
        return state_update
