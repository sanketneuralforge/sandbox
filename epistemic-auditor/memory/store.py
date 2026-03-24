# memory/store.py

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path

class ClaimMemory:
    """
    Persists audit results to disk.
    
    Key insight: we hash the claim text as the key.
    "5G causes covid" and "5G CAUSES COVID" map to different hashes,
    so in Stage 3 we normalize before hashing.
    
    Production gotcha: for production, replace this with Redis or 
    a proper database. JSON files don't scale and have race conditions
    under concurrent requests.
    """

    def __init__(self, storage_path: str = "memory/claim_store.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._store = self._load()

    def _load(self) -> dict:
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self._store, f, indent=2)

    def _key(self, claim: str) -> str:
        # Normalize: lowercase, strip whitespace, then hash
        normalized = claim.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, claim: str) -> dict | None:
        """
        Returns a cached audit result, or None if not seen before.
        """
        key = self._key(claim)
        entry = self._store.get(key)
        if entry:
            print(f"[Memory] Cache hit for claim (audited {entry['audited_at']})")
        return entry.get("result") if entry else None

    def store(self, claim: str, result: dict):
        """
        Saves an audit result. Call this after every successful audit.
        """
        key = self._key(claim)
        self._store[key] = {
            "claim": claim,
            "result": result,
            "audited_at": datetime.now().isoformat(),
        }
        self._save()
        print(f"[Memory] Stored audit for: '{claim[:50]}...'")

    def stats(self) -> dict:
        return {
            "total_claims_audited": len(self._store),
            "storage_path": str(self.storage_path),
        }