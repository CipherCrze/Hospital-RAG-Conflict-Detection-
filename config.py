"""
Configuration constants for the Hospital RAG Conflict Detection System.
"""
import os

# --- Project Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DOCS_DIR = os.path.join(BASE_DIR, "sample_documents")
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "data", "chroma_db")

# --- Text Chunking ---
CHUNK_SIZE = 800            # Characters per chunk
CHUNK_OVERLAP = 200         # Overlap between consecutive chunks

# --- Embedding Model ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Vector Store ---
COLLECTION_NAME = "hospital_docs"

# --- Retrieval ---
TOP_K = 8                   # Number of chunks to retrieve per query
RELEVANCE_THRESHOLD = 0.25  # Minimum similarity score to keep a chunk

# --- LLM ---
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0.2      # Low temperature for factual, grounded answers

# --- Conflict Detection ---
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
CONTRADICTION_THRESHOLD = 0.6   # NLI contradiction probability threshold
MAX_PAIRWISE_COMPARISONS = 28   # C(8,2) = 28 for top-8 chunks

# --- Supported File Types ---
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt"]

# --- Prompt Templates ---
RAG_CONFLICT_PROMPT = """You are an expert hospital performance analyst. Answer the user's question based ONLY on the provided document context.

## Critical Instructions
1. Base your answer ONLY on the provided context. Do NOT use external knowledge.
2. If documents contain CONFLICTING information, you MUST explicitly identify and explain the conflicts.
3. Always cite sources using the format [Document Name].
4. Provide a confidence level: High, Medium, or Low.
5. If conflicts exist, explain possible reasons for the discrepancy (different departments, different metrics, different time periods, etc.).
6. Structure your response clearly.

## Document Context
{context}

## Detected Conflicts (from automated analysis)
{conflicts}

## User Question
{question}

## Your Response
Provide:
1. **Answer**: A comprehensive answer acknowledging any conflicting evidence
2. **Conflicting Evidence**: List specific contradictions found (if any)
3. **Confidence Level**: High / Medium / Low
4. **Reasoning**: Why you assigned this confidence level, considering any conflicts
"""

CONFLICT_EXPLANATION_PROMPT = """You are analyzing two document excerpts from a hospital's records that appear to contain CONFLICTING information.

Document A ({source_a}):
"{text_a}"

Document B ({source_b}):
"{text_b}"

Briefly explain:
1. What specific claims conflict between these two documents?
2. What might explain this discrepancy (different departments, metrics, perspectives)?
Keep your explanation to 2-3 sentences.
"""
