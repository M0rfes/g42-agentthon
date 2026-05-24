import os
import sys
import json
import requests
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging

load_dotenv()
setup_logging()

def run_end_to_end_test():
    print("\n==================================================")
    print("RUNNING END-TO-END DEEP RESEARCH FLOW VERIFICATION")
    print("==================================================")
    
    url = "http://localhost:8000/research"
    payload = {
        "query": "Should artificial intelligence coding assistants write code autonomously?"
    }
    
    print(f"Triggering deep research flow on server at {url}...")
    print(f"Query: '{payload['query']}'")
    print("This runs the entire LangGraph workflow (4 nodes, search, scraping, Vector/GraphRAG ingestion, and report generation).")
    print("Waiting for response...")
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        
        print(f"\nResponse Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[ERROR] API request failed: {response.text}")
            sys.exit(1)
            
        data = response.json()
        
        print("\nAPI Response successfully received!")
        print(f"Keys returned in response: {list(data.keys())}")
        
        # We assert the 6 expected judge outputs are populated
        print("\nVerifying the 6 expected outputs required by judges:")
        
        # 1. Research Plan
        research_plan = data.get("research_plan")
        print(f"1. Research Plan: {'[OK]' if research_plan else '[FAILED]'}")
        assert research_plan, "Research plan is missing or empty."
        
        # 2. Paper Shortlist
        paper_shortlist = data.get("paper_shortlist")
        print(f"2. Paper Shortlist: {'[OK]' if paper_shortlist else '[FAILED]'} (Count: {len(paper_shortlist)})")
        assert len(paper_shortlist) > 0, "Paper shortlist is empty."
        
        # 3. Individual Paper Summaries
        paper_summaries = data.get("paper_summaries")
        print(f"3. Paper Summaries: {'[OK]' if paper_summaries else '[FAILED]'} (Count: {len(paper_summaries)})")
        assert len(paper_summaries) > 0, "Paper summaries is empty."
        
        # 4. Insight Synthesis
        insight_synthesis = data.get("insight_synthesis")
        print(f"4. Insight Synthesis: {'[OK]' if insight_synthesis else '[FAILED]'}")
        assert insight_synthesis, "Insight synthesis is missing or empty."
        
        # 5. Research Report
        research_report = data.get("research_report")
        print(f"5. Research Report: {'[OK]' if research_report else '[FAILED]'} (Length: {len(research_report)} chars)")
        assert len(research_report) > 100, "Research report is empty or too short."
        
        # 6. Citation or Source List
        citation_source_list = data.get("citation_source_list")
        print(f"6. Citation/Source List: {'[OK]' if citation_source_list else '[FAILED]'} (Count: {len(citation_source_list)})")
        assert len(citation_source_list) > 0, "Citation source list is empty."
        
        print("\n--- SAMPLE OF RESEARCH REPORT ---")
        print(research_report[:1000])
        print("\n... [Truncated for readability] ...")
        
        print("\n[SUCCESS] All 6 expected judge outputs verified and present!")
        
    except requests.exceptions.RequestException as re:
        print(f"\n[CONNECTION ERROR] Server could not be reached: {str(re)}")
        sys.exit(1)
    except AssertionError as ae:
        print(f"\n[ASSERTION ERROR] Verification failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected exception during test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_end_to_end_test()
    print("\n==================================================")
    print("END-TO-END DEEP RESEARCH VERIFICATION COMPLETED!")
    print("==================================================")
