"""
Academic Paper Search Tools
============================
Provides two LangChain tools for retrieving peer-reviewed academic papers:

  1. openalex_search  — OpenAlex REST API (250M+ works, free, no key required)
                        Returns results sorted by citation count (most influential first).
                        Covers all disciplines: STEM, social science, humanities, etc.

  2. arxiv_search     — arXiv Atom API (CS/AI/Physics preprints, free, no key required)
                        Returns the most recent papers sorted by relevance.
                        Ideal for cutting-edge AI, ML, and software engineering research.

Both tools return a list of dicts with: title, url, snippet (abstract), source, year, citations.
They are drop-in compatible with the existing web_search tool output shape used in data_gathering.py.
"""

import time
import urllib.parse
import urllib.request
import json
import re
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from utils.logging import logger, track_step


# ── OpenAlex Search ───────────────────────────────────────────────────────────

_OPENALEX_BASE = "https://api.openalex.org/works"
_OPENALEX_CONTACT = "deep-research-agent@hackathon.ai"  # Polite pool: avoids rate limits

def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct an abstract string from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    try:
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_positions)
    except Exception:
        return ""


@tool
def openalex_search(query: str, max_results: int = 5) -> list:
    """
    Search OpenAlex (https://openalex.org) for peer-reviewed academic papers.
    Returns papers sorted by citation count (most influential papers first).
    Covers 250M+ works across all academic disciplines. Free, no API key required.
    Each result includes: title, url (DOI landing page), snippet (abstract), year, citations.
    """
    with track_step("openalex_search", query=query) as metrics:
        logger.info("openalex_search_start", query=query)

        params = urllib.parse.urlencode({
            "search": query,
            "per-page": min(max_results, 10),
            "sort": "cited_by_count:desc",
            "select": "title,doi,primary_location,open_access,publication_year,cited_by_count,abstract_inverted_index",
            "mailto": _OPENALEX_CONTACT,  # Polite pool header – higher rate limits
        })
        url = f"{_OPENALEX_BASE}?{params}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"DeepResearchAgent/1.0 (mailto:{_OPENALEX_CONTACT})"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("openalex_search_failed", query=query, error=str(e))
            return [{"error": f"OpenAlex search failed: {str(e)}"}]

        results = []
        for work in raw.get("results", []):
            title = work.get("title") or "Untitled"

            # Determine the best URL: prefer DOI, fall back to OA landing page
            doi = work.get("doi") or ""
            primary_loc = work.get("primary_location") or {}
            landing_url = (primary_loc.get("landing_page_url") or "") if primary_loc else ""
            oa = work.get("open_access") or {}
            oa_url = (oa.get("oa_url") or "") if oa else ""

            final_url = doi or landing_url or oa_url
            if not final_url or not final_url.startswith("http"):
                continue  # Skip entries with no valid URL

            abstract = _reconstruct_abstract(work.get("abstract_inverted_index") or {})
            year = work.get("publication_year") or ""
            citations = work.get("cited_by_count") or 0

            snippet = abstract[:400] if abstract else f"Published {year}. Cited {citations} times."

            results.append({
                "title": title,
                "url": final_url,
                "snippet": snippet,
                "source": "openalex",
                "year": year,
                "citations": citations,
            })

        logger.info("openalex_search_success", query=query, results_count=len(results))
        return results


# ── arXiv Search ──────────────────────────────────────────────────────────────

_ARXIV_BASE = "https://export.arxiv.org/api/query"
_ARXIV_NS = "http://www.w3.org/2005/Atom"


@tool
def arxiv_search(query: str, max_results: int = 5) -> list:
    """
    Search arXiv (https://arxiv.org) for preprint research papers.
    Best for cutting-edge AI, machine learning, and software engineering research.
    Results are sorted by relevance. Free, no API key required.
    Each result includes: title, url (arXiv abstract page), snippet (abstract), year.
    """
    with track_step("arxiv_search", query=query) as metrics:
        logger.info("arxiv_search_start", query=query)

        params = urllib.parse.urlencode({
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 10),
            "sortBy": "relevance",
            "sortOrder": "descending",
        })
        url = f"{_ARXIV_BASE}?{params}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DeepResearchAgent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_xml = resp.read().decode("utf-8")
        except Exception as e:
            logger.error("arxiv_search_failed", query=query, error=str(e))
            return [{"error": f"arXiv search failed: {str(e)}"}]

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError as e:
            logger.error("arxiv_xml_parse_failed", error=str(e))
            return [{"error": f"arXiv XML parse error: {str(e)}"}]

        ns = {"atom": _ARXIV_NS}
        results = []

        for entry in root.findall("atom:entry", ns):
            # Title
            title_elem = entry.find("atom:title", ns)
            title = (title_elem.text or "").strip().replace("\n", " ") if title_elem is not None else "Untitled"

            # Canonical arXiv abstract URL (use id tag, stripping API base if present)
            id_elem = entry.find("atom:id", ns)
            raw_id = (id_elem.text or "").strip() if id_elem is not None else ""
            # Normalize to https://arxiv.org/abs/XXXX.XXXXX format
            arxiv_id_match = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", raw_id)
            if arxiv_id_match:
                final_url = f"https://arxiv.org/abs/{arxiv_id_match.group(1)}"
            elif raw_id.startswith("http"):
                final_url = raw_id
            else:
                continue  # Skip entries with no valid URL

            # Abstract
            summary_elem = entry.find("atom:summary", ns)
            abstract = (summary_elem.text or "").strip().replace("\n", " ") if summary_elem is not None else ""

            # Published year
            published_elem = entry.find("atom:published", ns)
            year = ""
            if published_elem is not None and published_elem.text:
                year = published_elem.text[:4]

            snippet = abstract[:400] if abstract else f"arXiv preprint published {year}."

            results.append({
                "title": title,
                "url": final_url,
                "snippet": snippet,
                "source": "arxiv",
                "year": year,
                "citations": 0,  # arXiv does not provide citation counts
            })

        logger.info("arxiv_search_success", query=query, results_count=len(results))
        return results
