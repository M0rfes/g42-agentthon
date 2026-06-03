import os
import json
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from models.llm import get_langchain_llm
from graphs.state import ResearchState
from models.index_manager import index_scraped_content, get_vector_index, get_property_graph_index
from utils.logging import logger, track_step, count_tokens
from utils.metadata import get_prompt

# ── Pydantic Output Schemas ──────────────────────────────────────────────────

class InsightSynthesisResult(BaseModel):
    executive_summary: str = Field(
        description="High-level executive summary of synthesized research insights"
    )
    key_themes: List[str] = Field(
        description="List of 3-5 core themes, paradigms, or arguments identified across the papers"
    )
    empirical_findings: List[str] = Field(
        description="Specific empirical results, experimental data, or statistics gathered from the papers"
    )
    entities_and_relationships: List[str] = Field(
        description="Structured entities and their relationships extracted from the GraphRAG knowledge graph (Memgraph)"
    )

# ── Node Function ─────────────────────────────────────────────────────────────

def synthesis(state: ResearchState) -> ResearchState:
    """
    Agent node that indexes gathered research into standard Vector and Memgraph PropertyGraph indices,
    executes semantic Vector search and GraphRAG path queries, and synthesizes unified insights.
    """
    query = state["query"]
    scraped_data = state.get("scraped_data", [])
    
    with track_step("synthesis", query=query, scraped_count=len(scraped_data)) as metrics:
        logger.info("synthesis_node_start", query=query, scraped_count=len(scraped_data))
        
        # If no research data has been scraped, return empty synthesis gracefully
        if not scraped_data:
            logger.warning("synthesis_no_scraped_data_available")
            empty_synthesis = {
                "executive_summary": "No research content was successfully gathered during the research step.",
                "key_themes": [],
                "empirical_findings": [],
                "entities_and_relationships": []
            }
            return {
                **state,
                "insight_synthesis": empty_synthesis
            }
            
        # 1. DOCUMENT INGESTION STEP
        logger.info("synthesis_ingestion_start")
        for item in scraped_data:
            url = item["url"]
            title = item["title"]
            text = item["text"]
            
            logger.info("synthesis_ingesting_document", url=url, title=title)
            try:
                # Indexes content in both Vector Store and Memgraph Property Graph
                index_scraped_content(url, title, text)
            except Exception as e:
                logger.error("synthesis_ingestion_failed", url=url, error=str(e))
                
        logger.info("synthesis_ingestion_completed")
        
        # 2. VECTOR SEARCH RETRIEVAL
        logger.info("synthesis_vector_retrieval_start")
        try:
            vector_index = get_vector_index()
            vector_query_engine = vector_index.as_query_engine(similarity_top_k=5)
            vector_response = str(vector_query_engine.query(
                f"Synthesize the main empirical findings, metrics, and arguments for: '{query}'"
            ))
            logger.info("synthesis_vector_retrieval_success")
        except Exception as e:
            logger.error("synthesis_vector_retrieval_failed", error=str(e))
            vector_response = "No vector search results found."
            
        # 3. GraphRAG RELATION RETRIEVAL (MEMGRAPH)
        logger.info("synthesis_graphrag_retrieval_start")
        try:
            graph_index = get_property_graph_index()
            graph_query_engine = graph_index.as_query_engine(include_text=True)
            graph_response = str(graph_query_engine.query(
                f"Identify all key entities, facts, and relationships related to: '{query}'"
            ))
            logger.info("synthesis_graphrag_retrieval_success")
        except Exception as e:
            logger.error("synthesis_graphrag_retrieval_failed", error=str(e))
            graph_response = "No knowledge graph relationships found."
            
        # 4. STRUCTURED LLM SYNTHESIS
        logger.info("synthesis_llm_compilation_start")
        
        system_prompt = get_prompt("synthesis")
        
        user_prompt = (
            f"Research Subject: '{query}'\n\n"
            f"--- Vector Context ---\n{vector_response}\n\n"
            f"--- GraphRAG Relationship Context ---\n{graph_response}\n"
        )
        
        try:
            llm = get_langchain_llm()
            structured_llm = llm.with_structured_output(InsightSynthesisResult)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            metrics["input_tokens"] += count_tokens(system_prompt + user_prompt)
            
            compilation = structured_llm.invoke(messages)
            
            result = {
                "executive_summary": compilation.executive_summary,
                "key_themes": compilation.key_themes,
                "empirical_findings": compilation.empirical_findings,
                "entities_and_relationships": compilation.entities_and_relationships
            }
            
            metrics["output_tokens"] += count_tokens(json.dumps(result))
            
            logger.info("synthesis_llm_compilation_success")
            
            # Return updated state
            return {
                **state,
                "insight_synthesis": result
            }
            
        except Exception as e:
            logger.error("synthesis_llm_compilation_failed", error=str(e))
            fallback = {
                "executive_summary": f"Could not compile insights due to an error: {str(e)}",
                "key_themes": [],
                "empirical_findings": [],
                "entities_and_relationships": []
            }
            return {
                **state,
                "insight_synthesis": fallback
            }
