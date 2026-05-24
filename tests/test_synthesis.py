import os
import sys
import json
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging
from graphs.nodes.synthesis import synthesis

load_dotenv()
setup_logging()

def run_synthesis_test():
    print("\n==================================================")
    print("RUNNING NODE 3: SYNTHESIS VERIFICATION")
    print("==================================================")
    
    mock_state = {
        "query": "Should artificial intelligence coding assistants write code autonomously?",
        "research_plan": {
            "elaborated_query": "The query investigates the implications, benefits, and challenges of autonomous AI coding assistants...",
            "search_topics": ["autonomous AI coding assistants benefits"]
        },
        "paper_shortlist": [],
        "paper_summaries": [],
        "insight_synthesis": {},
        "research_report": "",
        "citation_source_list": [],
        "enriched_query": "",
        "search_topics": [],
        "scraped_data": [
            {
                "url": "https://example.com/facts1",
                "title": "Efficiency of autonomous coding assistants",
                "text": (
                    "Google DeepMind's Antigravity assistant speeds up development by 50 percent for complex agentic workflows. "
                    "Autonomous coding assistants significantly reduce debugging overhead by automating test-driven development."
                )
            },
            {
                "url": "https://example.com/facts2",
                "title": "Risks of autonomous coding assistants",
                "text": (
                    "Autonomous coding assistants pose major security and quality challenges. "
                    "Security researchers identified that AI-generated code has a 40 percent vulnerability rate "
                    "due to legacy API signatures and insecure default prompts."
                )
            }
        ],
        "contradictions": []
    }
    
    print(f"Executing Synthesis node with {len(mock_state['scraped_data'])} scraped articles...")
    try:
        updated_state = synthesis(mock_state)
        
        print("\nNode execution completed successfully!")
        
        insight = updated_state["insight_synthesis"]
        
        print("\n--- INSIGHT SYNTHESIS: EXECUTIVE SUMMARY ---")
        print(insight["executive_summary"])
        
        print("\n--- INSIGHT SYNTHESIS: KEY THEMES ---")
        for idx, theme in enumerate(insight["key_themes"], 1):
            print(f"{idx}. {theme}")
            
        print("\n--- INSIGHT SYNTHESIS: EMPIRICAL FINDINGS ---")
        for idx, finding in enumerate(insight["empirical_findings"], 1):
            print(f"{idx}. {finding}")
            
        print("\n--- INSIGHT SYNTHESIS: GraphRAG ENTITIES & RELATIONSHIPS ---")
        for idx, relation in enumerate(insight["entities_and_relationships"], 1):
            print(f"{idx}. {relation}")
            
        # Assertions to confirm correctness
        assert len(insight["executive_summary"]) > 50, "Executive summary is too short or empty."
        assert len(insight["key_themes"]) > 0, "No key themes were synthesized."
        assert len(insight["empirical_findings"]) > 0, "No empirical findings were extracted."
        
        print("\n[SUCCESS] Node 3 synthesis assertions completed successfully!")
        
    except AssertionError as ae:
        print(f"\n[ASSERTION ERROR] verification failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Node execution threw exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GITHUB_TOKEN"):
        print("\n[WARNING] Neither GITHUB_TOKEN nor OPENAI_API_KEY environment variable is set. Skipping LLM-based Node 3 tests.")
    else:
        run_synthesis_test()
        
    print("\n==================================================")
    print("NODE 3 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")
