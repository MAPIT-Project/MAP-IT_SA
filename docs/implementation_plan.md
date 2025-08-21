# Horizon Europe RAG Implementation Plan

## Phase 1: Supabase Setup and Configuration

### 1.1 Supabase Project Setup
```bash
# Install Supabase CLI
npm install -g supabase

# Initialize Supabase project
supabase init

# Link to your Supabase project
supabase link --project-ref your-project-ref
```

### 1.2 Enable pgvector Extension
```sql
-- Run in Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.3 Environment Variables
```env
# Add to .env file
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
GOOGLE_EMBEDDING_API_KEY=your-google-api-key
```

## Phase 2: Core Services Implementation

### 2.1 Supabase Client Service
`app/services/supabase_service.py`
- Initialize Supabase client
- Handle authentication
- Manage connection pooling

### 2.2 Document Processor Service
`app/services/document_processor.py`
- PDF extraction using PyPDF2/pdfplumber
- Web scraping with BeautifulSoup
- Text cleaning and normalization
- Metadata extraction

### 2.3 Embedding Service
`app/services/embedding_service.py`
- Google text-embedding-004 integration
- Batch embedding generation
- Embedding caching
- Dimension validation (768)

### 2.4 Chunking Service
`app/services/chunking_service.py`
- Smart text chunking with overlap
- Section-aware splitting
- Token counting
- Metadata preservation

### 2.5 Vector Search Service
`app/services/vector_search_service.py`
- Semantic search implementation
- Hybrid search (vector + keyword)
- Result ranking and filtering
- Context window selection

## Phase 3: Database Models

### 3.1 SQLAlchemy Models
```python
# app/models/vector_models.py

class HorizonDocument(Base):
    __tablename__ = 'horizon_documents'
    
    id = Column(UUID, primary_key=True)
    source_type = Column(String)  # pdf, web, cordis
    source_url = Column(String)
    title = Column(String)
    document_type = Column(String)
    programme_year = Column(String)
    metadata = Column(JSONB)
    last_updated = Column(DateTime)
    created_at = Column(DateTime)

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    
    id = Column(UUID, primary_key=True)
    document_id = Column(UUID, ForeignKey('horizon_documents.id'))
    chunk_index = Column(Integer)
    content = Column(Text)
    embedding = Column(Vector(768))
    metadata = Column(JSONB)
    token_count = Column(Integer)
    created_at = Column(DateTime)
```

## Phase 4: API Endpoints

### 4.1 Document Management
```python
# app/api/document_routes.py

POST /api/documents/upload
- Upload PDF/document for processing
- Returns job ID for tracking

GET /api/documents/{document_id}
- Get document details and metadata

DELETE /api/documents/{document_id}
- Remove document and its chunks

GET /api/documents/list
- List all ingested documents with filters
```

### 4.2 Ingestion Pipeline
```python
# app/api/ingestion_routes.py

POST /api/ingest/pdf
- Process PDF document
- Extract text, chunk, generate embeddings

POST /api/ingest/web
- Scrape and process web content
- Handle EU portal pages

GET /api/ingest/status/{job_id}
- Check ingestion job status
```

### 4.3 Vector Search
```python
# app/api/vector_search_routes.py

POST /api/search/semantic
- Pure vector similarity search
- Returns ranked chunks with scores

POST /api/search/hybrid
- Combined vector + keyword search
- Configurable weighting

POST /api/search/filtered
- Search with metadata filters
- Document type, year, source filtering
```

### 4.4 Enhanced RAG
```python
# app/api/rag_routes.py

POST /api/rag/query
- Enhanced query with document context
- Combines CORDIS + document knowledge

POST /api/rag/stream
- Streaming response with citations
- Real-time answer generation
```

## Phase 5: Document Sources and Ingestion Schedule

### 5.1 Priority Documents
1. **Horizon Europe Work Programme 2023-2024**
   - Main work programme documents
   - Specific destination documents
   - Call texts

2. **Programme Guide**
   - Application procedures
   - Evaluation criteria
   - Financial rules

3. **EU Grants AGA**
   - Grant agreement annotations
   - Legal framework
   - Implementation guidance

4. **FAQ Collections**
   - Common questions database
   - Portal help documentation

### 5.2 Web Scraping Targets
- https://ec.europa.eu/info/funding-tenders/
- https://ec.europa.eu/research/participants/
- CORDIS project pages
- National Contact Point resources

### 5.3 Update Schedule
- Daily: Check for new calls and updates
- Weekly: Re-scrape FAQ and help pages
- Monthly: Full document refresh
- On-demand: Manual trigger for critical updates

## Phase 6: Integration with Existing System

### 6.1 Unified Query Interface
```python
class UnifiedRAG:
    def query(self, question: str):
        # 1. Determine intent (projects vs general info)
        intent = self.classify_intent(question)
        
        # 2. Route to appropriate pipeline
        if intent == "PROJECT_SEARCH":
            return self.existing_cordis_search(question)
        elif intent == "GENERAL_INFO":
            return self.vector_document_search(question)
        else:
            return self.hybrid_search(question)
```

### 6.2 Response Merging
- Combine CORDIS project data with document context
- Cross-reference projects with programme documentation
- Provide comprehensive answers with citations

## Phase 7: Testing Strategy

### 7.1 Unit Tests
- Document processing functions
- Chunking algorithms
- Embedding generation
- Vector search accuracy

### 7.2 Integration Tests
- End-to-end ingestion pipeline
- Search result quality
- API endpoint functionality
- Database operations

### 7.3 Performance Tests
- Query response time
- Concurrent request handling
- Large document processing
- Vector search scalability

### 7.4 Quality Metrics
- Search relevance scoring
- Answer accuracy validation
- Citation correctness
- User satisfaction tracking

## Phase 8: Deployment

### 8.1 Docker Configuration
```dockerfile
# Dockerfile additions
RUN pip install supabase pypdf2 pdfplumber
RUN pip install google-cloud-aiplatform
```

### 8.2 Database Migrations
```python
# alembic/versions/xxx_add_vector_tables.py
def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('horizon_documents', ...)
    op.create_table('document_chunks', ...)
```

### 8.3 CI/CD Pipeline
- Automated testing on push
- Document ingestion jobs
- Performance monitoring
- Rollback procedures

## Timeline

### Week 1-2: Infrastructure
- Set up Supabase project
- Configure pgvector
- Create database schema
- Basic authentication

### Week 3-4: Core Services
- Document processor
- Embedding service
- Chunking implementation
- Vector storage

### Week 5-6: Search & Retrieval
- Semantic search
- Hybrid search
- Result ranking
- Context selection

### Week 7-8: Integration
- Merge with existing RAG
- API endpoints
- Testing suite
- Documentation

### Week 9-10: Production
- Performance optimization
- Monitoring setup
- Admin interface
- Launch preparation

## Success Metrics

1. **Search Quality**
   - Precision: >85% relevant results
   - Recall: >80% of relevant documents found
   - MRR (Mean Reciprocal Rank): >0.7

2. **Performance**
   - Query latency: <2 seconds
   - Document ingestion: <30 seconds per PDF
   - Concurrent users: 100+

3. **Coverage**
   - Documents indexed: 100% of priority sources
   - Update frequency: Daily for critical content
   - Language support: EN (primary), other EU languages (future)

4. **User Satisfaction**
   - Answer accuracy: >90% correct
   - Citation quality: All answers properly sourced
   - Feedback score: >4.5/5

## Risk Mitigation

1. **Data Quality**
   - Risk: Poor PDF extraction
   - Mitigation: Multiple extraction libraries, manual validation

2. **Performance**
   - Risk: Slow vector search at scale
   - Mitigation: Proper indexing, caching, query optimization

3. **Cost**
   - Risk: High embedding API costs
   - Mitigation: Batch processing, caching, rate limiting

4. **Maintenance**
   - Risk: Document updates breaking system
   - Mitigation: Versioning, rollback capability, monitoring

## Next Immediate Steps

1. Create Supabase project and get credentials
2. Set up development environment with new dependencies
3. Create database schema in Supabase
4. Build basic document ingestion pipeline
5. Test with sample Horizon Europe PDFs