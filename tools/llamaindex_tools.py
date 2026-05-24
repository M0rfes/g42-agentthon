import os
import json
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from models.llm import get_langchain_llm
from models.index_manager import get_vector_index, get_property_graph_index
from utils.logging import logger, track_step, count_tokens

class FactCheckResult(BaseModel):
    verification_status: str = Field(description="Must be SUPPORTED, REFUTED, or UNVERIFIED based on the retrieved context")
    confidence_score: float = Field(description="Confidence score for this verdict, ranging from 0.0 to 1.0")
    explanation: str = Field(description="A highly detailed explanation analyzing the claim against the retrieved facts and identifying any support or contradictions")
    supporting_citations: list[str] = Field(description="List of URLs or document titles from the retrieved context that support this fact check")

@tool
def fact_checker(claim: str) -> str:
    """
    Fact-check an assertion/claim against all gathered research documents stored in LlamaIndex 
    and Memgraph GraphRAG. Returns a structured verdict (SUPPORTED, REFUTED, or UNVERIFIED) 
    with confidence, explanation, and citations.
    """
    with track_step("fact_checker", claim=claim) as metrics:
        logger.info("fact_checker_start", claim=claim)
        
        # 1. Retrieve from LlamaIndex Vector Index
        try:
            vector_index = get_vector_index()
            # If empty or not created, handled gracefully
            retriever = vector_index.as_retriever(similarity_top_k=4)
            nodes = retriever.retrieve(claim)
            vector_context = "\n\n".join([
                f"Source: {n.node.metadata.get('url', 'Unknown')} | Title: {n.node.metadata.get('title', 'Unknown')}\nContent: {n.node.get_content()}"
                for n in nodes
            ])
        except Exception as e:
            logger.warning("fact_checker_vector_retrieval_failed", error=str(e))
            vector_context = "No vector index context available."
            
        # 2. Retrieve from Memgraph Property Graph (GraphRAG)
        try:
            graph_index = get_property_graph_index()
            # Retrieve structured relationship paths matching the claim
            query_engine = graph_index.as_query_engine(include_text=True)
            graph_response = str(query_engine.query(
                f"Identify all key entities, facts, and relationships related to: '{claim}'"
            ))
        except Exception as e:
            logger.warning("fact_checker_graph_retrieval_failed", error=str(e))
            graph_response = "No knowledge graph relationships found."
            
        # Check if we have absolutely zero context gathered
        if not vector_context.strip() or vector_context == "No vector index context available.":
            logger.info("fact_checker_empty_index", claim=claim)
            result = {
                "verification_status": "UNVERIFIED",
                "confidence_score": 0.0,
                "explanation": "No documents have been gathered or indexed in LlamaIndex yet. Please run research queries first to gather context.",
                "supporting_citations": []
            }
            return json.dumps(result, indent=2)
            
        # 3. Compile context and prompt LLM using Pydantic structured output
        system_prompt = (
            "You are a scientific fact checker. Your job is to strictly evaluate the user's assertion/claim "
            "against the provided Vector Store Context and GraphRAG (Knowledge Graph) Context.\n\n"
            "Verdicts must follow these guidelines:\n"
            "- SUPPORTED: If the context directly supports or confirms the claim.\n"
            "- REFUTED: If the context directly contradicts or disproves the claim.\n"
            "- UNVERIFIED: If the context does not contain enough information to prove or disprove the claim.\n\n"
            "Do not use external knowledge beyond the provided contexts. If the contexts are empty or do not mention the claim, "
            "it MUST be UNVERIFIED."
        )
        
        user_content = (
            f"Assertion to evaluate: '{claim}'\n\n"
            f"--- Vector Context ---\n{vector_context}\n\n"
            f"--- GraphRAG Context ---\n{graph_response}\n"
        )
        
        try:
            # Setup Structured LLM using ChatOpenAI and Pydantic
            llm = get_langchain_llm()
            structured_llm = llm.with_structured_output(FactCheckResult)
            
            # Predict
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            # Count input tokens
            metrics["input_tokens"] += count_tokens(system_prompt + user_content)
            
            evaluation = structured_llm.invoke(messages)
            
            # Parse output
            result = {
                "verification_status": evaluation.verification_status,
                "confidence_score": evaluation.confidence_score,
                "explanation": evaluation.explanation,
                "supporting_citations": evaluation.supporting_citations
            }
            
            # Count output tokens
            metrics["output_tokens"] += count_tokens(json.dumps(result))
            
            logger.info("fact_checker_success", claim=claim, status=evaluation.verification_status)
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error("fact_checker_llm_failed", claim=claim, error=str(e))
            fallback = {
                "verification_status": "UNVERIFIED",
                "confidence_score": 0.0,
                "explanation": f"LLM Fact check execution error: {str(e)}",
                "supporting_citations": []
            }
            return json.dumps(fallback, indent=2)
