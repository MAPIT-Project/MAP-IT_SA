# CORDIS Research Projects RAG API

A Retrieval-Augmented Generation (RAG) system for querying European research projects from the CORDIS database.

## Overview

This project implements a specialized RAG system focused on European research projects. It allows users to ask natural language questions about EU-funded research and receive comprehensive answers based on data retrieved from the CORDIS database.

## Key Features

- Natural language query processing using GPT-4
- Automatic extraction of search terms from user questions
- Intelligent search of the CORDIS database
- Structured data extraction from XML project documentation
- Answer generation based on retrieved project information
- FastAPI interface for easy integration
- Demo endpoint for UI testing without making actual CORDIS queries

## System Architecture

The system follows this process flow:

1. User submits a question via the API
2. The system prompts GPT-4 to analyze the question and extract search terms
3. The extracted queries are used to search the CORDIS database
4. Top results are fetched and converted to structured data
5. GPT-4 is used again to generate a comprehensive answer using the retrieved information

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- Chrome WebDriver for Selenium

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/cordis-rag-api.git
   cd cordis-rag-api
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Running the API

Start the FastAPI server:

```
python fast_api.py
```

The API will be available at `http://localhost:8000`.

Interactive API documentation is available at `http://localhost:8000/docs`.

## API Endpoints

- `GET /`: Health check endpoint
- `GET /api/health`: Detailed health check endpoint
- `POST /api/query`: Main endpoint for querying European research projects
- `POST /api/demo`: Demo endpoint that returns simulated responses (for UI testing)

### Query Example

Request:
```json
{
  "question": "What are some recent AI projects in healthcare with German participants?",
  "max_results": 5
}
```

Response:
```json
{
  "answer": "Based on the retrieved information, there are several recent AI projects in healthcare with German participants...",
  "projects": null
}
```

### Demo Endpoint

The `/api/demo` endpoint is specifically designed for UI testing and development purposes. It returns simulated responses without making actual CORDIS queries or using your OpenAI API quota.

Request:
```json
{
  "question": "What are recent AI projects in healthcare?"
}
```

Response:
```json
{
  "answer": "Based on the European research projects data, there are several notable AI initiatives in healthcare...",
  "demo": true,
  "processing_time": "3.45 seconds",
  "query": "What are recent AI projects in healthcare?"
}
```

## Usage Examples

### Python Client

```python
import requests

url = "http://localhost:8000/api/query"
payload = {
    "question": "What are the top EU-funded quantum computing projects in the last 3 years?"
}
response = requests.post(url, json=payload)
print(response.json()["answer"])
```

### JavaScript Fetch (for UI integration)

```javascript
// Using the real query endpoint
fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: "What are recent AI projects in healthcare?",
  }),
})
.then(response => response.json())
.then(data => {
  console.log(data.answer);
  // Update UI with the response
});

// Using the demo endpoint for testing
fetch('http://localhost:8000/api/demo', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: "What are recent AI projects in healthcare?",
  }),
})
.then(response => response.json())
.then(data => {
  console.log(data.answer);
  // Update UI with the response
});
```

### cURL

```bash
curl -X 'POST' \
  'http://localhost:8000/api/query' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "Which countries are leading in renewable energy research projects?"
}'
```

## Development

### Project Structure

- `cordisBased_RAG_function.py`: Core RAG system implementation
- `fast_api.py`: FastAPI implementation for RESTful access

## Future Improvements

- Add caching to improve performance for repeated queries
- Implement more advanced filtering options
- Add support for returning structured project data
- Create a web interface for easier access
- Add authentication for API access control

## License

This project is licensed under the MIT License - see the LICENSE file for details.

