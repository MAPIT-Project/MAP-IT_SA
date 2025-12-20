# MAPIT AI - System Architecture

**Version:** 2.0
**Last Updated:** December 2024
**Authors:** MAPIT Development Team

## 1. Executive Summary

MAPIT AI is an intelligent research funding assistant that leverages RAG (Retrieval-Augmented Generation) technology to help researchers navigate EU funding opportunities. The system combines a graph database backend with large language models to provide contextual, accurate responses about EU research funding programs.

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   Web Browser   │  │    API Client   │  │   CLI Interface     │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘ │
└───────────┴──────────────────┬─┴─────────────────────┬──────────────┘
                               │                        │
┌──────────────────────────────┴────────────────────────┴──────────────┐
│                      APPLICATION LAYER                                │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      Flask Web Server                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │  │
│  │  │    Routes    │  │  Templates   │  │   Static Assets      │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
┌──────────────────────────────────┴───────────────────────────────────┐
│                      SERVICE LAYER                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    RAG Engine (CORDISRetriever)                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │  │
│  │  │ Embedding  │  │  Context   │  │   Prompt   │  │   LLM    │ │  │
│  │  │  Service   │  │ Retrieval  │  │  Builder   │  │ Service  │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      ETL Pipeline                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐   │  │
│  │  │   Extract  │  │ Transform  │  │         Load           │   │  │
│  │  │   (CSV)    │  │  (Parse)   │  │       (Dgraph)         │   │  │
│  │  └────────────┘  └────────────┘  └────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
┌──────────────────────────────────┴───────────────────────────────────┐
│                       DATA LAYER                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Dgraph (Graph)  │  │   PDF Documents  │  │  CORDIS CSV Data   │  │
│  │                  │  │   (Embeddings)   │  │                    │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┴───────────────────────────────────┐
│                    EXTERNAL SERVICES                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │    Mistral AI    │  │   CORDIS API     │  │  Sentence          │  │
│  │   (LLM Service)  │  │                  │  │  Transformers      │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Web Server** | Handle HTTP requests, render templates, serve static assets |
| **RAG Engine** | Process queries, retrieve context, generate responses |
| **ETL Pipeline** | Extract, transform, and load CORDIS data |
| **Dgraph** | Store and query graph-structured project data |
| **Mistral AI** | Generate natural language responses |
| **Sentence Transformers** | Create semantic embeddings for similarity search |

## 3. Core Components

### 3.1 RAG Engine (`src/retrieve/CORDISRetriever.py`)

The heart of MAPIT's intelligence. Implements Retrieval-Augmented Generation for accurate, contextual responses.

```
Query Flow:
┌─────────┐    ┌──────────────┐    ┌─────────────────┐
│  User   │───▶│   Encode     │───▶│    Retrieve     │
│  Query  │    │   Query      │    │    Context      │
└─────────┘    └──────────────┘    └────────┬────────┘
                                            │
                                   ┌────────▼────────┐
                                   │  - PDF Docs     │
                                   │  - Topic Data   │
                                   │  - History      │
                                   └────────┬────────┘
                                            │
┌─────────┐    ┌──────────────┐    ┌────────▼────────┐
│Response │◀───│   Generate   │◀───│  Build Prompt   │
│         │    │   (LLM)      │    │  with Context   │
└─────────┘    └──────────────┘    └─────────────────┘
```

**Key Methods:**

- `encode(text)`: Generate embeddings using sentence transformers
- `get_base_information()`: Retrieve relevant PDF chunks
- `get_CORDIS_topic_info()`: Query Dgraph for topic-related projects
- `get_relevant_history()`: Get relevant conversation history
- `ask_llm(prompt)`: Send prompt to Mistral and get response

**Configuration:**

```python
# Model settings
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
LLM_MODEL = "mistral-large-latest"
MAX_TOKENS = 131072
SIMILARITY_THRESHOLD = 0.8
HISTORY_LIMIT = 10
```

### 3.2 ETL Pipeline

#### 3.2.1 Project Reader (`src/etl/CORDISProjectReader.py`)

Handles loading CORDIS project data from CSV files.

**Data Model:**

```python
@dataclass
class CORDISProject:
    id: str
    acronym: str
    status: str
    title: str
    startDate: datetime
    endDate: datetime
    totalCost: float
    ecMaxContribution: float
    legalBasis: str
    topics: str
    frameworkProgramme: str
    fundingScheme: str
    nature: str
    objective: str
    keywords: List[str]
```

**Currency Handling:**

Supports multiple formats:
- German: `101.131.292,00`
- US: `101,131,292.00`
- Standardized output: `101131292.00`

#### 3.2.2 Graph Builder (`src/etl/MAPITGraphBuilder.py`)

Creates relationships between projects based on shared topics.

```
Project A ──[SIMILAR_TOPIC]──▶ Project B
    │                              │
    ├── topic: "AI"                ├── topic: "AI"
    └── topic: "Health"            └── topic: "Robotics"
```

### 3.3 Web Interface (`src/gui/`)

Simple, responsive chat interface using Flask + Bootstrap.

**Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Render chat interface |
| `/query` | POST | Process user query, return response |

**Frontend Components:**

- `templates/index.html`: Main chat interface
- `static/script.js`: Form handling, message rendering
- `static/styles.css`: Custom styling

## 4. Data Architecture

### 4.1 Dgraph Schema

```graphql
type Project {
    id: String! @id
    acronym: String
    status: String
    title: String @search(by: [fulltext])
    startDate: DateTime
    endDate: DateTime
    totalCost: Float
    ecMaxContribution: Float
    legalBasis: String
    topics: String @search(by: [fulltext])
    frameworkProgramme: String @search(by: [term])
    fundingScheme: String
    nature: String
    objective: String @search(by: [fulltext])
    keywords: [String] @search(by: [term])
    relatedProjects: [Project] @reverse
}
```

### 4.2 Data Sources

| Source | Format | Update Frequency | Description |
|--------|--------|------------------|-------------|
| CORDIS CSV | CSV | Weekly | Project metadata and descriptions |
| CORDIS PDFs | PDF | On-demand | Detailed project documentation |
| CORDIS API | REST | Real-time | Bulk data extraction |
| Topic Mappings | Python Dict | Manual | EU program topic hierarchies |

### 4.3 Embedding Storage

Embeddings are computed on-demand and cached in memory:
- PDF chunk embeddings
- Topic title embeddings
- Query embeddings

## 5. AI/ML Pipeline

### 5.1 Embedding Pipeline

```python
# Sentence Transformer Configuration
model = SentenceTransformer('all-mpnet-base-v2')
embedding_dim = 768

# Encoding process
def encode(text: str) -> np.ndarray:
    return model.encode(text, convert_to_tensor=True)
```

### 5.2 Similarity Search

Uses cosine similarity for matching:

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

**Thresholds:**
- PDF matching: 0.8+
- Topic matching: 0.75+
- History relevance: 0.7+

### 5.3 LLM Integration

**Mistral AI Configuration:**

```python
client = MistralClient(api_key=MISTRAL_API_KEY)

response = client.chat(
    model="mistral-large-latest",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ],
    max_tokens=4096,
    temperature=0.7
)
```

## 6. Deployment Architecture

### 6.1 Docker Configuration

```yaml
# docker-compose.yml
services:
  flask_app:
    build: ./src/gui
    ports:
      - "5000:5000"
    environment:
      - PYTHONPATH=/app/src
      - DGRAPH_HOST=dgraph
      - DGRAPH_PORT=9080
    depends_on:
      - dgraph

  dgraph:
    image: dgraph/standalone:latest
    ports:
      - "8080:8080"
      - "9080:9080"
```

### 6.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MISTRAL_API_KEY` | Mistral AI API key | Required |
| `DGRAPH_HOST` | Dgraph server host | localhost |
| `DGRAPH_PORT` | Dgraph gRPC port | 9080 |
| `FLASK_ENV` | Flask environment | development |

## 7. Security Considerations

### 7.1 Current Implementation

- API keys stored in `.env` (gitignored)
- No user authentication (single-user mode)
- Input sanitization on web forms

### 7.2 Production Requirements

- [ ] Implement user authentication (OAuth2/OIDC)
- [ ] Add rate limiting on API endpoints
- [ ] Enable HTTPS with valid certificates
- [ ] Implement API key rotation
- [ ] Add input validation for all endpoints
- [ ] GDPR compliance for EU users
- [ ] Audit logging for sensitive operations

## 8. Performance Considerations

### 8.1 Current Bottlenecks

1. **Embedding Generation**: CPU-bound, ~100ms per query
2. **LLM Response**: Network-bound, 2-5 seconds
3. **Dgraph Queries**: Fast (<50ms) but unoptimized

### 8.2 Optimization Opportunities

- [ ] GPU acceleration for embeddings
- [ ] Embedding caching with Redis
- [ ] Query result caching
- [ ] Connection pooling for Dgraph
- [ ] Streaming LLM responses

## 9. Monitoring and Observability

### 9.1 Recommended Metrics

- Request latency (P50, P95, P99)
- LLM token usage and costs
- Error rates by endpoint
- Dgraph query performance
- Cache hit/miss ratios

### 9.2 Logging Strategy

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

## 10. Future Architecture Considerations

### 10.1 Scalability

- Horizontal scaling with load balancer
- Distributed Dgraph cluster
- Microservices architecture for RAG components

### 10.2 Feature Expansion

- Multi-tenant support
- Real-time collaboration
- Advanced analytics dashboard
- Proposal document generation
- Consortium matching algorithms

## 11. References

- [Dgraph Documentation](https://dgraph.io/docs/)
- [Mistral AI API](https://docs.mistral.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [CORDIS Database](https://cordis.europa.eu/)
- [Flask Documentation](https://flask.palletsprojects.com/)
