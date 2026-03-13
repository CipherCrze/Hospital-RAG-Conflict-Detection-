"""
RAG Pipeline Orchestrator
- Combines retrieval, conflict detection, and LLM reasoning
- Provides structured responses with confidence calibration
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    RAG_CONFLICT_PROMPT,
)
from retriever import retrieve_with_scores, format_retrieved_context, get_unique_sources
from conflict_detector import detect_conflicts, format_conflicts_for_prompt


def build_chain(api_key: str):
    """Build the RAG LLM chain."""
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=api_key,
        temperature=LLM_TEMPERATURE,
        convert_system_message_to_human=True,
    )

    prompt = PromptTemplate(
        template=RAG_CONFLICT_PROMPT,
        input_variables=["context", "conflicts", "question"],
    )

    chain = prompt | llm | StrOutputParser()
    return chain


def calibrate_confidence(
    retrieved_chunks: list[dict],
    conflict_result: dict,
) -> dict:
    """
    Calibrate confidence based on retrieval scores and conflicts.

    Returns:
        Dict with 'score' (0-100), 'level' (High/Medium/Low), 'factors' list
    """
    if not retrieved_chunks:
        return {"score": 0, "level": "Low", "factors": ["No relevant documents found"]}

    # Base confidence from retrieval scores
    avg_similarity = sum(r["similarity_score"] for r in retrieved_chunks) / len(retrieved_chunks)
    max_similarity = max(r["similarity_score"] for r in retrieved_chunks)

    base_score = (avg_similarity * 0.6 + max_similarity * 0.4) * 100

    factors = []

    # Penalty for conflicts
    conflict_penalty = 0
    if conflict_result["has_conflicts"]:
        n_conflicts = conflict_result["conflict_count"]
        avg_contradiction = sum(
            c["contradiction_score"] for c in conflict_result["conflicts"]
        ) / n_conflicts

        conflict_penalty = min(30, n_conflicts * 8 * avg_contradiction)
        factors.append(
            f"{n_conflicts} conflict(s) detected (avg contradiction: {avg_contradiction:.2f})"
        )

    # Bonus for multiple agreeing sources
    unique_sources = set(r["source"] for r in retrieved_chunks)
    if len(unique_sources) >= 3:
        source_bonus = 5
        factors.append(f"Evidence from {len(unique_sources)} different sources")
    else:
        source_bonus = 0

    # Penalty for low retrieval scores
    if avg_similarity < 0.4:
        factors.append(f"Low average relevance score ({avg_similarity:.2f})")

    final_score = max(0, min(100, base_score - conflict_penalty + source_bonus))

    if final_score >= 70 and not conflict_result["has_conflicts"]:
        level = "High"
    elif final_score >= 40 or conflict_result["has_conflicts"]:
        level = "Medium"
    else:
        level = "Low"

    # If conflicts exist, cap at Medium
    if conflict_result["has_conflicts"]:
        level = "Medium" if level == "High" else level

    factors.insert(0, f"Avg retrieval similarity: {avg_similarity:.2f}")

    return {
        "score": round(final_score, 1),
        "level": level,
        "factors": factors,
    }


def query_with_conflict_detection(
    chain,
    vector_store,
    question: str,
) -> dict:
    """
    Full RAG pipeline with conflict detection.

    Returns:
        Dict with answer, conflicts, sources, confidence, and reasoning.
    """
    # Step 1: Retrieve relevant chunks with scores
    retrieved = retrieve_with_scores(vector_store, question)

    if not retrieved:
        return {
            "answer": "I couldn't find any relevant information in the hospital documents to answer this question.",
            "conflicts": {"conflicts": [], "has_conflicts": False, "conflict_count": 0},
            "sources": [],
            "confidence": {"score": 0, "level": "Low", "factors": ["No relevant documents found"]},
            "retrieved_chunks": [],
        }

    # Step 2: Detect conflicts among retrieved chunks
    conflict_result = detect_conflicts(retrieved)

    # Step 3: Format context and conflicts for LLM
    context_str = format_retrieved_context(retrieved)
    conflicts_str = format_conflicts_for_prompt(conflict_result)

    # Step 4: Invoke LLM
    answer = chain.invoke({
        "context": context_str,
        "conflicts": conflicts_str,
        "question": question,
    })

    # Step 5: Calibrate confidence
    confidence = calibrate_confidence(retrieved, conflict_result)

    # Step 6: Extract unique sources
    sources = get_unique_sources(retrieved)

    return {
        "answer": answer,
        "conflicts": conflict_result,
        "sources": sources,
        "confidence": confidence,
        "retrieved_chunks": retrieved,
    }
