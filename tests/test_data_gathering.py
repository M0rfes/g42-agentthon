import os
import sys
import json
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging
from graphs.nodes.data_gathering import data_gathering

load_dotenv()
setup_logging()

def run_data_gathering_test():
    print("\n==================================================")
    print("RUNNING NODE 2: DATA GATHERING VERIFICATION")
    print("==================================================")
    
    mock_state = {
        "query": "Should artificial intelligence coding assistants write code autonomously?",
        "research_plan": {
            "elaborated_query": "The query investigates the implications, benefits, and challenges of autonomous AI coding assistants...",
            "search_topics": [
                "autonomous AI coding assistants benefits",
                "autonomous AI coding assistants risks"
            ]
        },
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
    
    print(f"Executing Data Gathering node with {len(mock_state['research_plan']['search_topics'])} topics...")
    try:
        updated_state = data_gathering(mock_state)
        
        print("\nNode execution completed successfully!")
        
        print(f"\n--- PAPER SHORTLIST ({len(updated_state['paper_shortlist'])} found) ---")
        for idx, item in enumerate(updated_state["paper_shortlist"][:5], 1):
            print(f"{idx}. [{item['title']}]({item['url']})")
            
        print(f"\n--- INDIVIDUAL PAPER SUMMARIES ({len(updated_state['paper_summaries'])} generated) ---")
        for idx, item in enumerate(updated_state["paper_summaries"], 1):
            print(f"\nSummary {idx}: [{item['title']}]({item['url']}) [Relevance: {item['relevance_score']}]")
            print(f"Content: {item['summary']}")
            
        # Assertions to confirm correctness
        assert len(updated_state["paper_shortlist"]) > 0, "No papers were shortlisted during search."
        assert len(updated_state["paper_summaries"]) > 0, "No paper summaries were generated."
        assert len(updated_state["scraped_data"]) > 0, "No data was successfully scraped."
        
        print("\n[SUCCESS] Node 2 data-gathering assertions completed successfully!")
        
    except AssertionError as ae:
        print(f"\n[ASSERTION ERROR] verification failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Node execution threw exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GITHUB_TOKEN"):
        print("\n[WARNING] Neither GITHUB_TOKEN nor OPENAI_API_KEY environment variable is set. Skipping LLM-based Node 2 tests.")
    else:
        run_data_gathering_test()
        
    print("\n==================================================")
    print("NODE 2 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")
