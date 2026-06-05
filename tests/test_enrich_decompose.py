import os
import sys
import json
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging
from graphs.nodes.enrich_decompose import enrich_decompose

load_dotenv()
setup_logging()

def run_enrich_decompose_test():
    print("\n==================================================")
    print("RUNNING NODE 1: ENRICH AND DECOMPOSE VERIFICATION")
    print("==================================================")
    
    mock_state = {
        "query": "Should artificial intelligence coding assistants write code autonomously?",
        "research_plan": {},
        "paper_shortlist": [],
        "paper_summaries": [],
        "insight_synthesis": {},
        "research_report": "",
        "citation_source_list": [],
        "enriched_query": "",
        "search_topics": [],
        "scraped_data": [],
        "contradictions": []
    }
    
    print(f"Executing node with query: '{mock_state['query']}'...")
    try:
        updated_state = enrich_decompose(mock_state)
        
        print("\nNode execution completed successfully!")
        print("\n--- RESEARCH PLAN: ELABORATED QUERY ---")
        print(updated_state["research_plan"]["elaborated_query"])
        
        print("\n--- RESEARCH PLAN: REFINED SEARCH TOPICS ---")
        for idx, topic in enumerate(updated_state["research_plan"]["search_topics"], 1):
            print(f"{idx}. {topic}")
            
        # Assertions to confirm correctness
        assert len(updated_state["research_plan"]["elaborated_query"]) > 50, "Research plan elaborated query is too short or empty."
        assert len(updated_state["research_plan"]["search_topics"]) >= 3, "Research plan search topics list should have at least 3 queries."
        print("\n[SUCCESS] Node 1 state-aligned assertions completed successfully!")
        
    except AssertionError as ae:
        print(f"\n[ASSERTION ERROR] verification failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Node execution threw exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GITHUB_TOKEN"):
        print("\n[WARNING] Neither GITHUB_TOKEN nor OPENAI_API_KEY environment variable is set. Skipping LLM-based Node 1 tests.")
    else:
        run_enrich_decompose_test()
        
    print("\n==================================================")
    print("NODE 1 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")
