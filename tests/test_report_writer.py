import os
import sys
import json
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging
from graphs.nodes.report_writer import report_writer

load_dotenv()
setup_logging()

def run_report_writer_test():
    print("\n==================================================")
    print("RUNNING NODE 4: REPORT WRITER VERIFICATION")
    print("==================================================")
    
    mock_state = {
        "query": "Should artificial intelligence coding assistants write code autonomously?",
        "research_plan": {
            "elaborated_query": "The query investigates the implications, benefits, and challenges of autonomous AI coding assistants...",
            "search_topics": ["autonomous AI coding assistants benefits"]
        },
        "paper_shortlist": [
            {
                "title": "Efficiency of autonomous coding assistants",
                "url": "https://example.com/facts1"
            },
            {
                "title": "Risks of autonomous coding assistants",
                "url": "https://example.com/facts2"
            }
        ],
        "paper_summaries": [
            {
                "title": "Efficiency of autonomous coding assistants",
                "url": "https://example.com/facts1",
                "summary": "Google DeepMind's Antigravity assistant speeds up development by 50 percent for complex agentic workflows.",
                "relevance_score": 0.95
            },
            {
                "title": "Risks of autonomous coding assistants",
                "url": "https://example.com/facts2",
                "summary": "Autonomous coding assistants pose major security challenges with a 40 percent vulnerability rate in generated code.",
                "relevance_score": 0.88
            }
        ],
        "insight_synthesis": {
            "executive_summary": (
                "Synthesizing perspectives on autonomous AI coding assistants reveals a strong tension between "
                "developmental velocity (50% speedup) and codebase security (40% vulnerability rate)."
            ),
            "key_themes": [
                "Velocity vs Security Trade-offs",
                "Insecure Code Defaults",
                "Test-Driven Development (TDD) Mitigation"
            ],
            "empirical_findings": [
                "50% velocity boost with Antigravity assistant",
                "40% security vulnerability rate in AI-generated code"
            ],
            "entities_and_relationships": [
                "Antigravity -> Increases developer speed by 50%",
                "AI-generated code -> Has a 40% vulnerability rate"
            ]
        },
        "research_report": "",
        "citation_source_list": [],
        "enriched_query": "",
        "search_topics": [],
        "scraped_data": [
            {
                "url": "https://example.com/facts1",
                "title": "Efficiency of autonomous coding assistants",
                "text": "Google DeepMind's Antigravity assistant speeds up development by 50 percent for complex agentic workflows."
            },
            {
                "url": "https://example.com/facts2",
                "title": "Risks of autonomous coding assistants",
                "text": "Autonomous coding assistants pose major security challenges with a 40 percent vulnerability rate."
            }
        ],
        "contradictions": []
    }
    
    print("Executing Report Writer node...")
    try:
        updated_state = report_writer(mock_state)
        
        print("\nNode execution completed successfully!")
        
        report = updated_state["research_report"]
        citations = updated_state["citation_source_list"]
        
        print("\n--- RESEARCH REPORT DRAFT ---")
        print(report[:1500])
        if len(report) > 1500:
            print("\n... [Truncated for readability] ...")
            
        print("\n--- CITATION SOURCE LIST ---")
        for c in citations:
            print(f"[{c['id']}] {c['title']} - {c['url']}")
            
        # Assertions to confirm correctness
        assert len(report) > 200, "Research report is too short or empty."
        assert len(citations) > 0, "No citations were populated in the citation source list."
        
        print("\n[SUCCESS] Node 4 report writer assertions completed successfully!")
        
    except AssertionError as ae:
        print(f"\n[ASSERTION ERROR] verification failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Node execution threw exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GITHUB_TOKEN"):
        print("\n[WARNING] Neither GITHUB_TOKEN nor OPENAI_API_KEY environment variable is set. Skipping LLM-based Node 4 tests.")
    else:
        run_report_writer_test()
        
    print("\n==================================================")
    print("NODE 4 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")
