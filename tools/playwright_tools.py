import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from langchain_core.tools import tool
from utils.logging import logger, track_step

@tool
def web_search(query: str, max_results: int = 5) -> list:
    """
    Search the web for real-time information and research papers using a zero-config engine.
    Returns a list of search results, each containing a title, URL, and snippet.
    """
    import base64
    import urllib.request
    
    with track_step("web_search", query=query) as metrics:
        logger.info("playwright_search_start", query=query)
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
        except Exception as e:
            logger.error("playwright_search_failed", query=query, error=str(e))
            return [{"error": f"Search failed: {str(e)}"}]
            
        soup = BeautifulSoup(content, "html.parser")
        results = []
        
        for algo in soup.select(".b_algo")[:max_results]:
            title_elem = algo.select_one("h2 a")
            snippet_elem = algo.select_one(".b_caption p") or algo.select_one(".b_snippet") or algo.select_one("p")
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                raw_href = title_elem["href"]
                
                # Decode Bing base64 redirect link to get the clean target URL
                href = raw_href
                try:
                    parsed = urllib.parse.urlparse(raw_href)
                    query_params = urllib.parse.parse_qs(parsed.query)
                    if "u" in query_params:
                        u_val = query_params["u"][0]
                        if u_val.startswith("a1"):
                            base64_str = u_val[2:]
                            # Add correct base64 padding
                            base64_str += "=" * ((4 - len(base64_str) % 4) % 4)
                            href = base64.urlsafe_b64decode(base64_str).decode("utf-8")
                except Exception as e:
                    logger.debug("bing_url_decode_error", error=str(e))
                
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet
                })
        
        logger.info("playwright_search_success", query=query, results_count=len(results))
        return results

@tool
def scrape_page(url: str) -> str:
    """
    Scrapes the text content of a webpage or research resource, stripping out structural layouts 
    (headers, footers, scripts, styles), and returns clean plain text content.
    """
    with track_step("scrape_page", url=url) as metrics:
        logger.info("playwright_scrape_start", url=url)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Custom user agent to prevent basic scraping blocks
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    ignore_https_errors=True
                )
                page = context.new_page()
                
                # Block resource types we do not need (images, css, fonts, media) for speed
                page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
                
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                content = page.content()
                browser.close()
        except Exception as e:
            logger.error("playwright_scrape_failed", url=url, error=str(e))
            return f"Error scraping {url}: {str(e)}"
            
        soup = BeautifulSoup(content, "html.parser")
        
        # Remove structural clutter
        for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
            element.extract()
            
        text = soup.get_text(separator="\n")
        
        # Clean whitespaces and empty lines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase for line in lines for phrase in line.split("  "))
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Cap text payload to avoid context/token overflow (10,000 characters)
        final_text = cleaned_text[:10000]
        
        logger.info("playwright_scrape_success", url=url, payload_size=len(final_text))
        return final_text
