# tools/search.py

from ddgs import DDGS
from dataclasses import dataclass
from logger import get_logger

log = get_logger("search_tool")

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

class WebSearchTool:
    name = "web_search"
    description = "Search the web for music, films, or cultural references"

    def run(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                    ))
            log.info(f"Search '{query[:50]}' returned {len(results)} results")
            return results
        except Exception as e:
            log.error(f"Search failed: {e}")
            return []

    def format_for_prompt(self, results: list[SearchResult]) -> str:
        if not results:
            return "No search results found. Use your knowledge to recommend."
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r.title}\n"
                f"    {r.snippet}"
            )
        return "\n\n".join(formatted)