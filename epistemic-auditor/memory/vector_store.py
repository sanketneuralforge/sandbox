# memory/vector_store.py

import json
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
from models import AuditResult
from config import CHROMA_PERSIST_PATH, CHROMA_COLLECTION, RAG_TOP_K, RAG_MIN_SIMILARITY
from logger import get_logger

log = get_logger("vector_store")

class AuditVectorStore:
    """
    ChromaDB-backed vector store for audit results.
    
    Two operations:
    1. store(result)   — embed and persist an audit result
    2. retrieve(claim) — find the most relevant past audits
    
    The retrieved audits become RAG context for the agents.
    """

    def __init__(self):
        # Persistent client — survives restarts
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)

        # Use sentence-transformers for embeddings
        # Same model as our semantic cache for consistency
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )

        log.info(f"Vector store initialized. "
                 f"Collection '{CHROMA_COLLECTION}' has "
                 f"{self.collection.count()} documents.")

    def store(self, result: AuditResult):
        """
        Stores an audit result in ChromaDB.
        
        The document is a rich text representation of the audit —
        not just the claim, but the evidence, verdict, and psychology.
        This makes retrieval richer than just claim-to-claim matching.
        """
        verdict = result.verdict.value if hasattr(result.verdict, 'value') \
                  else result.verdict

        # Build a rich document for embedding
        # More context = better retrieval quality
        document = f"""
Claim: {result.claim_as_stated}
Verdict: {verdict}
Confidence: {result.confidence}
Atomic claims: {' | '.join(result.atomic_claims)}
Evidence: {result.evidence_summary}
Origin: {result.origin_hypothesis}
Why believed: {result.why_people_believe_it}
Counter-narrative: {result.counter_narrative}
""".strip()

        # Metadata stored alongside — used for filtering
        metadata = {
            "claim": result.claim_as_stated[:500],
            "verdict": verdict,
            "confidence": str(result.confidence),
            "audited_at": datetime.now().isoformat(),
            "has_sources": str(len(result.sources) > 0),
        }

        # Use a hash of the claim as the document ID
        import hashlib
        doc_id = hashlib.md5(
            result.claim_as_stated.lower().strip().encode()
        ).hexdigest()

        try:
            # Upsert — update if exists, insert if not
            self.collection.upsert(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata],
            )
            log.info(f"Stored audit in vector store: '{result.claim_as_stated[:60]}'")
        except Exception as e:
            log.error(f"Failed to store in vector store: {e}")

    def retrieve(self, claim: str, top_k: int = None) -> list[dict]:
        """
        Retrieves the most relevant past audits for a given claim.
        
        Returns a list of dicts with:
        - claim: the original claim
        - verdict: what we found
        - evidence: what evidence was gathered
        - psychology: why people believed it
        - similarity: how similar to current claim (0-1)
        
        These become the RAG context injected into agent prompts.
        """
        top_k = top_k or RAG_TOP_K
        min_similarity = RAG_MIN_SIMILARITY

        if self.collection.count() == 0:
            log.info("Vector store empty — no context to retrieve")
            return []

        try:
            results = self.collection.query(
                query_texts=[claim],
                n_results=min(top_k, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            retrieved = []
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )):
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity: 1 - (distance/2)
                similarity = 1 - (distance / 2)

                if similarity < min_similarity:
                    log.info(f"Skipping result {i} — similarity {similarity:.3f} "
                             f"below threshold {min_similarity}")
                    continue

                retrieved.append({
                    "claim": meta.get("claim", ""),
                    "verdict": meta.get("verdict", ""),
                    "confidence": float(meta.get("confidence", 0)),
                    "document": doc,
                    "similarity": similarity,
                })
                log.info(f"Retrieved relevant audit: '{meta.get('claim', '')[:50]}' "
                         f"(similarity: {similarity:.3f})")

            return retrieved

        except Exception as e:
            log.error(f"Vector store retrieval failed: {e}")
            return []

    def format_as_context(self, retrieved: list[dict]) -> str:
        """
        Formats retrieved audits into a context block
        the LLM can read and reason from.
        
        This is the RAG prompt — how you format retrieved
        context is as important as what you retrieve.
        """
        if not retrieved:
            return ""

        lines = ["RELEVANT PAST AUDITS (use as background context):"]
        lines.append("=" * 50)

        for i, item in enumerate(retrieved, 1):
            lines.append(
                f"\n[Past Audit {i}] Similarity: {item['similarity']:.2f}\n"
                f"{item['document']}"
            )
            lines.append("-" * 30)

        lines.append(
            "\nUse these past audits to inform your analysis. "
            "Do not simply copy their conclusions — use them as "
            "background knowledge to produce a richer, more accurate audit."
        )

        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "total_audits": self.collection.count(),
            "storage_path": CHROMA_PERSIST_PATH,
            "collection": CHROMA_COLLECTION,
        }