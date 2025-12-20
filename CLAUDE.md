# CLAUDE.md - MAPIT AI Project Conventions

## Project Overview

MAPIT (Mobilizing Advanced Partnerships for Digital Innovation and Transformation) is an EU Horizon Europe project that provides an intelligent RAG-LLM (Retrieval Augmented Generation with Large Language Models) search interface for querying EU research funding data, specifically the CORDIS database.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask application
docker-compose up --build

# Or run directly
cd src/gui && python app.py
```

## Project Structure

```
MAP-IT_SA/
├── src/                          # Main application source code
│   ├── gui/                      # Flask web interface
│   ├── etl/                      # Data extraction and loading
│   ├── retrieve/                 # Retrieval and RAG services
│   ├── devops/                   # Infrastructure and setup
│   └── main.py
├── app/                          # Backend API services
│   ├── api/                      # API endpoints
│   ├── core/                     # Core utilities
│   ├── models/                   # Data models
│   └── services/                 # Business logic services
├── data/                         # Data processing utilities
├── tests/                        # Unit and integration tests
├── docs/                         # Documentation
├── docs_tracked/                 # Version-controlled documentation
├── docker-compose.yml            # Docker configuration
└── requirements.txt              # Python dependencies
```

## Code Conventions

### Python Style

- **Python Version**: 3.12+
- **Style Guide**: Follow PEP 8
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions and classes

```python
def example_function(param1: str, param2: int) -> dict:
    """Brief description of function.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param2 is negative.
    """
    pass
```

### Naming Conventions

- **Files**: Use snake_case (e.g., `cordis_retriever.py`)
- **Classes**: Use PascalCase (e.g., `CORDISRetriever`)
- **Functions/Methods**: Use snake_case (e.g., `get_base_information`)
- **Constants**: Use UPPER_SNAKE_CASE (e.g., `MAX_TOKEN_LIMIT`)
- **Variables**: Use snake_case (e.g., `project_data`)

### Import Order

1. Standard library imports
2. Third-party library imports
3. Local application imports

Separate each group with a blank line.

### Error Handling

- Use specific exception types rather than generic `Exception`
- Always log errors with appropriate context
- Provide meaningful error messages to users
- Use try-except blocks around external API calls

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = external_api.call()
except ExternalAPIError as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    raise UserFriendlyError("Unable to complete request. Please try again.")
```

## Testing Conventions

- **Framework**: pytest (preferred) or unittest
- **Test File Naming**: `test_<module_name>.py`
- **Test Function Naming**: `test_<function_name>_<scenario>`
- **Location**: All tests in `tests/` directory
- **Coverage Target**: 80%+

```python
def test_load_projects_success():
    """Test successful project loading from CSV."""
    # Arrange
    loader = ProjectLoader()

    # Act
    result = loader.load("test_data.csv")

    # Assert
    assert len(result) > 0
    assert result[0].title is not None
```

## Configuration

### Environment Variables

Store all sensitive configuration in `.env` file (never commit to git):

- `MISTRAL_API_KEY`: Mistral AI API key (primary LLM)
- `OPENAI_API_KEY`: OpenAI API key (backup)
- `DGRAPH_HOST`: Dgraph database host
- `DGRAPH_PORT`: Dgraph database port

### Database

- **Primary**: Dgraph (graph database)
- **Schema**: Defined in `src/devops/CORDISProjectSchemaInit.py`

## AI/LLM Integration

### Primary Provider: Mistral AI

- Model: `mistral-large-latest`
- Max tokens: 131,072
- Used for: Answer generation from retrieved context

### Embedding Model

- Model: `sentence-transformers/all-mpnet-base-v2`
- Used for: Semantic similarity matching

### RAG Pipeline

1. User query received
2. Query encoded using sentence transformer
3. Context retrieved from multiple sources:
   - PDF documents (base information)
   - Dgraph database (project data)
   - Conversation history
4. Augmented prompt built with context
5. Prompt sent to Mistral LLM
6. Response returned to user

## Git Workflow

- **Main Branch**: `main`
- **Feature Branches**: `feature/<description>`
- **Fix Branches**: `fix/<description>`
- **Commit Messages**: Use conventional commits format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/retrieve/CORDISRetriever.py` | Core RAG engine with LLM integration |
| `src/etl/CORDISProjectReader.py` | Project CSV loading and parsing |
| `src/gui/app.py` | Flask web application |
| `src/etl/MAPITGraphBuilder.py` | Graph relationship building |
| `src/retrieve/topic_ids_and_titles.py` | Topic mappings (Horizon Europe) |

## Common Tasks

### Adding a New EU Program

1. Add topic mappings to `src/retrieve/topic_ids_and_titles.py`
2. Update ETL loader if data format differs
3. Add program-specific prompts if needed
4. Update documentation

### Adding a New Feature

1. Create feature branch
2. Implement with tests
3. Update relevant documentation
4. Submit pull request

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ProjectLoaderTest.py
```

## Troubleshooting

### Common Issues

1. **Dgraph Connection Error**: Ensure Dgraph is running and `DGRAPH_HOST`/`DGRAPH_PORT` are set correctly
2. **API Rate Limits**: Implement exponential backoff for external API calls
3. **Memory Issues**: Large embeddings may require GPU or chunked processing

## Resources

- [CORDIS Database](https://cordis.europa.eu/)
- [Dgraph Documentation](https://dgraph.io/docs/)
- [Mistral AI Documentation](https://docs.mistral.ai/)
- [Sentence Transformers](https://www.sbert.net/)
