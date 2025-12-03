# Horizon Europe AI Assistant - Question Categories & Capabilities

## Overview
This document categorizes all types of questions that the enhanced RAG system can answer, providing a comprehensive reference for testing and utilizing the AI tool's full capabilities. The system leverages comprehensive Horizon Europe documentation, including Work Programmes, Call Texts, Programme Guides, and FAQs, ingested into a vector database for semantic search.

## Question Categories

### 1. Call-Specific Questions
**Description**: Questions targeting specific Horizon Europe call or topic identifiers. These queries leverage the comprehensive call documentation for precise, detailed answers about specific funding opportunities.

**Examples**:
- "What are the eligibility criteria for HORIZON-CL4-2024-DATA-01-01?"
- "Tell me about the budget and deadlines for HORIZON-CL5-2024-CLIMATE-01"
- "What are the evaluation criteria for HORIZON-HLTH-2024-DISEASE-03-02?"
- "Explain the submission process for HORIZON-EIC-2024-ACCELERATOR-01"
- "What are the specific requirements for HORIZON-ERC-2024-SYG-01?"

**Data Sources**: Horizon Europe Call Texts, Work Programme sections, Topic Descriptions
**Handled By**: CallSpecificRAG service with intent detection and vector search

### 2. Cluster-Specific Questions
**Description**: Questions about specific Horizon Europe clusters or programmes. The system identifies cluster keywords and provides relevant call information.

**Examples**:
- "What health cluster calls are available for 2024?"
- "Show me digital transformation topics in Horizon Europe"
- "What climate and energy calls are open now?"
- "Tell me about the European Innovation Council (EIC) opportunities"
- "What are the ERC grants available for frontier research?"

**Data Sources**: Work Programme cluster sections, Programme Guides
**Handled By**: Enhanced intent detection with cluster keyword matching

### 3. General Funding Opportunity Questions
**Description**: Broad queries about open calls and funding opportunities. Uses EU Funding & Tenders Portal API integration combined with document context.

**Examples**:
- "What are some open calls for AI research?"
- "Find funding opportunities for renewable energy projects"
- "Are there any grants for sustainable agriculture?"
- "What calls are available for cybersecurity research?"
- "Show me open proposals for quantum technology"

**Data Sources**: EU Funding & Tenders Portal API, Horizon Europe documentation
**Handled By**: CORDIS RAG with API integration and document enhancement

### 4. General Eligibility & Programme Questions
**Description**: Questions about Horizon Europe programme rules, eligibility criteria, and general procedures. Leverages the comprehensive document database.

**Examples**:
- "What are the eligibility criteria for Horizon Europe?"
- "How do I form a consortium for Horizon Europe projects?"
- "What is the evaluation process for Horizon Europe proposals?"
- "What are the different funding rates in Horizon Europe?"
- "Explain the difference between RIA, IA, and CSA actions"

**Data Sources**: Horizon Europe Programme Guide, General Annexes, FAQs
**Handled By**: Enhanced RAG service with vector search

### 5. Project Search Questions
**Description**: Queries about existing or past research projects funded by Horizon Europe. Uses CORDIS database integration.

**Examples**:
- "Show me successful AI healthcare projects funded by EU"
- "What renewable energy projects have been funded recently?"
- "Find me projects about digital transformation in manufacturing"
- "What climate change adaptation projects exist?"
- "Show me ERC-funded projects in quantum physics"

**Data Sources**: CORDIS project database, Project summaries
**Handled By**: CORDIS RAG service with project search capabilities

### 6. Mixed Intent & Complex Queries
**Description**: Complex questions that combine multiple aspects, such as call details with project examples or procedures with eligibility.

**Examples**:
- "How do I apply for HORIZON-CL4-2024-DATA-01 and what are successful examples?"
- "What are the deadlines for health calls and what projects have been funded in this area?"
- "Explain the evaluation criteria for EIC Accelerator and show me past successful projects"
- "What are the eligibility requirements for digital calls and how do I submit a proposal?"

**Data Sources**: Multiple sources combined - calls, projects, programme docs
**Handled By**: Enhanced RAG with intelligent routing and combined search

## Testing Methods

### 1. Script-Based Testing
- **Call-Specific Testing**: Run `python scripts/test_call_specific_rag.py`
- **General RAG Testing**: Run `python scripts/test_enhanced_rag.py` 
- **Comprehensive Verification**: Run `python scripts/verify_system.py`

### 2. API Endpoints
- **Enhanced RAG**: POST to `/api/enhanced-rag/answer` with JSON payload: `{"question": "Your question here"}`
- **Direct Service Testing**: Use the `EnhancedRAGService` or `CallSpecificRAG` classes directly in Python

### 3. Example Test Queries by Category
Each test script includes example queries for all categories. Modify the scripts to add new test cases or use the API for interactive testing.

## Data Sources Overview
- **Horizon Europe Work Programme 2023-2024**: Comprehensive call descriptions and budgets
- **Horizon Europe Programme Guide**: Eligibility rules and procedures
- **Call Texts and Topic Descriptions**: Detailed call-specific information
- **FAQs and Annexes**: Additional programme details
- **CORDIS Database**: Existing project information
- **EU Funding & Tenders Portal**: Real-time call information

## System Capabilities Summary
- ✅ Intent detection and routing to appropriate handlers
- ✅ Semantic search across comprehensive documentation
- ✅ Call-specific query handling with precise answers
- ✅ Project search and information retrieval
- ✅ Real-time funding opportunity search
- ✅ Combined query processing across multiple data sources
- ✅ Confidence scoring and source referencing

## Version Information
- **RAG System Version**: V9 with enhanced call-specific capabilities
- **Last Updated**: September 2024
- **Documentation Coverage**: Full Horizon Europe 2021-2027 programme

This document serves as a living reference for all question types the system can handle. Update it as new capabilities are added or new document types are ingested.