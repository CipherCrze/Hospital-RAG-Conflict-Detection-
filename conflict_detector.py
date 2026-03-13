"""
Conflict Detection Engine
- Stage 1: NLI-based pairwise contradiction classification
- Stage 2: LLM reasoning for flagged contradictions
"""
import sys
import io
import os

# Fix Windows console encoding for tqdm/transformers Unicode output
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import itertools
from sentence_transformers import CrossEncoder
from config import NLI_MODEL, CONTRADICTION_THRESHOLD

# Global model cache
_nli_model = None


def get_nli_model():
    """Load and cache the NLI cross-encoder model."""
    global _nli_model
    if _nli_model is None:
        print("[NLI] Loading NLI model for conflict detection...")
        _nli_model = CrossEncoder(NLI_MODEL)
        print("  [OK] NLI model loaded")
    return _nli_model


def detect_conflicts(retrieved_chunks: list[dict]) -> dict:
    """
    Detect contradictions among retrieved document chunks using NLI.

    Uses a cross-encoder NLI model to classify pairs of chunks as:
    - entailment (0)
    - neutral (1)
    - contradiction (2)

    Args:
        retrieved_chunks: List of dicts from retriever with 'content' and 'source'

    Returns:
        Dict with 'conflicts' list, 'has_conflicts' bool, 'conflict_count' int
    """
    if len(retrieved_chunks) < 2:
        return {"conflicts": [], "has_conflicts": False, "conflict_count": 0}

    model = get_nli_model()

    # Generate all unique pairs of chunks from DIFFERENT sources
    pairs = []
    pair_indices = []
    for i, j in itertools.combinations(range(len(retrieved_chunks)), 2):
        chunk_a = retrieved_chunks[i]
        chunk_b = retrieved_chunks[j]
        # Only compare chunks from different source documents
        if chunk_a["source"] != chunk_b["source"]:
            pairs.append((chunk_a["content"], chunk_b["content"]))
            pair_indices.append((i, j))

    if not pairs:
        return {"conflicts": [], "has_conflicts": False, "conflict_count": 0}

    # Batch predict NLI scores
    # Output: [entailment, neutral, contradiction] probabilities
    texts = [(a, b) for a, b in pairs]
    scores = model.predict(texts)

    # Extract contradictions above threshold
    conflicts = []
    for idx, (score_triple, (i, j)) in enumerate(zip(scores, pair_indices)):
        # score_triple: [entailment, neutral, contradiction]
        contradiction_score = float(score_triple[2]) if len(score_triple) > 2 else 0.0

        if contradiction_score >= CONTRADICTION_THRESHOLD:
            chunk_a = retrieved_chunks[i]
            chunk_b = retrieved_chunks[j]
            conflicts.append({
                "doc_a": {
                    "source": chunk_a["source"],
                    "department": chunk_a["department"],
                    "snippet": chunk_a["content"][:300],
                    "similarity_score": chunk_a["similarity_score"],
                },
                "doc_b": {
                    "source": chunk_b["source"],
                    "department": chunk_b["department"],
                    "snippet": chunk_b["content"][:300],
                    "similarity_score": chunk_b["similarity_score"],
                },
                "contradiction_score": round(contradiction_score, 4),
                "entailment_score": round(float(score_triple[0]), 4),
                "neutral_score": round(float(score_triple[1]), 4),
            })

    # Sort by contradiction score descending
    conflicts.sort(key=lambda x: x["contradiction_score"], reverse=True)

    return {
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
    }


def format_conflicts_for_prompt(conflict_result: dict) -> str:
    """
    Format detected conflicts into a string for the LLM prompt.
    """
    if not conflict_result["has_conflicts"]:
        return "No conflicting evidence detected among retrieved documents."

    lines = [f"⚠️ {conflict_result['conflict_count']} potential conflict(s) detected:\n"]

    for i, conflict in enumerate(conflict_result["conflicts"], 1):
        lines.append(f"Conflict #{i} (Contradiction Score: {conflict['contradiction_score']:.2f}):")
        lines.append(f"  • {conflict['doc_a']['source']} ({conflict['doc_a']['department']}):")
        lines.append(f"    \"{conflict['doc_a']['snippet'][:150]}...\"")
        lines.append(f"  • {conflict['doc_b']['source']} ({conflict['doc_b']['department']}):")
        lines.append(f"    \"{conflict['doc_b']['snippet'][:150]}...\"")
        lines.append("")

    return "\n".join(lines)
