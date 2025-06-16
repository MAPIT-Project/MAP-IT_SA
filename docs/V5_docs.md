# CORDIS Research Projects API Documentation (V5)

## Overview

This API provides a Retrieval-Augmented Generation (RAG) interface for querying European research projects from the CORDIS database. V5 introduces **local database integration** for significantly faster performance and richer data access.

- **V5** supports both CORDIS API and local Supabase database modes for project retrieval
- Local database provides 3-5x faster response times with richer consortium and financial data
- Supports both OpenAI and Gemini as AI providers, with dynamic provider/model selection
- Implements enhanced 2-phase RAG logic with performance optimizations
- Backward compatible with V2, V3, and V4 logic using the `ai_version` parameter

## Key V5 Features

### 🚀 **Performance Enhancements**
- **Local Database Mode**: Query pre-structured project data from Supabase PostgreSQL
- **Concurrent Processing**: Parallel XML enrichment and database queries
- **Smart Caching**: Multi-level caching for API calls, database queries, and XML data
- **Connection Pooling**: Efficient database connection management

### 📊 **Richer Data Access**
- **Enhanced Consortium Information**: Detailed participant roles, SME counts, geographic distribution
- **Financial Intelligence**: EU contributions, total costs, partner funding breakdowns
- **Geographic Insights**: NUTS codes, country/city distributions, coordinator details
- **Program Context**: Framework programmes, funding schemes, call information

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
- `DATABASE_URL`: PostgreSQL connection string for Supabase database
  ```
  DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"
  ```

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
      "V2": {
        "openai": {"status": "configured"},
        "gemini": {"status": "configured"}
      },
      "V3": {
        "openai": {"status": "configured"},
        "gemini": {"status": "configured"}
      },
      "V4": {
        "openai": {"status": "configured"},
        "gemini": {"status": "configured"}
      },
      "V5": {
        "openai": {"status": "configured"},
        "gemini": {"status": "configured"}
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
    "V2": {
      "openai": {"model": "gpt-4-turbo", "is_default": false},
      "gemini": {"model": "gemini-2.5-flash-preview-05-20", "is_default": true}
    },
    "V3": {
      "openai": {"model": "gpt-4-turbo", "is_default": false},
      "gemini": {"model": "gemini-2.5-flash-preview-05-20", "is_default": true}
    },
    "V4": {
      "openai": {"model": "gpt-4-turbo", "is_default": false},
      "gemini": {"model": "gemini-2.5-flash-preview-05-20", "is_default": true}
    },
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
  "database_url": "postgresql://***@localhost:54322/postgres"
}
```

**Possible Status Values:**
- `connected`: Database is connected and ready
- `not_configured`: DATABASE_URL not provided
- `not_connected`: Database pool not initialized
- `error`: Connection failed

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
| use_local_db | boolean | No | Override global database setting for V5 (V5 only) |

**Enhanced V5 Response:**
```json
{
  "answer": "Based on our local CORDIS database, there are several notable AI initiatives in healthcare from recent years...",
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
  "answer": "Based on the European research projects data, there are several notable...",
  "ai_provider": "gemini",
  "ai_version": "V5",
  "data_source": "Local Database (Demo)",
  "processing_time": 1.2,
  "projects_found": 6,
  "demo": true,
  "query": "What is the impact of climate change on biodiversity?"
}
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
      use_local_db: useLocalDb
    })
  });
  
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  const result = await response.json();
  
  console.log(`Response from ${result.data_source} in ${result.processing_time}s`);
  console.log(`Found ${result.projects_found} projects`);
  
  return result;
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
  
  return result;
}

// Check database status
async function checkDatabaseStatus() {
  const response = await fetch('http://localhost:8000/api/database/status');
  const status = await response.json();
  
  if (status.status === 'connected') {
    console.log('✅ Database ready for fast queries');
  } else {
    console.log('⚠️ Database not available, will use CORDIS API');
  }
  
  return status;
}
```

### Python (Requests)

```python
import requests
import time

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
    """Compare local database vs CORDIS API performance"""
    response = requests.post('http://localhost:8000/api/query/benchmark', json={
        'question': question,
        'ai_version': 'V5'
    })
    
    if response.status_code == 200:
        result = response.json()
        comparison = result['benchmark_results']['comparison']
        
        print(f"🏃‍♂️ Performance Comparison:")
        print(f"Local DB: {result['benchmark_results']['local_database']['processing_time']}s")
        print(f"CORDIS API: {result['benchmark_results']['cordis_api']['processing_time']}s")
        print(f"Speedup: {comparison['speedup_factor']}x faster with local database")
        
        return result
    else:
        raise Exception(f"Benchmark error: {response.status_code}")

def check_database_status():
    """Check if local database is available"""
    response = requests.get('http://localhost:8000/api/database/status')
    status = response.json()
    
    if status['status'] == 'connected':
        print("✅ Local database connected and ready")
    else:
        print(f"⚠️ Database status: {status['status']} - {status['message']}")
    
    return status

# Example usage
if __name__ == "__main__":
    # Check database availability
    db_status = check_database_status()
    
    # Query with local database (fast)
    if db_status['status'] == 'connected':
        result = query_projects_v5("AI projects in healthcare", use_local_db=True)
        print(f"Answer preview: {result['answer'][:200]}...")
        
        # Benchmark performance
        benchmark_performance("machine learning projects")
    else:
        # Fallback to CORDIS API
        result = query_projects_v5("AI projects in healthcare", use_local_db=False)
```

### Environment Setup

```bash
# .env file configuration for V5
DEFAULT_AI_PROVIDER=gemini
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here

# V5 Database Configuration
USE_LOCAL_DB=true
DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Supabase Local Development
VITE_SUPABASE_URL="http://localhost:54321"
VITE_SUPABASE_ANON_KEY="your_supabase_anon_key"
```

## Performance Comparison

| Feature | V4 (CORDIS API) | V5 (Local DB) | V5 (CORDIS API) |
|---------|----------------|---------------|-----------------|
| Average Response Time | 8-15 seconds | 1-3 seconds | 8-15 seconds |
| Data Richness | Standard | Enhanced | Standard |
| Consortium Details | Basic | Detailed | Basic |
| Financial Information | Limited | Comprehensive | Limited |
| Geographic Insights | Basic | Advanced | Basic |
| Caching | API + XML | Multi-level | API + XML |
| Offline Capability | No | Yes | No |

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

**Database-Specific Errors:**
```json
{
  "error": "Database not configured",
  "details": "DATABASE_URL required when use_local_db=True"
}
```

## V5 Database Schema

The local database includes rich project and organization data:

### Projects Table
- Basic project information (ID, title, acronym, objective)
- Temporal data (start/end dates, status)
- Financial data (total cost, EU contribution)
- Program context (framework, funding scheme)

### Organizations Table
- Detailed participant information (name, role, SME status)
- Geographic data (country, city, NUTS codes)
- Financial contributions (EC contribution, total costs)
- Organization metadata (activity type, contact info)

## Limitations and Considerations

### V5 Specific
1. **Local Database Dependency**: Enhanced features require proper database setup and maintenance
2. **Data Freshness**: Local database may not have the latest projects compared to live CORDIS API
3. **Storage Requirements**: Local database requires significant storage for full CORDIS dataset

### General
1. **Rate Limits**: API has rate limits based on AI provider limitations
2. **Query Complexity**: Very complex queries may require longer processing time
3. **Data Availability**: Response quality depends on available data in the database/CORDIS

---

**V5 Changelog:**
- ✅ **Local Supabase Database Integration**: 3-5x faster queries with richer data
- ✅ **Enhanced Performance Monitoring**: Detailed timing and caching metrics
- ✅ **Comprehensive Consortium Data**: SME counts, geographic distribution, coordinator details
- ✅ **Advanced Financial Intelligence**: Multi-level budget breakdown and EU funding details
- ✅ **Benchmark Tools**: Compare local database vs CORDIS API performance
- ✅ **Smart Caching**: Multi-level caching for optimal performance
- ✅ **Connection Pooling**: Efficient database connection management
- ✅ **Backward Compatibility**: Full compatibility with V2, V3, and V4 endpoints
- ✅ **Enhanced Error Handling**: Database-specific error reporting and guidance
