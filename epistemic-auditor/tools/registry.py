# tools/registry.py

from tools.search import WebSearchTool
from tools.credibility import CredibilityTool

class ToolRegistry:
    """
    The complete menu of tools available to the agent.
    
    Two responsibilities:
    1. Describe tools to the LLM (so it knows what to call)
    2. Execute tool calls (so the agent's decisions become actions)
    """

    def __init__(self):
        self.search = WebSearchTool()
        self.credibility = CredibilityTool()

        # This is what the LLM reads to decide which tool to use
        self.tool_descriptions = """
AVAILABLE TOOLS:

1. web_search(query: str)
   Use this to search for evidence about a claim or sub-claim.
   Call this multiple times with different queries to gather 
   comprehensive evidence. Good queries are specific and include
   context like "scientific evidence", "fact check", "origin of claim".
   Example: web_search("5G radiation biological effects peer reviewed")

2. check_credibility(url: str)
   Use this to verify how trustworthy a source is before citing it.
   Always call this for sources you plan to include in your final audit.
   Example: check_credibility("https://www.infowars.com/...")

HOW TO USE TOOLS:
When you want to call a tool, respond with ONLY this format:
TOOL_CALL: tool_name(argument)

Examples:
TOOL_CALL: web_search("microplastics found in human blood study 2023")
TOOL_CALL: check_credibility("https://pubmed.ncbi.nlm.nih.gov/12345")

After I give you the tool result, you can call another tool or 
produce your final JSON audit.
When you are ready to give the final answer, respond with:
FINAL_ANSWER: followed by your JSON.
"""

    def execute(self, tool_name: str, argument: str) -> str:
        """
        Execute whichever tool the LLM decided to call.
        Returns result as a string the LLM can read.
        """
        if tool_name == "web_search":
            results = self.search.run(argument.strip('"'))
            return self.search.format_for_prompt(results)

        elif tool_name == "check_credibility":
            result = self.credibility.run(argument.strip('"'))
            return (
                f"Credibility check for {result.domain}:\n"
                f"  Score: {result.score:.2f}/1.00\n"
                f"  Category: {result.category}\n"
                f"  {result.explanation}"
            )

        else:
            return f"Unknown tool: '{tool_name}'. Available: web_search, check_credibility"