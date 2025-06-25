# CORDIS Research Projects API Documentation (V3)

## Overview

This API provides a Retrieval-Augmented Generation (RAG) interface for querying European research projects from the CORDIS database. It supports natural language questions and can provide AI-generated responses based on retrieved project data.

- **V3** uses the CORDIS API (no Selenium) for project retrieval, making it faster and more robust.
- Supports both OpenAI and Gemini as AI providers, with dynamic provider/model selection.
- Implements a 2-phase RAG logic: query extraction, retrieval, reranking, and answer generation.
- You can switch between V2 and V3 logic using the `ai_version` parameter in the API.

## Configuration

The API uses the following environment variables:

- `DEFAULT_AI_PROVIDER`: The default AI provider to use ("openai" or "gemini", defaults to "gemini")
- `OPENAI_API_KEY`: API key for OpenAI services
- `GEMINI_API_KEY`: API key for Google Gemini services
- `OPENAI_MODEL`: The model to use for OpenAI (default: "gpt-4-turbo")
- `GEMINI_MODEL`: The model to use for Gemini (default: "gemini-2.5-flash-lite-preview-06-17")

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

Detailed health check with status of all components.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "api": "online",
    "providers": {
      "openai": {"status": "configured"},
      "gemini": {"status": "configured"}
    }
  }
}
```

### Provider Information

#### GET /api/providers

Lists all available AI providers and their configured models for both V2 and V3.

**Response:**
```json
{
  "available_providers": {
    "V2": {
      "openai": {"model": "gpt-4-turbo", "is_default": false},
      "gemini": {"model": "gemini-2.5-flash-lite-preview-06-17", "is_default": true}
    },
    "V3": {
      "openai": {"model": "gpt-4-turbo", "is_default": false},
      "gemini": {"model": "gemini-2.5-flash-lite-preview-06-17", "is_default": true}
    }
  },
  "default_provider": "gemini"
}
```

### Query Endpoints

#### POST /api/query

The main endpoint for querying CORDIS projects with natural language questions.

**Request Body:**
```json
{
  "question": "What European research projects focus on sustainable agriculture?",
  "max_results": 5,
  "ai_provider": "openai",
  "ai_version": "V3"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | string | Yes | Natural language question about European research projects |
| max_results | integer | No | Maximum number of projects to retrieve (default: 5) |
| ai_provider | string | No | AI provider to use ("openai" or "gemini"). If not specified, uses the default provider |
| ai_version | string | No | RAG logic version to use ("V2" or "V3"). Default: "V3" |

**Response:**
```json
{
  "answer": "Based on the retrieved information from the CORDIS database, there are several European research projects focused on sustainable agriculture...",
  "ai_provider": "openai",
  "model_used": "gpt-4-turbo"
}
```

#### POST /api/demo

Simulated query endpoint for UI testing that returns fake AI responses after a short delay.

**Request Body:**
```json
{
  "question": "What is the impact of climate change on biodiversity?"
}
```

**Response:**
```json
{
  "answer": "Based on the European research projects data, there are several notable...",
  "ai_provider": "openai",
  "demo": true,
  "processing_time": "3.42 seconds",
  "query": "What is the impact of climate change on biodiversity?"
}
```

## Usage Examples

### JavaScript (Fetch API)

```javascript
// Query the API with a natural language question
async function queryProjects(question, provider = null, version = "V3") {
  const payload = {
    question: question,
    max_results: 5,
    ai_version: version
  };
  if (provider) payload.ai_provider = provider;
  const response = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return await response.json();
}
```

### Python (Requests)

```python
import requests

def query_projects(question, provider=None, version="V3"):
    payload = {
        'question': question,
        'max_results': 5,
        'ai_version': version
    }
    if provider:
        payload['ai_provider'] = provider
    r = requests.post('http://localhost:8000/api/query', json=payload)
    if r.status_code == 200:
        return r.json()
    else:
        raise Exception(f"API error: {r.status_code} - {r.text}")
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Server-side error

Error responses include a detail message:

```json
{
  "error": "Error processing request",
  "details": "Invalid AI provider specified"
}
```

## Limitations

1. The API has rate limits based on the underlying AI provider's limitations.
2. Long or complex queries may take more time to process.
3. The quality of responses depends on the available data in the CORDIS database.

---

**V3 Changelog:**
- Uses CORDIS API for project retrieval (no Selenium required)
- Supports both OpenAI and Gemini
- 2-phase RAG logic: query extraction, retrieval, reranking, answer generation
- Switch between V2 and V3 logic using `ai_version` parameter
- Improved speed, reliability, and maintainability