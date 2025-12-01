# TASK_11: Result Fusion Integration

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_11 |
| **Day** | 9 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_10 (Cross-Encoder) |
| **Blocks** | TASK_15 |
| **Priority** | High |

## Objective

Integrate the Cross-Encoder reranker into the DataIntelligenceService to provide:
1. Multi-source result fusion (graph + vector + keyword)
2. Neural reranking of combined results
3. Configurable reranking thresholds

## Context

After TASK_10, we have a Cross-Encoder that can score relevance. This task integrates it into the search pipeline so that results from all sources are combined and reranked for optimal ordering.

## Files to Modify

| Action | File Path |
|--------|-----------|
| MODIFY | `app/services/data_intelligence_service.py` |
| MODIFY | `app/services/data_intelligence/__init__.py` |

## Implementation

### Step 1: Update DataIntelligenceService

Add reranking capability to the search method:

```python
# Add import at top
from .data_intelligence.cross_encoder_reranker import CrossEncoderReranker, RankedDocument

class DataIntelligenceService:
    def __init__(self):
        # ... existing initialization ...
        
        # Initialize reranker
        try:
            self.reranker = CrossEncoderReranker(model_type="fast")
            self._reranker_available = self.reranker._model_loaded
        except Exception as e:
            logger.warning(f"Reranker unavailable: {e}")
            self.reranker = None
            self._reranker_available = False
    
    async def search(
        self,
        query: str,
        context: str = "",
        max_results: int = 10,
        rerank: bool = True,  # New parameter
        rerank_threshold: float = 0.0  # New parameter
    ) -> IntelligentSearchResult:
        """
        Execute intelligent search with optional reranking.
        
        Args:
            query: User's question
            context: Optional conversation context
            max_results: Maximum results per source
            rerank: Whether to apply neural reranking
            rerank_threshold: Minimum rerank score to include
        """
        # ... existing search logic ...
        
        # After collecting results, add reranking step:
        if rerank and self._reranker_available:
            combined = self._fuse_and_rerank(
                query=query,
                graph_results=graph_results,
                vector_results=vector_results,
                keyword_results=keyword_results,
                top_k=max_results,
                threshold=rerank_threshold
            )
            
            # Replace vector_results with reranked combined results
            vector_results = [r.to_dict() for r in combined]
            graph_results = []  # Already included in reranked results
            keyword_results = []
    
    def _fuse_and_rerank(
        self,
        query: str,
        graph_results: List[Dict],
        vector_results: List[Dict],
        keyword_results: List[Dict],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[RankedDocument]:
        """Fuse results from multiple sources and rerank."""
        
        # Tag results with source
        all_results = []
        for r in graph_results:
            r["_source"] = "graph"
            all_results.append(r)
        for r in vector_results:
            r["_source"] = "vector"
            all_results.append(r)
        for r in keyword_results:
            r["_source"] = "keyword"
            all_results.append(r)
        
        if not all_results:
            return []
        
        # Rerank
        reranked = self.reranker.rerank(
            query=query,
            documents=all_results,
            content_key="content",
            top_k=top_k,
            score_threshold=threshold
        )
        
        return reranked
```

## Acceptance Criteria

- [ ] Reranker integrated into search pipeline
- [ ] Combined results properly ordered by relevance
- [ ] Sources preserved in reranked results
- [ ] Threshold filtering works
- [ ] Graceful degradation without reranker

## Verification

```bash
python -c "
import asyncio
from app.services.data_intelligence_service import DataIntelligenceService

async def test():
    service = DataIntelligenceService()
    result = await service.search('What is the budget for climate research?', rerank=True)
    print(f'Reranking enabled: {service._reranker_available}')
    print(f'Results: {len(result.vector_results)}')

asyncio.run(test())
"
```

