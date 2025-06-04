# CORDIS Research Projects API Documentation

## Overview

This API provides a Retrieval-Augmented Generation (RAG) interface for querying European research projects from the CORDIS database. It supports natural language questions and can provide AI-generated responses based on retrieved project data.

The API supports multiple AI providers (currently OpenAI and Gemini) and can be configured to use specific models for each provider.

## Configuration

The API uses the following environment variables:

- `DEFAULT_AI_PROVIDER`: The default AI provider to use ("openai" or "gemini", defaults to "gemini")
- `OPENAI_API_KEY`: API key for OpenAI services
- `GEMINI_API_KEY`: API key for Google Gemini services
- `OPENAI_MODEL`: The model to use for OpenAI (default: "gpt-4-turbo")
- `GEMINI_MODEL`: The model to use for Gemini (default: "gemini-2.5-flash-preview-05-20")

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

Lists all available AI providers and their configured models.

**Response:**
```json
{
  "available_providers": {
    "openai": {
      "model": "gpt-4-turbo",
      "is_default": true
    },
    "gemini": {
      "model": "gemini-2.5-flash-preview-05-20",
      "is_default": false
    }
  },
  "default_provider": "openai"
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
  "ai_provider": "openai"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | string | Yes | Natural language question about European research projects |
| max_results | integer | No | Maximum number of projects to retrieve (default: 5) |
| ai_provider | string | No | AI provider to use ("openai" or "gemini"). If not specified, uses the default provider |

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
async function queryProjects(question, provider = null) {
  const payload = {
    question: question,
    max_results: 5
  };
  
  // Add provider if specified
  if (provider) {
    payload.ai_provider = provider;
  }
  
  const response = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return await response.json();
}

// Example usage
queryProjects("What European projects are related to quantum computing?", "gemini")
  .then(result => {
    console.log("AI Provider:", result.ai_provider);
    console.log("Model Used:", result.model_used);
    console.log("Answer:", result.answer);
  })
  .catch(error => {
    console.error("Error:", error);
  });
```

### Python (Requests)

```python
import requests

def query_projects(question, provider=None):
    """Query the API with a natural language question"""
    payload = {
        'question': question,
        'max_results': 5
    }
    
    # Add provider if specified
    if provider:
        payload['ai_provider'] = provider
    
    r = requests.post('http://localhost:8000/api/query', json=payload)
    
    if r.status_code == 200:
        return r.json()
    else:
        raise Exception(f"API error: {r.status_code} - {r.text}")

# Example usage
result = query_projects("What projects address climate change adaptation?", "openai")
print(f"AI Provider: {result['ai_provider']}")
print(f"Model Used: {result['model_used']}")
print(f"Answer: {result['answer']}")
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Server-side error

Error responses include a detail message:

```json
{
  "detail": "Error processing request: Invalid AI provider specified"
}
```

## Limitations

1. The API has rate limits based on the underlying AI provider's limitations.
2. Long or complex queries may take more time to process.
3. The quality of responses depends on the available data in the CORDIS database.