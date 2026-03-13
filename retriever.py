"""
Retrieval Pipeline
- Similarity search with scores
- Source provenance tracking
- Filtered retrieval with metadata
"""
from langchain_community.vectorstores import Chroma
from config import TOP_K, RELEVANCE_THRESHOLD


def retrieve_with_scores(
    vector_store: Chroma,
    query: str,
    top_k: int = TOP_K,
    min_score: float = RELEVANCE_THRESHOLD,
) -> list[dict]:
    """
    Retrieve documents with relevance scores and full provenance.

    Returns:
        List of dicts with keys: content, source, doc_id, page, chunk_id,
        department, quarter, doc_type, similarity_score
    """
    results = vector_store.similarity_search_with_relevance_scores(query, k=top_k)

    retrieved = []
    for doc, score in results:
        if score < min_score:
            continue
        retrieved.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "doc_id": doc.metadata.get("doc_id", "Unknown"),
            "page": doc.metadata.get("page", "?"),
            "chunk_id": doc.metadata.get("chunk_id", 0),
            "department": doc.metadata.get("department", "Unknown"),
            "quarter": doc.metadata.get("quarter", "Unknown"),
            "doc_type": doc.metadata.get("doc_type", "Unknown"),
            "similarity_score": round(score, 4),
        })

    return retrieved


def format_retrieved_context(results: list[dict]) -> str:
    """
    Format retrieved results into a context string for the LLM prompt.
    """
    if not results:
        return "No relevant documents found."

    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"[Source #{i}: {r['source']} | Dept: {r['department']} | "
            f"Score: {r['similarity_score']:.2f}]\n{r['content']}"
        )

    return "\n\n---\n\n".join(context_parts)


def get_unique_sources(results: list[dict]) -> list[dict]:
    """
    Extract unique source documents from results with aggregated info.
    """
    sources = {}
    for r in results:
        src = r["source"]
        if src not in sources:
            sources[src] = {
                "source": src,
                "doc_id": r["doc_id"],
                "department": r["department"],
                "doc_type": r["doc_type"],
                "chunks_retrieved": 0,
                "max_similarity": 0.0,
                "snippets": [],
            }
        sources[src]["chunks_retrieved"] += 1
        sources[src]["max_similarity"] = max(
            sources[src]["max_similarity"], r["similarity_score"]
        )
        # Keep first 200 chars of each chunk as snippet
        snippet = r["content"][:200]
        if len(r["content"]) > 200:
            snippet += "..."
        sources[src]["snippets"].append(snippet)

    return list(sources.values())
