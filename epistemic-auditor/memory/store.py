# memory/store.py

import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer

class ClaimMemory:
    """
    Two-layer memory:
    
    Layer 1 — Exact match (MD5 hash). Free, instant.
    Layer 2 — Semantic match (embeddings). Catches paraphrases.
    
    Lookup order: exact → semantic → miss (run the agent)
    """

    # How similar two claims must be to count as the same.
    # 0.92 is tight enough to avoid false positives but catches
    # clear paraphrases. Tune this if you get false hits.
    SIMILARITY_THRESHOLD = 0.92

    def __init__(self, storage_path: str = "memory/claim_store.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._store = self._load()

        # Load embedding model once — reused for every lookup and store
        # all-MiniLM-L6-v2 is small (80MB), fast, and good enough for
        # semantic similarity on short claims
        print("[Memory] Loading embedding model...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Memory] Ready.")

    def _load(self) -> dict:
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self._store, f, indent=2)

    def _exact_key(self, claim: str) -> str:
        return hashlib.md5(claim.lower().strip().encode()).hexdigest()

    def _embed(self, text: str) -> list[float]:
        vec = self.embedder.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        # Both vectors are already L2-normalized by normalize_embeddings=True
        # so cosine similarity is just the dot product
        return float(np.dot(a, b))

    def get(self, claim: str) -> dict | None:
        """
        Two-stage lookup:
        1. Try exact match first (fast)
        2. Try semantic match (slower but catches paraphrases)
        """
        # ── Layer 1: exact match ───────────────────────────────────
        exact_key = self._exact_key(claim)
        if exact_key in self._store:
            entry = self._store[exact_key]
            print(f"[Memory] Exact cache hit (audited {entry['audited_at']})")
            return entry["result"]

        # ── Layer 2: semantic match ────────────────────────────────
        query_vec = self._embed(claim)

        best_score = 0.0
        best_entry = None

        for key, entry in self._store.items():
            stored_vec = entry.get("embedding")
            if not stored_vec:
                continue   # old entries without embeddings — skip

            score = self._cosine_similarity(query_vec, stored_vec)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= self.SIMILARITY_THRESHOLD:
            print(
                f"[Memory] Semantic cache hit "
                f"(similarity: {best_score:.3f}, "
                f"matched: '{best_entry['claim'][:60]}...')"
            )
            return best_entry["result"]

        print(f"[Memory] Cache miss (best similarity: {best_score:.3f})")
        return None

    def store(self, claim: str, result: dict):
        """
        Stores result with both exact key and embedding vector.
        """
        key = self._exact_key(claim)
        embedding = self._embed(claim)

        self._store[key] = {
            "claim": claim,
            "result": result,
            "embedding": embedding,
            "audited_at": datetime.now().isoformat(),
        }
        self._save()
        print(f"[Memory] Stored audit for: '{claim[:60]}...'")

    def stats(self) -> dict:
        return {
            "total_claims_audited": len(self._store),
            "storage_path": str(self.storage_path),
        }