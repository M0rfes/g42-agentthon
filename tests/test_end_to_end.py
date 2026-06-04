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
    
    url = "http://localhost:8000/run"
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
        
        print("\nVerifying standardized /run response fields:")
        assert data.get("status") == "success", "Status is not success."
        assert data.get("use_case_id"), "use_case_id is missing."
        assert data.get("trace_id"), "trace_id is missing."
        assert "runtime_seconds" in data, "runtime_seconds is missing."
        assert isinstance(data.get("agents_used"), list) and data.get("agents_used"), "agents_used is missing or empty."

        result = data.get("result") or {}
        assert isinstance(result, dict), "result is missing."
        summary = result.get("summary")
        recommendations = result.get("recommendations")
        artifacts = result.get("artifacts")

        print(f"1. Summary: {'[OK]' if summary else '[FAILED]'}")
        assert summary, "result.summary is missing or empty."
        print(f"2. Recommendations: {'[OK]' if recommendations is not None else '[FAILED]'}")
        assert recommendations is not None, "result.recommendations is missing."
        print(f"3. Artifacts: {'[OK]' if artifacts is not None else '[FAILED]'}")
        assert artifacts is not None, "result.artifacts is missing."

        print("\n--- SAMPLE OF SUMMARY ---")
        print(summary[:1000])
        print("\n... [Truncated for readability] ...")
        
        print("\n[SUCCESS] Standardized /run response verified!")
        
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
