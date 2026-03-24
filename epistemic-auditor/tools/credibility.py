# tools/credibility.py

from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class CredibilityResult:
    url: str
    domain: str
    score: float          # 0.0 (junk) to 1.0 (highly credible)
    category: str         # "scientific" | "news" | "government" | "unknown" | "unreliable"
    explanation: str

class CredibilityTool:
    """
    Scores a URL's credibility based on its domain.
    
    In production this would call a proper media bias API.
    For learning, we use a curated lookup table — the pattern
    is identical, just the data source changes.
    """

    name = "check_credibility"
    description = "Check how credible a source URL is before citing it"

    # Curated credibility map
    # Pattern: (score, category)
    KNOWN_DOMAINS = {
        # Scientific / academic
        "pubmed.ncbi.nlm.nih.gov":  (0.97, "scientific"),
        "nature.com":               (0.96, "scientific"),
        "science.org":              (0.96, "scientific"),
        "thelancet.com":            (0.95, "scientific"),
        "nejm.org":                 (0.95, "scientific"),
        "who.int":                  (0.94, "government"),
        "cdc.gov":                  (0.94, "government"),
        "nih.gov":                  (0.93, "government"),
        "scholar.google.com":       (0.90, "scientific"),
        "arxiv.org":                (0.82, "scientific"),

        # Fact checkers
        "snopes.com":               (0.88, "fact_check"),
        "factcheck.org":            (0.88, "fact_check"),
        "politifact.com":           (0.85, "fact_check"),
        "fullfact.org":             (0.85, "fact_check"),

        # Mainstream news
        "bbc.com":                  (0.80, "news"),
        "reuters.com":              (0.82, "news"),
        "apnews.com":               (0.83, "news"),
        "theguardian.com":          (0.78, "news"),
        "nytimes.com":              (0.78, "news"),

        # Known unreliable
        "infowars.com":             (0.05, "unreliable"),
        "naturalnews.com":          (0.08, "unreliable"),
        "beforeitsnews.com":        (0.05, "unreliable"),
    }

    def run(self, url: str) -> CredibilityResult:
        try:
            domain = urlparse(url).netloc.lower()
            # strip www.
            domain = domain.removeprefix("www.")

            if domain in self.KNOWN_DOMAINS:
                score, category = self.KNOWN_DOMAINS[domain]
                explanation = self._explain(score, category, domain)
            else:
                # Unknown domain — neutral score, flag it
                score = 0.5
                category = "unknown"
                explanation = f"'{domain}' is not in our credibility database. Treat with moderate caution."

            return CredibilityResult(
                url=url,
                domain=domain,
                score=score,
                category=category,
                explanation=explanation,
            )
        except Exception as e:
            return CredibilityResult(
                url=url, domain="", score=0.0,
                category="unknown",
                explanation=f"Could not check credibility: {e}"
            )

    def _explain(self, score: float, category: str, domain: str) -> str:
        if score >= 0.90:
            return f"'{domain}' is a highly credible {category} source."
        elif score >= 0.75:
            return f"'{domain}' is a generally reliable {category} source."
        elif score >= 0.50:
            return f"'{domain}' has moderate credibility. Verify independently."
        else:
            return f"'{domain}' is considered unreliable. Do not cite."