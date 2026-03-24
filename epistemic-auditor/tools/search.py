# tools/search.py

from ddgs import DDGS  # pyright: ignore[reportMissingImports]
from dataclasses import dataclass

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

class WebSearchTool:
    """
    Searches the web and returns structured results.
    
    The agent calls this when it needs evidence for a claim.
    """
    
    name = "web_search"
    description = "Search the web for information about a claim or topic"

    def run(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """
        Run a web search. Returns a list of results.
        
        If search fails, returns empty list — NEVER raises.
        The agent must handle empty results gracefully.
        This is our first failure mode defense from Stage 1.
        """
        try:
            results = []
            for r in DDGS().text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
            return results

        except Exception as e:
            # Production gotcha: never let a tool failure crash the agent
            # Log it, return empty, let the agent decide what to do
            print(f"[SearchTool] Search failed: {e}")
            return []

    def format_for_prompt(self, results: list[SearchResult]) -> str:
        """
        Converts search results into text the LLM can read.
        This is called 'tool result formatting' — crucial for 
        how well the LLM reasons about evidence.
        """
        if not results:
            return "No search results found. Reason from what you know, but flag uncertainty."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r.title}\n"
                f"    URL: {r.url}\n"
                f"    {r.snippet}"
            )
        return "\n\n".join(formatted)