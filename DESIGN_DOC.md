# Design Document — Hospital RAG Conflict Detection System

## 1. System Overview

A retrieval-augmented generation (RAG) pipeline that answers free-text queries about hospital performance documents, automatically detects conflicting claims between sources, and provides confidence-calibrated responses with full source provenance.

## 2. Scalability Plan

### Current Scale
- **Documents**: 12 files → ~150 chunks
- **Vector DB**: ChromaDB (local, single-node)
- **NLI Model**: CPU inference, pairwise O(C(k,2)) comparisons
- **LLM**: Single API call per query

### Scaling to 1,000+ Documents (~10K chunks)

| Component | Current | Scaled Approach |
|-----------|---------|----------------|
| Vector DB | ChromaDB local | ChromaDB in Docker or Weaviate Cloud |
| Embeddings | CPU, on-the-fly | GPU batch embedding, pre-computed |
| NLI Pairs | All pairs from top-8 | Pre-filter by topic/department, reduce k |
| LLM | Single call | Batch API with retry logic |

### Scaling to 100K+ Documents
- **Vector DB**: Migrate to Pinecone (managed) or Weaviate (self-hosted with HNSW)  
- **Embedding**: GPU cluster with batch processing, ONNX-optimized model
- **Conflict Detection**: Replace pairwise NLI with claim extraction + clustering approach:
  1. Extract factual claims from each chunk using LLM
  2. Cluster claims by topic using embeddings
  3. Run NLI only within same-topic clusters
  4. Reduces complexity from O(n²) to O(n·k) where k = cluster size

## 3. Performance Bottlenecks

### Identified Bottlenecks

| Bottleneck | Impact | Mitigation |
|-----------|--------|-----------|
| **NLI Pairwise Computation** | O(C(k,2)) = 28 comparisons for k=8. Grows quadratically. | Reduce k, pre-filter by topic, use faster ONNX model |
| **Cold Start (Model Loading)** | NLI model load: ~5s first query | Pre-load in Streamlit session state |
| **Embedding Computation** | Re-embeds all docs on each restart | Persistent ChromaDB storage, batch ingestion |
| **LLM Latency** | 2-4s per Gemini API call | Use streaming responses, caching for repeated queries |

### Latency Budget (Target per Query)

| Step | Target | Current |
|------|--------|---------|
| Embedding query | <100ms | ~80ms |
| Vector search | <200ms | ~150ms |
| NLI conflict detection | <500ms | ~400ms |
| LLM response | <3s | 2-4s |
| **Total** | **<4s** | **~3-5s** |

## 4. Monitoring Strategy

### Key Metrics to Track

| Metric | How to Measure | Alert Threshold |
|--------|---------------|-----------------|
| Retrieval relevance | Avg similarity score per query | <0.3 avg → low quality |
| Conflict detection precision | Manual review of flagged conflicts | <70% precision → tune threshold |
| Response latency (P95) | End-to-end timing | >8s → investigate |
| LLM error rate | API error count / total queries | >5% → check API quota |
| User satisfaction | Thumbs up/down feedback | <60% positive → review prompts |

### Monitoring Implementation
- **Logging**: Structured JSON logs for each query (retrieval scores, conflicts, confidence, latency)
- **Dashboards**: Streamlit admin page with query analytics
- **Alerting**: Slack/email notifications on threshold breaches
- **A/B Testing**: Compare conflict detection thresholds, prompt variants

## 5. Cost Trade-offs

### Current Cost Structure (Development)

| Resource | Cost | Notes |
|----------|------|-------|
| Gemini 2.0 Flash | Free tier (60 RPM) | Sufficient for demo/dev |
| ChromaDB | $0 | Local storage |
| NLI Model | $0 | Local CPU inference |
| Embedding Model | $0 | Local CPU inference |
| **Total per query** | **~$0** | |

### Production Cost Estimates (1,000 queries/day)

| Resource | Option A (Budget) | Option B (Performance) |
|----------|-------------------|----------------------|
| LLM | Gemini Flash: ~$0.15/1K queries | GPT-4o: ~$3/1K queries |
| Vector DB | ChromaDB self-hosted: $50/mo (VM) | Pinecone: $70/mo (Starter) |
| Embedding | Local CPU: included in VM | OpenAI ada-002: ~$0.10/1K queries |
| NLI Model | Local CPU: included in VM | GPU instance: $200/mo |
| **Monthly Total** | **~$55/mo** | **~$370/mo** |

### Cost Optimization Strategies
1. **Caching**: Cache LLM responses for repeated/similar queries (30-50% cost reduction)
2. **Tiered conflict detection**: Simple heuristic check first, NLI only for borderline cases
3. **Embedding reuse**: Never re-embed unchanged documents
4. **Batch processing**: Combine multiple queries for LLM API efficiency

## 6. Assumptions

1. Documents are in English
2. Hospital documents follow semi-structured reporting formats
3. Conflicts are cross-document (same-document inconsistencies are not flagged)
4. The NLI model's notion of "contradiction" aligns with factual disagreement
5. Users have a basic understanding of hospital metrics to interpret nuanced answers
6. Gemini API quotas are sufficient for query volume (free tier: 60 RPM)
