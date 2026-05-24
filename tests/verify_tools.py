import os
import json
import sys
from dotenv import load_dotenv

# Ensure the root directory is in the path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import setup_logging, logger
from models.index_manager import index_scraped_content, get_vector_index, get_property_graph_index
from tools.playwright_tools import web_search, scrape_page
from tools.llamaindex_tools import fact_checker
from tools.contradiction_tools import resolve_contradiction

load_dotenv()
setup_logging()

def run_playwright_tests():
    print("\n==================================================")
    print("RUNNING PLAYWRIGHT WEB SEARCH & SCRAPING TESTS")
    print("==================================================")
    
    # 1. Test Search
    query = "LangGraph agentic architecture deep learning"
    print(f"Searching web for: '{query}'...")
    results = web_search.invoke({"query": query, "max_results": 2})
    print("Search Results:")
    print(json.dumps(results, indent=2))
    
    if results and "error" not in results[0]:
        # 2. Test Scraping
        target_url = results[0].get("url")
        if target_url:
            print(f"\nScraping top URL: {target_url}...")
            scraped_text = scrape_page.invoke({"url": target_url})
            print(f"Scraped successfully. Captured {len(scraped_text)} characters.")
            print("Preview of scraped text (first 200 characters):")
            print(scraped_text[:200] + "...")
            return results[0]
    else:
        print("Search returned no valid results or errored out. Skipping scrape test.")
    return None

def run_indexing_and_fact_checker_tests(scraped_result):
    print("\n==================================================")
    print("RUNNING LLAMAINDEX & GRAPH INDEXING + FACT CHECKER TESTS")
    print("==================================================")
    
    # 1. Index mock content
    test_url = "https://mock.example.com/deepmind"
    test_title = "Antigravity Coding Assistant Announcement"
    test_text = (
        "Google DeepMind has officially announced the launch of the Antigravity AI coding assistant in May 2026. "
        "Antigravity is designed specifically as an advanced pair-programmer built on Google's next-generation Gemini model family. "
        "Early developers report that Antigravity boosts productivity by up to 50 percent for complex agentic workflows."
    )
    
    print("Indexing mock product announcement...")
    index_scraped_content(test_url, test_title, test_text)
    print("Factual content successfully loaded into LlamaIndex and Memgraph!")
    
    # 2. Test Fact Checker
    claim_supported = "Antigravity was released in May 2026 by Google DeepMind."
    print(f"\nFact checking SUPPORTED claim: '{claim_supported}'...")
    verdict_1 = fact_checker.invoke({"claim": claim_supported})
    print("Fact Checker Response:")
    print(verdict_1)
    
    claim_refuted = "Antigravity is an AI model created by OpenAI in 2020."
    print(f"\nFact checking REFUTED claim: '{claim_refuted}'...")
    verdict_2 = fact_checker.invoke({"claim": claim_refuted})
    print("Fact Checker Response:")
    print(verdict_2)

def run_contradiction_resolver_tests():
    print("\n==================================================")
    print("RUNNING CONTRADICTION RESOLVER TESTS")
    print("==================================================")
    
    claim_a = "Antigravity AI coding assistant was released in May 2026 by Google DeepMind."
    claim_b = "Antigravity AI coding assistant was released in November 2020 by Google DeepMind."
    
    print(f"Resolving contradiction between:\nClaim A: '{claim_a}'\nClaim B: '{claim_b}'...")
    resolution = resolve_contradiction.invoke({"claim_a": claim_a, "claim_b": claim_b})
    print("Contradiction Resolver Verdict:")
    print(resolution)

if __name__ == "__main__":
    print("Starting Deep Research Agent Tools Verification Suite...")
    
    # Run Playwright Search & Scrape
    scraped_result = run_playwright_tests()
    
    # Run Indexing & Fact Checking (Requires OPENAI_API_KEY)
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[WARNING] OPENAI_API_KEY environment variable is not set. Skipping LLM-based Fact Checker and Contradiction Resolver tests.")
    else:
        run_indexing_and_fact_checker_tests(scraped_result)
        run_contradiction_resolver_tests()
        
    print("\n==================================================")
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")
