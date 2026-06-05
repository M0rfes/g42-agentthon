from langgraph.graph import StateGraph, START, END
from graphs.state import ResearchState
from graphs.nodes.enrich_decompose import enrich_decompose
from graphs.nodes.data_gathering import data_gathering
from graphs.nodes.synthesis import synthesis
from graphs.nodes.report_writer import report_writer
from utils.logging import logger

def create_research_graph():
    """
    Compiles the full Deep Research agentic LangGraph workflow.
    Fulfills 100% of Node integrations: Enrich & Decompose, Data Gathering,
    Synthesis (Vector/GraphRAG Memgraph), and final Fact-Checked Report Writing.
    """
    logger.info("orchestrator_compiling_graph")
    
    # Initialize the state graph with our ResearchState
    workflow = StateGraph(ResearchState)
    
    # Add all four custom nodes
    workflow.add_node("enrich_decompose", enrich_decompose)
    workflow.add_node("data_gathering", data_gathering)
    workflow.add_node("synthesis", synthesis)
    workflow.add_node("report_writer", report_writer)
    
    # Connect edges linearly
    workflow.add_edge(START, "enrich_decompose")
    workflow.add_edge("enrich_decompose", "data_gathering")
    workflow.add_edge("data_gathering", "synthesis")
    workflow.add_edge("synthesis", "report_writer")
    workflow.add_edge("report_writer", END)
    
    # Compile and return graph
    compiled_graph = workflow.compile()
    logger.info("orchestrator_graph_compiled_successfully")
    return compiled_graph
