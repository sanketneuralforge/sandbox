# models.py

from pydantic import BaseModel
from typing import Optional

class EmotionalAnchor(BaseModel):
    """
    The core emotional fingerprint of a vibe.
    Multi-dimensional — not just a single mood label.
    This is what prevents emotional flattening.
    """
    core_feeling: str          # e.g. "bittersweet anticipation"
    energy: float              # 0.0 (still) to 1.0 (electric)
    warmth: float              # 0.0 (cold/distant) to 1.0 (warm/intimate)
    tension: float             # 0.0 (resolved) to 1.0 (unresolved)
    nostalgia: float           # 0.0 (present) to 1.0 (deeply nostalgic)
    primary_colors: list[str]  # color words that feel right, e.g. ["amber", "dusty rose"]
    musical_tempo: str         # "slow" | "medium" | "upbeat"
    key_imagery: list[str]     # concrete images from the vibe, e.g. ["highway", "golden light"]

class Track(BaseModel):
    """One music recommendation."""
    title: str
    artist: str
    reason: str    # why this track fits the vibe

class ColorSwatch(BaseModel):
    """One color in the palette."""
    name: str       # poetic name, e.g. "Fading Amber"
    hex: str        # e.g. "#D4956A"
    feeling: str    # what emotional quality this color carries

class Film(BaseModel):
    """One film recommendation."""
    title: str
    year: int
    director: str
    reason: str     # why this film fits the vibe

class CoherenceScore(BaseModel):
    """Output of the Coherence Judge agent (Stage 4)."""
    score: float           # 0.0 to 10.0
    is_coherent: bool      # score >= 7.0
    notes: str             # what works, what doesn't
    revision_needed: Optional[str] = None  # which domain to revise

class VibePackage(BaseModel):
    """
    The complete output of the Vibe Architect.
    All four creative domains + the emotional anchor that unifies them.
    """
    vibe_input: str                          # original description
    emotional_anchor: EmotionalAnchor
    music: list[Track]                       # 5 tracks
    colors: list[ColorSwatch]               # 4-6 colors
    films: list[Film]                        # 3 films
    poem: str                               # original verse
    coherence: Optional[CoherenceScore] = None  # filled in Stage 4