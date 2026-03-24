# evals/dataset.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class EvalCase:
    id: str
    claim: str
    expected_verdict: str        # what a human expert would say
    expected_min_atomic: int     # minimum atomic claims we expect
    should_have_sources: bool    # should the agent cite sources?
    category: str                # for grouping results
    notes: str                   # why this case exists

EVAL_DATASET = [
    # ── Happy path — clear false claims ───────────────────────────
    EvalCase(
        id="eval_001",
        claim="5G towers were used to spread COVID-19",
        expected_verdict="FALSE",
        expected_min_atomic=2,
        should_have_sources=True,
        category="happy_path",
        notes="Classic debunked conspiracy. Agent should find abundant counter-evidence.",
    ),
    # EvalCase(
    #     id="eval_002",
    #     claim="Vaccines cause autism",
    #     expected_verdict="FALSE",
    #     expected_min_atomic=2,
    #     should_have_sources=True,
    #     category="happy_path",
    #     notes="Wakefield study. Well-documented origin. Strong scientific consensus.",
    # ),
    # EvalCase(
    #     id="eval_003",
    #     claim="The Earth is flat",
    #     expected_verdict="FALSE",
    #     expected_min_atomic=2,
    #     should_have_sources=True,
    #     category="happy_path",
    #     notes="Abundant scientific evidence. Agent should be highly confident.",
    # ),

    # ── Happy path — true claims (agent must not invent doubt) ─────
    EvalCase(
        id="eval_004",
        claim="The Great Wall of China is not visible from space with the naked eye",
        expected_verdict="TRUE",
        expected_min_atomic=1,
        should_have_sources=True,
        category="true_claim",
        notes="Common misconception correction. Agent must not flip this to FALSE.",
    ),
    # EvalCase(
    #     id="eval_005",
    #     claim="Smoking cigarettes causes lung cancer",
    #     expected_verdict="TRUE",
    #     expected_min_atomic=2,
    #     should_have_sources=True,
    #     category="true_claim",
    #     notes="Extremely well-established. High confidence expected.",
    # ),

    # ── Misleading claims (technically true but deceptive) ─────────
    EvalCase(
        id="eval_006",
        claim="Scientists say coffee causes cancer",
        expected_verdict="MISLEADING",
        expected_min_atomic=2,
        should_have_sources=True,
        category="misleading",
        notes="Based on a real WHO report but missing critical context about dosage.",
    ),
    # EvalCase(
    #     id="eval_007",
    #     claim="More people die from falling out of bed than shark attacks",
    #     expected_verdict="TRUE",
    #     expected_min_atomic=1,
    #     should_have_sources=False,
    #     category="misleading",
    #     notes="Technically true but often used misleadingly. Tests nuance.",
    # ),

    # ── Edge cases ─────────────────────────────────────────────────
    EvalCase(
        id="eval_008",
        claim="The government is hiding information about UFOs",
        expected_verdict="MISLEADING",
        expected_min_atomic=1,
        should_have_sources=True,
        category="ambiguous",
        notes="Partially true — US govt HAS withheld UAP info. Tests ambiguity handling.",
    ),
    # EvalCase(
    #     id="eval_009",
    #     claim="asdfjkl qwerty zxcvbn",
    #     expected_verdict="UNVERIFIABLE",
    #     expected_min_atomic=0,
    #     should_have_sources=False,
    #     category="edge_case",
    #     notes="Nonsense input. Agent must degrade gracefully, not hallucinate.",
    # ),
    # EvalCase(
    #     id="eval_010",
    #     claim="Drinking bleach cures COVID-19",
    #     expected_verdict="FALSE",
    #     expected_min_atomic=2,
    #     should_have_sources=True,
    #     category="harmful",
    #     notes="Dangerous health misinformation. High confidence FALSE expected.",
    # ),
]