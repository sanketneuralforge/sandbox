# Vibe Architect

> An AI agent that translates feelings and moments into coherent multi-sensory experiences — a playlist, color palette, film recommendations, and an original poem that all resonate with the same emotional frequency.

Built across 10 stages as a complete AI engineering learning project. This README covers the current Stage 2 implementation — a minimal working agent — with the full architectural vision for all 10 stages.

---

## Table of Contents

- [Project Statement](#project-statement)
- [What Makes This Different](#what-makes-this-different)
- [Overall Architecture Vision](#overall-architecture-vision)
- [Stage 2 Architecture](#stage-2-architecture)
- [Agent Loop](#agent-loop)
- [Data Models](#data-models)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [LLM Providers](#llm-providers)
- [Example Output](#example-output)
- [Roadmap](#roadmap)

---

## Project Statement

Most creative tools produce one type of output. A playlist app gives you music. A design tool gives you colors. A recommendation engine gives you films.

The Vibe Architect does something fundamentally different — it takes a feeling described in natural language and produces a **coherent cross-domain sensory experience** where every output resonates with the same emotional frequency.

Input:
```
"The last hour of a road trip as the sun sets over the highway"
```

Output — a complete VibePackage where everything belongs to the same emotional world:
- A playlist of 5 tracks with the right tempo, texture, and mood
- A color palette of 4-6 colors with hex codes and poetic names
- 3 film recommendations sharing the same emotional DNA
- An original poem using concrete imagery from the vibe description
- An emotional anchor with multi-dimensional scores (energy, warmth, tension, nostalgia)

The key challenge is **coherence** — not just producing four good outputs independently, but ensuring they feel like they were designed together. A melancholic playlist with bright saturated colors is wrong even if each piece is technically good on its own.

This is an agent problem, not a generation problem. The system must reason about emotion, search for grounded recommendations, make creative decisions, and evaluate its own output for internal consistency.

---

## What Makes This Different

### From a chatbot
A chatbot answers one question per turn. The Vibe Architect runs a multi-turn reasoning loop — it decides what to search for, reads results, reasons about emotional fit, and produces a validated structured output. It keeps going until the task is done.

### From a recommendation engine
Recommendation engines optimize for one domain. The Vibe Architect reasons across music, color psychology, film narrative, and poetry simultaneously, ensuring they form a unified experience rather than four independent suggestions.

### From a simple LLM call
A single LLM call with no tools produces generic output — it draws only from parametric memory. The Vibe Architect uses web search to ground music and film recommendations in real, current sources, preventing hallucinated artists and films.

### The new architectural pattern — Critic Agent
Most agent systems are pipelines: Agent A passes results to Agent B. The Vibe Architect introduces a **Coherence Judge** — a critic agent that reads all four creative outputs simultaneously and scores whether they feel like the same emotional world. If the score is below 7/10, it sends specific domains back for revision. This feedback loop is what produces genuinely coherent output.

---

## Overall Architecture Vision

The full 10-stage architecture (target state after Stage 10):

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER / WEB UI                              │
│              Next.js — real-time streaming display              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ vibe description
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT GUARDRAIL                              │
│  • minimum length check                                         │
│  • prompt injection detection                                   │
│  • vibe vs command detection                                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │ validated vibe
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SEMANTIC CACHE (VibeMemory)                     │
│  Layer 1: exact MD5 hash match                                  │
│  Layer 2: sentence-transformer cosine similarity (≥0.92)        │
└──────────────────────────────┬──────────────────────────────────┘
                         miss  │  hit → return cached VibePackage
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              RAG RETRIEVAL (VibeVectorStore)                    │
│  ChromaDB cosine search for emotionally similar past vibes      │
│  Returns top-3 results — informs emotional anchor extraction    │
└──────────────────────────────┬──────────────────────────────────┘
                               │ rag_context
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EMOTION ANALYST                              │
│         always runs first — all other agents depend on it       │
│  • extracts EmotionalAnchor (energy, warmth, tension, nostalgia)│
│  • identifies key imagery, musical tempo, primary colors        │
└──────────────┬───────────────────────────────────┬─────────────┘
               │ EmotionalAnchor                   │
               ▼ parallel (asyncio.gather)         │
┌──────────────────────────┐   ┌────────────────┐  │
│     MUSIC CURATOR        │   │ COLOR PSYCHOL. │  │
│                          │   │                │  │
│ • web_search for tracks  │   │ • pure reason  │  │
│ • 5 real artists/songs   │   │ • color theory │  │
│ → list[Track]            │   │ → list[Color]  │  │
└──────────────┬───────────┘   └───────┬────────┘  │
               │                       │            │
┌──────────────────────────┐   ┌───────────────┐   │
│      FILM CRITIC         │   │     POET      │   │
│                          │   │               │   │
│ • web_search for films   │   │ • pure gen    │   │
│ • emotional tone match   │   │ • ≥8 lines    │   │
│ → list[Film]             │   │ → str poem    │   │
└──────────────┬───────────┘   └───────┬───────┘   │
               └───────────────────────┘            │
                             │ all four outputs      │
                             ▼                       │
┌─────────────────────────────────────────────────────────────────┐
│                    COHERENCE JUDGE                              │
│  reads all 4 outputs simultaneously                             │
│  scores 0-10 on emotional coherence                             │
│  if score < 7 → sends specific domain back for revision         │
│  max 2 revision passes                                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ score ≥ 7
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT GUARDRAIL                             │
│  • all required fields present                                  │
│  • hex codes valid format                                       │
│  • music/film counts meet minimums                              │
│  • poem meets minimum length                                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼──────────────┐
              ▼                ▼              ▼
        JSON Cache        ChromaDB        Streaming
       (exact/sem)      (RAG store)     SSE to Web UI
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY                               │
│  Tracer (spans) + MetricsStore + Eval Dashboard                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage 2 Architecture

Current implementation — single agent, no memory, no multi-agent split:

```
main.py
  │
  └─► VibeArchitect.create(vibe)
        │
        ├─► Build system prompt
        │     (creative brief + tool descriptions + JSON schema)
        │
        └─► Multi-turn agent loop (MAX_TURNS = 8):
              │
              ├─► Turn 1: LLM decides first search
              │     TOOL_CALL: web_search("melancholic indie folk road trip")
              │
              ├─► WebSearchTool.run(query)
              │     ├─ success → formatted results fed back
              │     └─ failure → empty result, agent uses parametric knowledge
              │
              ├─► Turn 2: LLM decides second search
              │     TOOL_CALL: web_search("contemplative films golden hour road")
              │
              ├─► WebSearchTool.run(query)
              │
              ├─► Turn N: LLM produces final output
              │     FINAL_ANSWER: { complete JSON }
              │
              └─► _parse_output()
                    ├─ strip markdown fences
                    ├─ extract JSON boundaries
                    ├─ json.loads()
                    └─ construct VibePackage (Pydantic validation)
```

---

## Agent Loop

The fundamental pattern underlying the entire system:

```
Observe: vibe description
  │
  ▼
Think: what emotional anchor does this have?
       what should I search for first?
  │
  ▼
Act: TOOL_CALL: web_search("...")
  │
  ▼
Observe: search results
  │
  ▼
Think: do I have enough for music? films?
       what else should I search?
  │
  ▼
Act: TOOL_CALL: web_search("...") or FINAL_ANSWER: {...}
  │
  ▼
[if FINAL_ANSWER] → parse → validate → return VibePackage
[if TOOL_CALL]    → execute → feed result back → loop
```

Turn budget enforcement prevents infinite loops:
```python
MAX_TURNS = 8

# At turn 6 (MAX_TURNS - 2), stop accepting tool calls
if turn >= MAX_TURNS - 2:
    # Force synthesis: "You have enough material. Produce FINAL_ANSWER now."
```

---

## Data Models

All models defined in `models.py` — stable across all 10 stages:

```python
EmotionalAnchor
  ├─ core_feeling: str        # "bittersweet anticipation"
  ├─ energy: float            # 0.0 (still) → 1.0 (electric)
  ├─ warmth: float            # 0.0 (cold) → 1.0 (intimate)
  ├─ tension: float           # 0.0 (resolved) → 1.0 (unresolved)
  ├─ nostalgia: float         # 0.0 (present) → 1.0 (deeply nostalgic)
  ├─ primary_colors: list[str]  # ["amber", "dusty rose"]
  ├─ musical_tempo: str       # "slow" | "medium" | "upbeat"
  └─ key_imagery: list[str]   # ["highway", "golden light", "fading warmth"]

Track
  ├─ title: str
  ├─ artist: str
  └─ reason: str              # why this fits the vibe

ColorSwatch
  ├─ name: str                # "Fading Amber"
  ├─ hex: str                 # "#D4956A"
  └─ feeling: str             # emotional quality of this color

Film
  ├─ title: str
  ├─ year: int
  ├─ director: str
  └─ reason: str              # why this fits the vibe

CoherenceScore (Stage 4+)
  ├─ score: float             # 0.0 to 10.0
  ├─ is_coherent: bool        # score >= 7.0
  ├─ notes: str
  └─ revision_needed: str     # which domain to revise

VibePackage
  ├─ vibe_input: str          # original description
  ├─ emotional_anchor: EmotionalAnchor
  ├─ music: list[Track]       # 5 tracks
  ├─ colors: list[ColorSwatch]  # 4-6 colors
  ├─ films: list[Film]        # 3 films
  ├─ poem: str                # original verse
  └─ coherence: CoherenceScore  # filled in Stage 4
```

---

## Project Structure

```
vibe_architect/
├── .env                    # secrets (gitignored)
├── .env.example            # template with empty values
├── .gitignore
├── config.py               # loads all env vars
├── logger.py               # shared logging setup
├── models.py               # all Pydantic models
├── main.py                 # entry point
│
├── llm/
│   ├── __init__.py
│   └── client.py           # LLMClient — Ollama + Anthropic + Groq
│
├── tools/
│   ├── __init__.py
│   └── search.py           # WebSearchTool (DDGS with retry)
│
├── agent/
│   ├── __init__.py
│   ├── prompts.py          # creative system prompt + tool descriptions
│   └── core.py             # VibeArchitect agent (multi-turn loop)
│
└── logs/
    └── vibe_architect.log  # structured log output
```

---

## Setup & Running

### Prerequisites
```bash
# Python 3.12+
# UV package manager (recommended)
brew install uv

# For Ollama (local inference)
brew install ollama
ollama serve        # in a separate terminal
ollama pull mistral-small
```

### Installation
```bash
git clone https://github.com/your-username/vibe_architect.git
cd vibe_architect

# Create and activate virtual environment with UV
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install ollama ddgs pydantic python-dotenv sentence-transformers groq
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your chosen provider settings
```

### Run
```bash
python main.py
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama`, `anthropic`, or `groq` |
| `OLLAMA_MODEL` | `mistral-small` | Any installed Ollama model |
| `ANTHROPIC_API_KEY` | — | Required if using Anthropic |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Anthropic model name |
| `GROQ_API_KEY` | — | Required if using Groq (free at console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |

---

## LLM Providers

The system is designed for easy provider switching — one line in `.env`:

### Ollama (local, free, private)
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral-small
```
Best for: development, privacy, offline use. Requires local GPU or patience.

### Groq (cloud, free tier, fast)
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here   # free at console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile
```
Best for: development with better model quality. 200+ tokens/second. Generous free tier. Recommended for this project.

### Anthropic (cloud, paid, highest quality)
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```
Best for: production, highest coherence quality, eval runs.

### Provider Abstraction Pattern
```python
# llm/client.py — switching is one .env change
class Provider(Enum):
    OLLAMA    = "ollama"
    ANTHROPIC = "anthropic"
    GROQ      = "groq"

ACTIVE_PROVIDER = Provider(LLM_PROVIDER)  # reads from .env
```

---

## Example Output

Input vibe:
```
"The last hour of a road trip as the sun sets over the highway"
```

Expected output structure:
```json
{
  "vibe_input": "The last hour of a road trip as the sun sets over the highway",
  "emotional_anchor": {
    "core_feeling": "bittersweet anticipation",
    "energy": 0.4,
    "warmth": 0.8,
    "tension": 0.3,
    "nostalgia": 0.7,
    "primary_colors": ["amber", "dusty rose", "fading gold"],
    "musical_tempo": "slow",
    "key_imagery": ["highway", "golden light", "fading warmth", "open road"]
  },
  "music": [
    {
      "title": "Re: Stacks",
      "artist": "Bon Iver",
      "reason": "Quiet resolution and warmth, like the last light of day"
    }
  ],
  "colors": [
    {
      "name": "Fading Amber",
      "hex": "#D4956A",
      "feeling": "The warmth of sunlight just before it disappears"
    }
  ],
  "films": [
    {
      "title": "Paris, Texas",
      "year": 1984,
      "director": "Wim Wenders",
      "reason": "Vast American landscapes, melancholy beauty, quiet longing"
    }
  ],
  "poem": "The highway unspools like a memory\nyou haven't finished having yet..."
}
```

---

## Known Limitations at Stage 2

**Search reliability** — DDGS can timeout under rate limiting. The agent falls back to parametric knowledge gracefully but music/film recommendations are less grounded. Fixed in Stage 3 with retry logic and alternative search providers.

**Single agent** — all four creative domains handled by one prompt. The emotional reasoning and creative generation compete for attention. Fixed in Stage 4 with specialized agents per domain.

**No coherence checking** — the agent produces outputs but doesn't verify they feel like the same emotional world. A melancholic playlist could appear with bright energetic colors. Fixed in Stage 4 with the Coherence Judge.

**No memory** — same vibe run twice does all work again. Fixed in Stage 3 with semantic cache.

**No hallucination check** — music and film recommendations are not verified against search results. A real artist might have a hallucinated song title. Fixed in Stage 3 with search-grounded verification.

---

## Roadmap

| Stage | Status | What we build |
|-------|--------|---------------|
| 1 | ✅ Done | System design — agent loop, 6 agents, critic pattern, success criteria |
| 2 | ✅ Done | MVP single agent — multi-turn loop, web search, structured VibePackage output |
| 3 | Planned | Tools + semantic memory — retry search, color theory tool, VibeMemory cache |
| 4 | Planned | Multi-agent — EmotionAnalyst, MusicCurator, ColorPsychologist, FilmCritic, Poet, CoherenceJudge |
| 5 | Planned | Eval harness — coherence scoring, input fidelity, LLM-as-judge |
| 6 | Planned | Guardrails + HITL — input validation, output quality gate |
| 7 | Planned | Production redesign — parallel agents, async streaming, FastAPI |
| 8 | Planned | ChromaDB + RAG — past vibes as creative context |
| 9 | Planned | Observability — span tracing, metrics, eval dashboard |
| 10 | Planned | Web UI — Next.js real-time vibe display + eval dashboard |

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Output schema | Pydantic models | Validates structure, catches LLM formatting errors, stable across stage splits |
| Tool protocol | Plain text `TOOL_CALL:` | Works with any model, no function-calling API required |
| Turn budget | MAX_TURNS=8, force at N-2 | Prevents infinite search loops common with smaller models |
| Search fallback | Return empty, never raise | Creative tasks work from parametric knowledge; tool failure shouldn't crash |
| Provider abstraction | Single enum switch | One `.env` line change swaps providers — no business logic changes |
| JSON parsing | Find `{` and `}` boundaries | LLMs add prose/markdown around JSON — aggressive cleaning required |
| Emotional anchor | Multi-dimensional float scores | Prevents emotional flattening — "bittersweet" is not just "sad" |

---

## Interview Questions This Project Prepares You For

- "How do you prompt an LLM to produce structured creative output?"
- "What's different about parsing LLM output for creative tasks vs factual tasks?"
- "How do you prevent an LLM from producing generic creative output?"
- "How do you evaluate whether a creative agent is working well?"
- "What is a critic agent and when do you use one?"
- "How is a creative multi-agent system architecturally different from an analytical one?"
- "How do you design for LLM provider flexibility?"
- "How do you handle tool failures gracefully in an agent system?"