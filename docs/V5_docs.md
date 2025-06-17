# CORDIS Research Projects API Documentation (V5)

## Overview

This API provides a Retrieval-Augmented Generation (RAG) interface for querying European research projects from the CORDIS database. V5 introduces **local database integration** for significantly faster performance and richer data access.

- **V5** supports both CORDIS API and local PostgreSQL database modes for project retrieval
- Local database provides 3-5x faster response times with enriched consortium and financial data
- Supports both OpenAI and Gemini as AI providers with dynamic provider/model selection
- Implements enhanced 6-phase RAG pipeline with intelligent project selection
- Backward compatible with V2, V3, and V4 logic using the `ai_version` parameter
- **XML enrichment** included for CORDIS API mode to match V4 functionality

## Key V5 Features

### 🚀 **Performance Enhancements**
- **Local Database Mode**: Query pre-structured project data from PostgreSQL with full-text search
- **Connection Pooling**: Efficient database connection management (1-20 connections)
- **Multi-level Caching**: API calls, database queries, XML data, and preprocessed queries
- **Intelligent Query Preprocessing**: Domain-specific keyword expansion and query optimization
- **Concurrent XML Enrichment**: Parallel processing for CORDIS API mode (inherited from V4)

### 📊 **Richer Data Access**
- **Enhanced Full-Text Search**: PostgreSQL tsvector with relevance scoring
- **Comprehensive Consortium Data**: Participant counts, SME involvement, coordinator details
- **Financial Intelligence**: EU contributions, total costs, budget analysis with filtering
- **Geographic Intelligence**: NUTS codes, country/city distributions, multi-country analysis
- **Program Intelligence**: Framework programmes, funding schemes, legal basis information
- **Temporal Analysis**: Date-based filtering and trend analysis

### 🎯 **Smart Selection & Ranking**
- **Adaptive Result Selection**: Intelligent project selection based on relevance, recency, and significance
- **Enhanced Relevance Scoring**: PostgreSQL ts_rank_cd with custom scoring algorithms
- **Portfolio Analysis**: Automatic insights extraction (temporal, geographic, budget, framework trends)
- **Multi-criteria Ranking**: Combines database relevance with LLM-based reranking

### 🔍 **Enhanced RAG Pipeline**
- **Phase 1**: Query extraction with enhanced preprocessing
- **Phase 2**: Enhanced data retrieval (local DB with intelligent selection OR CORDIS API)
- **Phase 3**: Project data extraction (CORDIS API mode only)
- **Phase 3.5**: XML enrichment with concurrent processing (CORDIS API mode only)
- **Phase 4**: Enhanced reranking with multiple criteria
- **Phase 6**: Enhanced answer generation with portfolio insights

## V5 Architecture

### Database Mode Features
```
Query → Preprocessing → Full-Text Search → Adaptive Selection → Portfolio Analysis → Answer
  ↓         ↓              ↓                    ↓                  ↓              ↓
Cache    Domain       PostgreSQL         Relevance +         Temporal +      Enhanced
Check    Keywords     tsvector          Recency +           Geographic +     Summaries
         Expansion    ts_rank_cd        Budget +            Budget +         + Insights
                                       Diversity           Framework
```

### CORDIS API Mode Features  
```
Query → Preprocessing → API Search → Data Extraction → XML Enrichment → Reranking → Answer
  ↓         ↓            ↓             ↓                ↓                ↓          ↓
Cache    Domain       Concurrent     Standard         Parallel         LLM +      Enhanced
Check    Keywords     Requests       JSON             HTTP             Algo       Summaries
         Expansion                   Parsing          Processing       Scoring    + Insights
```

## Configuration

The API uses the following environment variables:

### AI Provider Configuration
- `DEFAULT_AI_PROVIDER`: The default AI provider to use ("openai" or "gemini", defaults to "gemini")
- `OPENAI_API_KEY`: API key for OpenAI services
- `GEMINI_API_KEY`: API key for Google Gemini services
- `OPENAI_MODEL`: The model to use for OpenAI (default: "gpt-4-turbo")
- `GEMINI_MODEL`: The model to use for Gemini (default: "gemini-2.5-flash-preview-05-20")

### V5 Database Configuration
- `USE_LOCAL_DB`: Enable local database mode globally ("true" or "false", default: "false")
- `DATABASE_URL`: PostgreSQL connection string for local database
  ```
  DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"
  ```

### Docker Configuration
V5 includes Docker-aware database URL handling for containerized deployments:
- Automatically detects Docker environment
- Replaces `localhost` with appropriate container networking
- Supports both local development and Docker Compose setups

## API Endpoints

### Health Check

#### GET /

Simple health check to verify the API is running.

**Response:**
```json
{
  "status": "online",
  "message": "CORDIS RAG API is running"
}
```

#### GET /api/health

Enhanced health check with V5 database status and all component information.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "api": "online",
    "providers": {
      "V5": {
        "openai": {"status": "configured", "supports_local_db": true},
        "gemini": {"status": "configured", "supports_local_db": true}
      }
    },
    "database": {
      "status": "connected",
      "url_configured": true,
      "local_db_enabled": true
    }
  },
  "versions": {
    "v2": true,
    "v3": true,
    "v4": true,
    "v5": true
  }
}
```

### Provider Information

#### GET /api/providers

Lists all available AI providers and their configured models for V2, V3, V4, and V5, including V5-specific database features.

**Response:**
```json
{
  "available_providers": {
    "V5": {
      "openai": {
        "model": "gpt-4-turbo",
        "is_default": false,
        "supports_local_db": true,
        "local_db_enabled": true,
        "database_available": true
      },
      "gemini": {
        "model": "gemini-2.5-flash-preview-05-20",
        "is_default": true,
        "supports_local_db": true,
        "local_db_enabled": true,
        "database_available": true
      }
    }
  },
  "default_provider": "gemini",
  "v5_features": {
    "local_database_support": true,
    "global_local_db_setting": true,
    "database_configured": true
  }
}
```

### Database Management

#### GET /api/database/status

Check the status of the local database connection for V5.

**Response:**
```json
{
  "status": "connected", 
  "message": "Database connection successful",
  "use_local_db": true,
  "database_url": "postgresql://***@host.docker.internal:54322/***",
  "docker_env": true
}
```

**Possible Status Values:**
- `connected`: Database is connected and ready
- `not_configured`: DATABASE_URL not provided
- `not_connected`: Database pool not initialized  
- `error`: Connection failed

**Docker Environment Detection:**
The API automatically detects Docker environments and adjusts database URLs accordingly, replacing `localhost` with `host.docker.internal` for proper container networking.

### Query Endpoints

#### POST /api/query

The main endpoint for querying CORDIS projects with natural language questions. V5 enhanced with local database support and performance metrics.

**Request Body:**
```json
{
  "question": "What European research projects focus on AI in healthcare from the last 3 years?",
  "max_results": 5,
  "ai_provider": "openai",
  "ai_version": "V5",
  "use_local_db": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | string | Yes | Natural language question about European research projects |
| max_results | integer | No | Maximum number of projects to retrieve (default: 5) |
| ai_provider | string | No | AI provider to use ("openai" or "gemini"). If not specified, uses the default provider |
| ai_version | string | No | RAG logic version to use ("V2", "V3", "V4", or "V5"). Default: "V5" |
| use_local_db | boolean | No | **V5 ONLY**: Override global USE_LOCAL_DB setting per request. `true` = use local database, `false` = use CORDIS API |

**Enhanced V5 Response:**
```json
{
  "answer": "Based on our local CORDIS database, there are several notable AI initiatives in healthcare from recent years. The **FeatureCloud** project focuses on federated learning for medical data analysis, coordinated by the University of Hamburg (Germany) with 12 participants from 8 countries including 3 SMEs involved. This project runs from 2019-2023 with a total budget of €3.2M under Horizon 2020.\n\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/826078\n\nAnother significant initiative is the **Human Brain Project SGA3** which develops AI-driven brain simulation platforms...",
  "ai_provider": "openai",
  "ai_version": "V5",
  "model_used": "gpt-4-turbo",
  "data_source": "Local Database",
  "processing_time": 1.23,
  "projects_found": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| answer | string | Comprehensive AI-generated response with CORDIS links |
| ai_provider | string | AI provider used for generation |
| ai_version | string | RAG version used |
| model_used | string | Specific model used |
| data_source | string | "Local Database" or "CORDIS API" |
| processing_time | float | Time taken to process request (seconds) |
| projects_found | integer | Number of projects found and referenced |

#### POST /api/query/benchmark

**V5 Exclusive**: Benchmark endpoint to compare local database vs CORDIS API performance.

**Request Body:**
```json
{
  "question": "renewable energy projects in Europe",
  "ai_version": "V5",
  "ai_provider": "gemini"
}
```

**Response:**
```json
{
  "question": "renewable energy projects in Europe", 
  "ai_provider": "gemini",
  "benchmark_results": {
    "local_database": {
      "processing_time": 1.45,
      "answer_length": 2847,
      "projects_found": 4,
      "status": "success"
    },
    "cordis_api": {
      "processing_time": 8.32,
      "answer_length": 2654, 
      "projects_found": 4,
      "status": "success"
    },
    "comparison": {
      "speedup_factor": 5.7,
      "time_saved": 6.87,
      "local_faster": true
    }
  }
}
```

#### POST /api/demo

Enhanced demo endpoint with V5 simulation including local database performance benefits.

**Request Body:**
```json
{
  "question": "What is the impact of climate change on biodiversity?",
  "ai_version": "V5",
  "use_local_db": true
}
```

**Response:**
```json
{
  "answer": "Based on the European research projects data, there are several notable initiatives addressing climate change impacts on biodiversity. The ADAPT project studies ecosystem adaptation strategies across 14 European countries with €4.2M funding...",
  "ai_provider": "gemini",
  "ai_version": "V5",
  "data_source": "Local Database (Demo)",
  "processing_time": 1.2,
  "projects_found": 6,
  "demo": true,
  "query": "What is the impact of climate change on biodiversity?"
}
```

## V5 Database Features Deep Dive

### Enhanced Search Capabilities

**Full-Text Search with PostgreSQL:**
```sql
-- Example of V5's enhanced search query
SELECT p.title, p.objective, 
       ts_rank_cd(to_tsvector('english', p.title || ' ' || p.objective), 
                  to_tsquery('english', 'artificial & intelligence'), 32) as relevance
FROM projects p
WHERE to_tsvector('english', p.title || ' ' || p.objective) @@ 
      to_tsquery('english', 'artificial & intelligence')
ORDER BY relevance DESC;
```

**Smart Query Preprocessing:**
- Domain-specific keyword expansion (AI/ML, energy, health, mobility, environment, digital)
- Stopword filtering and term optimization
- OR/AND logic conversion to PostgreSQL tsquery format
- Date and budget query parsing

**Adaptive Result Selection Algorithm:**
```python
# V5's intelligent project scoring
score = (relevance_score * 10) +           # Database relevance
        (recency_bonus * 5) +              # More recent = higher score  
        (budget_significance * 5) +        # Larger budget = more significant
        (geographic_diversity * 3) +       # Multi-country bonus
        (sme_involvement * 2) +            # SME participation bonus
        (keyword_matches * 2)              # Question-specific matching
```

### Rich Consortium Data

**Available Fields:**
- **Participant Count**: Total number of organizations involved
- **Country Distribution**: Number of countries and specific country list
- **SME Involvement**: Count and percentage of Small-Medium Enterprises
- **Coordinator Details**: Lead organization name, country, and city
- **Geographic Codes**: NUTS codes for regional analysis
- **Activity Types**: Organization activity classifications
- **Financial Breakdown**: EC contributions, net contributions, total costs per organization

**Enhanced Project Summaries:**
```
**FeatureCloud (826078)** [Relevance: 8.45]
📅 Duration: 2019-01-01 to 2022-12-31 (Status: CLOSED)
🏛️ Programme: H2020-EU.3.1. / RIA
💰 Budget: €3,200,000
🔗 CORDIS Link: https://cordis.europa.eu/project/id/826078
🤝 Consortium: Coordinated by University Medical Center Hamburg-Eppendorf (Germany) | 12 participants from 8 countries (including 3 SMEs)

Federated learning platform enabling privacy-preserving machine learning across distributed healthcare datasets. The project develops secure multi-party computation protocols for training AI models without centralizing sensitive medical data...
```

## Usage Examples

### JavaScript (Fetch API)

```javascript
// Query with V5 local database for faster performance
async function queryProjectsV5(question, useLocalDb = true) {
  const response = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question,
      max_results: 5,
      ai_version: "V5",
      use_local_db: useLocalDb  // Override global database setting
    })
  });
  
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  const result = await response.json();
  
  console.log(`Response from ${result.data_source} in ${result.processing_time}s`);
  console.log(`Found ${result.projects_found} projects`);
  
  return result;
}

// Example: Force CORDIS API even if local DB is enabled globally
async function queryWithCordisAPI(question) {
  return await queryProjectsV5(question, false);  // use_local_db: false
}

// Example: Force local database even if CORDIS API is default
async function queryWithLocalDB(question) {
  return await queryProjectsV5(question, true);   // use_local_db: true
}

// Benchmark local database vs API performance
async function benchmarkPerformance(question) {
  const response = await fetch('http://localhost:8000/api/query/benchmark', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question,
      ai_version: "V5"
    })
  });
  
  if (!response.ok) throw new Error(`Benchmark error: ${response.status}`);
  const result = await response.json();
  
  const comparison = result.benchmark_results.comparison;
  console.log(`Local DB is ${comparison.speedup_factor}x faster, saving ${comparison.time_saved}s`);
  console.log(`Main bottleneck in API mode: ${comparison.main_bottleneck_api}`);
  
  return result;
}

// Advanced V5 query with all options
async function advancedV5Query() {
  const response = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: "AI projects in healthcare with SME participation from last 5 years",
      max_results: 8,
      ai_version: "V5",
      ai_provider: "gemini",
      use_local_db: true
    })
  });
  
  const result = await response.json();
  
  // Extract insights from response
  console.log(`🔍 Query: ${result.answer.match(/User Question: (.+)/)?.[1]}`);
  console.log(`📊 Data source: ${result.data_source}`);
  console.log(`⚡ Processing time: ${result.processing_time}s`);
  console.log(`📈 Projects found: ${result.projects_found}`);
  
  return result;
}
```

### Python (Requests)

```python
import requests
import time
import json

def query_projects_v5(question, use_local_db=True, provider="gemini"):
    """Query projects using V5 with optional local database"""
    payload = {
        'question': question,
        'max_results': 5,
        'ai_version': 'V5',
        'ai_provider': provider,
        'use_local_db': use_local_db
    }
    
    start_time = time.time()
    response = requests.post('http://localhost:8000/api/query', json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Query completed in {result['processing_time']}s using {result['data_source']}")
        print(f"📊 Found {result['projects_found']} projects")
        return result
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

def benchmark_performance(question):
    """Compare local database vs CORDIS API performance with detailed analysis"""
    response = requests.post('http://localhost:8000/api/query/benchmark', json={
        'question': question,
        'ai_version': 'V5'
    })
    
    if response.status_code == 200:
        result = response.json()
        comparison = result['benchmark_results']['comparison']
        local_phases = result['benchmark_results']['local_database']['pipeline_phases']
        api_phases = result['benchmark_results']['cordis_api']['pipeline_phases']
        
        print(f"🏃‍♂️ Performance Comparison for: '{question}'")
        print(f"Local DB: {result['benchmark_results']['local_database']['processing_time']}s")
        print(f"CORDIS API: {result['benchmark_results']['cordis_api']['processing_time']}s")
        print(f"Speedup: {comparison['speedup_factor']}x faster with local database")
        print(f"Time saved: {comparison['time_saved']}s")
        
        print(f"\n📊 Phase Breakdown:")
        print(f"Local DB phases: {json.dumps(local_phases, indent=2)}")
        print(f"API phases: {json.dumps(api_phases, indent=2)}")
        
        return result
    else:
        raise Exception(f"Benchmark error: {response.status_code}")

def check_database_status():
    """Check if local database is available with detailed stats"""
    response = requests.get('http://localhost:8000/api/database/status')
    status = response.json()
    
    if status['status'] == 'connected':
        print("✅ Local database connected and ready")
        if 'stats' in status:
            stats = status['stats']
            print(f"📊 Database contains {stats['total_projects']} projects")
            print(f"📅 Date range: {stats['date_range'][0]} to {stats['date_range'][1]}")
            print(f"🏛️ Framework programmes: {stats['frameworks']}")
            print(f"💰 Funding schemes: {stats['funding_schemes']}")
    else:
        print(f"⚠️ Database status: {status['status']} - {status['message']}")
    
    return status

def analyze_v5_capabilities():
    """Demonstrate V5's advanced search capabilities"""
    
    # Test different query types
    test_queries = [
        "AI projects in healthcare with high SME participation",
        "renewable energy projects from Germany and France after 2020",
        "quantum computing research with budget over 5 million euros",
        "climate change adaptation projects in Mediterranean countries"
    ]
    
    print("🔬 Testing V5's Advanced Search Capabilities")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {query}")
        try:
            result = query_projects_v5(query, use_local_db=True)
            print(f"   ✅ Found {result['projects_found']} projects in {result['processing_time']}s")
            
            # Extract sample project info
            if 'answer' in result and 'CORDIS Link:' in result['answer']:
                links = [line.strip() for line in result['answer'].split('\n') 
                        if 'CORDIS Link:' in line]
                if links:
                    print(f"   🔗 Sample: {links[0]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

# Example usage with error handling
if __name__ == "__main__":
    try:
        # Check database availability
        db_status = check_database_status()
        
        if db_status['status'] == 'connected':
            # Test advanced capabilities
            analyze_v5_capabilities()
            
            # Benchmark performance
            print(f"\n🏁 Performance Benchmark")
            print("=" * 60)
            benchmark_performance("machine learning projects in healthcare")
            
        else:
            # Fallback to CORDIS API
            print("\n🔄 Fallback to CORDIS API mode")
            result = query_projects_v5("AI projects in healthcare", use_local_db=False)
            print(f"Answer preview: {result['answer'][:200]}...")
            
    except Exception as e:
        print(f"❌ Error in example execution: {e}")
```

### Environment Setup

```bash
# .env file configuration for V5
DEFAULT_AI_PROVIDER=gemini
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENAI_MODEL=gpt-4-turbo
GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# V5 Database Configuration
USE_LOCAL_DB=true
DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Optional: Docker environment detection (automatically set by Docker)
DOCKER_ENV=true  # Set in Docker containers
```

### Docker Compose Example

```yaml
# docker-compose.yml  
version: '3.8'
services:
  cordis-rag-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - USE_LOCAL_DB=true
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/cordis
      - DOCKER_ENV=true
      - DEFAULT_AI_PROVIDER=gemini
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=cordis
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

**Note:** The API automatically handles Docker networking by detecting the Docker environment and replacing `localhost` with `host.docker.internal` in database URLs when needed.

## Performance Comparison

| Feature | V4 (CORDIS API) | V5 (Local DB) | V5 (CORDIS API) |
|---------|----------------|---------------|-----------------|
| **Average Response Time** | 8-15 seconds | 1-3 seconds | 8-15 seconds |
| **Query Preprocessing** | Basic | Enhanced with domain keywords | Enhanced with domain keywords |
| **Search Method** | API + XML enrichment | PostgreSQL full-text search | API + XML enrichment |
| **Relevance Scoring** | LLM-based | ts_rank_cd + algorithmic | ts_rank_cd + algorithmic |
| **Result Selection** | Sequential | Adaptive intelligence | Adaptive intelligence |
| **Consortium Data** | Basic | Comprehensive | Enhanced via XML |
| **Financial Information** | Limited | Full breakdown | Enhanced via XML |
| **Geographic Insights** | Basic | NUTS codes + analysis | Enhanced via XML |
| **Caching Strategy** | API + XML | Multi-level (4 types) | Multi-level (4 types) |
| **Offline Capability** | No | Yes (full) | No |
| **SME Analysis** | No | Yes (counts + percentage) | Basic |
| **Portfolio Insights** | No | Yes (auto-generated) | Yes (auto-generated) |
| **Concurrent Processing** | XML only | Database queries | XML enrichment |

## Error Handling

The API returns standard HTTP status codes with enhanced error details for V5:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters or V5-specific validation errors
- `500 Internal Server Error`: Server-side error including database connection issues

**V5 Enhanced Error Response:**
```json
{
  "error": "Error processing request",
  "details": "Database connection failed: connection timeout"
}
```

**Database Status Response:**
```json
{
  "status": "connected",
  "message": "Database connection successful",
  "use_local_db": true,
  "database_url": "postgresql://***@host.docker.internal:54322/***",
  "docker_env": true
}
```

**Error Response for Query:**
```json
{
  "error": "Error processing request",
  "details": "Database connection failed: connection timeout"
}
```

## V5 Database Schema

The local database includes rich project and organization data optimized for fast retrieval:

### Projects Table
```sql
CREATE TABLE projects (
    id VARCHAR PRIMARY KEY,
    rcn VARCHAR,
    title TEXT NOT NULL,
    acronym VARCHAR,
    objective TEXT,
    "startDate" DATE,
    "endDate" DATE,
    status VARCHAR,
    "totalCost" BIGINT,
    "ecMaxContribution" BIGINT,
    "frameworkProgramme" VARCHAR,
    "fundingScheme" VARCHAR,
    "legalBasis" VARCHAR,
    topics TEXT,
    "grantDoi" VARCHAR,
    
    -- Full-text search indexes
    CONSTRAINT projects_title_idx GIN (to_tsvector('english', title)),
    CONSTRAINT projects_objective_idx GIN (to_tsvector('english', objective))
);
```

### Organizations Table
```sql
CREATE TABLE organizations (
    "organisationID" VARCHAR PRIMARY KEY,
    "projectID" VARCHAR REFERENCES projects(id),
    name TEXT,
    "legalName" TEXT,
    role VARCHAR, -- 'coordinator', 'participant'
    country VARCHAR,
    city VARCHAR,
    "nutsCode" VARCHAR,
    "activityType" VARCHAR,
    "SME" BOOLEAN DEFAULT FALSE,
    "ecContribution" BIGINT,
    "netEcContribution" BIGINT,
    "totalCost" BIGINT,
    
    -- Geographic and organizational indexes
    INDEX organizations_country_idx (country),
    INDEX organizations_sme_idx ("SME"),
    INDEX organizations_role_idx (role)
);
```

### Key Optimizations
- **Full-text search indexes** on title, objective, and topics
- **Compound indexes** for common query patterns
- **Materialized views** for complex aggregations
- **Connection pooling** for concurrent access
- **Query result caching** for repeated requests

## Limitations and Considerations

### V5 Specific
1. **Database Dependency**: Enhanced features require PostgreSQL setup and maintenance
2. **Data Freshness**: Local database may lag behind live CORDIS by 24-48 hours
3. **Storage Requirements**: Full CORDIS dataset requires ~5-10GB storage
4. **Memory Usage**: Connection pooling and caching increase memory footprint
5. **Index Maintenance**: Full-text indexes require periodic optimization

### General
1. **Rate Limits**: API calls to OpenAI/Gemini have rate limitations
2. **Query Complexity**: Very complex nested queries may timeout
3. **Language Support**: Optimized for English, limited multilingual support
4. **Historical Data**: Older projects may have incomplete consortium information

### Recommendations
1. **Production Setup**: Use dedicated PostgreSQL instance with sufficient resources
2. **Monitoring**: Implement database performance monitoring
3. **Backup Strategy**: Regular database backups for data protection
4. **Update Cycle**: Establish process for refreshing local database from CORDIS
5. **Scaling**: Consider read replicas for high-traffic scenarios

---

## V5 Complete Changelog

### ✅ **Core Enhancements**
- **Local PostgreSQL Database Integration**: 3-5x faster queries with comprehensive data
- **Enhanced 6-Phase RAG Pipeline**: Optimized flow from query to answer
- **Intelligent Project Selection**: Multi-criteria adaptive ranking algorithm
- **Portfolio Analysis Engine**: Automatic insights extraction and trend analysis
- **Advanced Query Preprocessing**: Domain-specific keyword expansion and optimization

### ✅ **Performance Optimizations**
- **Connection Pooling**: Efficient database connection management (1-20 connections)
- **Multi-level Caching**: API, database, XML, and query preprocessing caches
- **Concurrent Processing**: Parallel XML enrichment inherited from V4
- **Smart Query Optimization**: PostgreSQL tsvector with relevance scoring
- **Docker-Aware Networking**: Automatic container environment detection

### ✅ **Rich Data Access**
- **Full-Text Search**: PostgreSQL ts_rank_cd with custom relevance algorithms
- **Comprehensive Consortium Data**: SME counts, coordinator details, geographic distribution
- **Financial Intelligence**: Multi-level budget analysis with EU contribution breakdowns
- **Geographic Intelligence**: NUTS codes, country distributions, multi-country analysis
- **Temporal Intelligence**: Date-based filtering with trend analysis

### ✅ **Developer Experience**
- **Enhanced Error Handling**: Context-aware error messages with suggestions
- **Benchmark Tools**: Performance comparison between local DB and CORDIS API
- **Backward Compatibility**: Full compatibility with V2, V3, and V4 endpoints
- **Advanced Documentation**: Comprehensive examples and usage patterns
- **Docker Support**: Container-ready with environment-specific configurations

### ✅ **Answer Quality**
- **Enhanced Project Summaries**: Rich formatting with consortium and financial details
- **CORDIS Link Preservation**: Guaranteed inclusion of project links in responses
- **Portfolio Insights**: Automatic trend analysis and pattern recognition
- **Relevance Scoring**: Database-level relevance combined with LLM ranking
- **Structured Responses**: Consistent formatting with emoji indicators and clear sections

**Migration Path from V4:**
- V5 maintains full API compatibility with V4
- Local database mode provides immediate performance benefits
- Enhanced consortium data enriches existing workflows
- Benchmark tools help quantify performance improvements
- Fallback to CORDIS API mode ensures reliability during database maintenance