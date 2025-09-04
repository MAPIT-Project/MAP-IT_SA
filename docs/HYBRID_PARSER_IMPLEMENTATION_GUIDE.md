# Hybrid Query Parser Implementation Guide

## Overview

The Hybrid Query Parser combines the speed of rule-based parsing with the intelligence of AI-powered parsing to provide optimal query understanding for Horizon Europe call discovery.

## Architecture

### Components

1. **Intelligent Query Parser** (`intelligent_query_parser.py`)
   - Rule-based pattern matching
   - Extremely fast (sub-millisecond response)
   - Handles common Horizon Europe query patterns

2. **AI Query Parser** (`ai_query_parser.py`)  
   - Uses Gemini 2.5 Flash for natural language understanding
   - Better at complex, nuanced queries
   - Provides confidence scoring
   - Slower (~1 second per query)

3. **Hybrid Query Parser** (`hybrid_query_parser.py`)
   - Intelligent routing between the two parsers
   - Provides metadata about which parser was used
   - Maintains quality while optimizing performance

## Query Classification Logic

### Simple Queries (Use Intelligent Parser)
- Short queries (≤3 words)
- Basic status queries ("open calls", "recent calls")
- Single technology queries ("cybersecurity calls")
- Simple patterns matching `r'^\s*[a-z]+\s+[a-z]+\s*$'`

### Complex Queries (Use AI Parser)
- Multiple conjunctions ("and", "or", "with")
- Work programme references ("latest work programme")
- Explanatory queries ("how to", "what is", "explain")
- Multiple TRL levels ("TRL 5-7")
- Comma-separated technology lists
- Very long queries (>10 words)
- Multiple domain terms (≥3 different domains)

### Default Behavior (Try Intelligent First)
- Most Horizon Europe queries fall here
- Uses intelligent parser first
- Falls back to AI if:
  - No intents detected
  - Only "no_filters" intent
  - Procedural queries detected

## Performance Characteristics

### Speed Comparison
| Parser Type | Avg Time | Use Case |
|-------------|----------|----------|
| Intelligent | 0.000s | Simple, common queries |
| AI | 0.774s | Complex, nuanced queries |
| Hybrid | 0.2-0.9s | Adaptive based on complexity |

### Quality Comparison
| Metric | Intelligent | AI | Hybrid |
|--------|-------------|----|--------|
| Intent Detection | Good | Excellent | Excellent |
| Query Cleaning | Basic | Advanced | Context-aware |
| Confidence | Fixed (0.8) | Dynamic (0.0-1.0) | Dynamic |
| Specific Filters | Good | Excellent | Excellent |

## Integration with RAG System

### Enhanced Call Search
The hybrid parser integrates with the enhanced call search system to provide:

1. **Better Query Understanding**: More accurate intent detection
2. **Optimized Performance**: Fast responses for common queries
3. **Confidence Metrics**: Visibility into parsing reliability
4. **Parser Metadata**: Debugging and optimization insights

### Usage in RAG Service
```python
from app.services.hybrid_query_parser import HybridQueryParser

class CordisRAG:
    def __init__(self):
        self.hybrid_parser = HybridQueryParser()
    
    def search_for_calls(self, question: str):
        # Parse query with hybrid approach
        filters = self.hybrid_parser.parse_query(question)
        
        # Use filters for search optimization
        if filters.filter_intention == "open_only":
            # Apply open calls filter
            pass
        elif "technology:ai" in filters.user_intent_detected:
            # Focus on AI-related calls
            pass
        
        # Generate explanation with parser info
        explanation = self.hybrid_parser.get_filter_explanation(
            filters, results_count
        )
```

## Configuration

### Environment Variables
```bash
# Required for AI parser
GEMINI_API_KEY=your_gemini_api_key
# or
GOOGLE_API_KEY=your_google_api_key

# Optional performance tuning
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=50
```

### Tuning Parameters
The hybrid parser can be tuned by adjusting:

1. **Complexity Thresholds**: Modify `_is_complex_query()` method
2. **Pattern Matching**: Update `complex_patterns` and `simple_patterns`
3. **Fallback Logic**: Adjust conditions in default behavior
4. **Confidence Thresholds**: Change when to fallback from intelligent to AI

## Best Practices

### For Development
1. **Test Both Parsers**: Always compare intelligent vs AI results
2. **Monitor Performance**: Track parser choice statistics
3. **Update Patterns**: Regularly add new Horizon Europe terminology
4. **Cache Results**: Consider caching for repeated queries

### For Production
1. **Use Hybrid Default**: Default to hybrid parser for all queries
2. **Monitor API Costs**: Track Gemini API usage
3. **Set Timeouts**: Implement timeout protection for AI queries
4. **Log Parser Choices**: Monitor which parser is being used when

## Example Usage

```python
from app.services.hybrid_query_parser import HybridQueryParser

# Initialize parser
parser = HybridQueryParser()

# Parse queries
queries = [
    "open AI calls in Cluster 4",
    "How to find calls with lump-sum funding?",
    "cybersecurity and edge computing calls"
]

for query in queries:
    filters = parser.parse_query(query)
    print(f"Query: {query}")
    print(f"Parser: {filters.parser_used}")
    print(f"Intents: {filters.user_intent_detected}")
    print(f"Time: {filters.processing_time:.3f}s")
    print()
```

## Troubleshooting

### Common Issues

1. **AI Parser Timeouts**: Increase timeout or implement retry logic
2. **Poor Intent Detection**: Update pattern matching rules
3. **API Key Issues**: Verify Gemini/Google API key configuration
4. **Performance Regression**: Monitor parser choice statistics

### Debugging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test individual parsers
from app.services.intelligent_query_parser import IntelligentQueryParser
from app.services.ai_query_parser import AIQueryParser

intel = IntelligentQueryParser()
ai = AIQueryParser()

# Compare results
intel_result = intel.parse_query("your query")
ai_result = ai.parse_query("your query")
```

## Future Enhancements

1. **Learning Mode**: Automatically improve pattern matching from AI results
2. **Query Caching**: Cache AI parser results for common queries
3. **Confidence-Based Routing**: Use AI confidence scores for better routing
4. **Multi-Lingual Support**: Extend to other EU languages
5. **Real-time Adaptation**: Adjust thresholds based on query volume and patterns

## Conclusion

The Hybrid Query Parser provides the best of both worlds:
- **Speed** of rule-based parsing for common queries
- **Intelligence** of AI parsing for complex queries
- **Adaptability** to different query types and complexities
- **Visibility** into parsing decisions and confidence

This approach ensures that the Horizon Europe call discovery system remains both responsive and intelligent, capable of handling the wide variety of user queries while maintaining excellent performance.