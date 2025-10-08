# V2 Conversational AI System - Testing Guide

## Overview

This document describes the testing capabilities for the V2 conversational AI wrapper system. The system has been analyzed and comprehensive test scripts have been created to verify all major functionality.

## System Capabilities

The V2 conversational AI system supports the following major categories of questions:

### 1. **Basic Conversation**
- **Purpose**: Greeting and general conversation
- **Example**: "Hello, how are you?"
- **Expected Response**: Conversational AI response without tool execution
- **Intent Type**: `conversational`

### 2. **Horizon Europe Information**
- **Purpose**: General knowledge about EU research programmes
- **Example**: "What is Horizon Europe and what's its budget?"
- **Expected Response**: Detailed information about the programme using enhanced fallback responses
- **Intent Type**: `conversational`

### 3. **Funding Call Search**
- **Purpose**: Find current funding opportunities
- **Example**: "Find open calls for artificial intelligence research"
- **Expected Response**: Tool-based search results from EU Portal
- **Intent Type**: `search_calls`

### 4. **Project Search (CORDIS)**
- **Purpose**: Search for completed EU research projects
- **Example**: "Search for completed projects about renewable energy"
- **Expected Response**: Tool-based search results from CORDIS database
- **Intent Type**: `search_projects`

### 5. **Call Document Specific Queries**
- **Purpose**: Questions about specific funding calls
- **Example**: "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?"
- **Expected Response**: AI response using call-specific documents
- **Intent Type**: `call_document`

### 6. **Country Eligibility**
- **Purpose**: Questions about country participation
- **Example**: "Can researchers from Switzerland apply?"
- **Expected Response**: Conversational AI with country-specific information
- **Intent Type**: `conversational`

### 7. **Application Guidance**
- **Purpose**: Help with application processes
- **Example**: "How do I apply for a Horizon Europe grant?"
- **Expected Response**: Detailed application guidance
- **Intent Type**: `conversational`

### 8. **Budget & Funding Information**
- **Purpose**: Financial information and rates
- **Example**: "What are typical funding rates for different projects?"
- **Expected Response**: Budget and funding information
- **Intent Type**: `conversational`

### 9. **Technology-Specific Queries**
- **Purpose**: Funding for specific technologies
- **Example**: "What funding exists for quantum computing?"
- **Expected Response**: Tool-based search for technology-specific calls
- **Intent Type**: `search_calls`

### 10. **Climate & Environment**
- **Purpose**: Environmental research queries
- **Example**: "Show me climate change adaptation projects"
- **Expected Response**: Tool-based search for environmental projects
- **Intent Type**: `search_projects`

### 11. **Health Research**
- **Purpose**: Health research information
- **Example**: "What health areas are prioritized?"
- **Expected Response**: Health research priorities and guidance
- **Intent Type**: `conversational`

### 12. **Partnership & Collaboration**
- **Purpose**: Help finding research partners
- **Example**: "How can I find research partners in Germany?"
- **Expected Response**: Partnership guidance and collaboration tips
- **Intent Type**: `conversational`

### 13. **Success Stories**
- **Purpose**: Examples of successful projects
- **Example**: "Show me successful AI projects that received funding"
- **Expected Response**: Tool-based search for successful projects
- **Intent Type**: `search_projects`

### 14. **Deadline Information**
- **Purpose**: Information about upcoming deadlines
- **Example**: "What are the upcoming deadlines for energy calls?"
- **Expected Response**: Tool-based search for deadlines
- **Intent Type**: `search_calls`

### 15. **Complex Multi-part Queries**
- **Purpose**: Questions with multiple components
- **Example**: "I'm a researcher from Spain interested in renewable energy funding"
- **Expected Response**: Comprehensive response addressing all components
- **Intent Type**: `search_calls`

## Testing Scripts

Three testing scripts have been created:

### 1. `test_basic_functionality.py`
**Purpose**: Quick health check and basic functionality test
**Usage**: `python3 test_basic_functionality.py`
**Tests**: Server health, conversation clearing, simple question
**Time**: ~30 seconds

### 2. `test_system_quick.py`
**Purpose**: Tests key categories (5 representative questions)
**Usage**: `python3 test_system_quick.py`
**Tests**: One question from each major capability group
**Time**: ~2-3 minutes

### 3. `test_system_simple.py`
**Purpose**: Comprehensive test of all categories
**Usage**: `python3 test_system_simple.py`
**Tests**: All 15 question categories
**Time**: ~10-15 minutes

### 4. `test_system_capabilities.py` (requires aiohttp)
**Purpose**: Full-featured streaming test with detailed analysis
**Usage**: `python3 test_system_capabilities.py`
**Tests**: All categories with streaming endpoint
**Time**: ~10-15 minutes

## Usage Instructions

### Quick Verification (Recommended for regular use)
```bash
python3 test_basic_functionality.py
```

### Comprehensive Testing
```bash
python3 test_system_quick.py
```

### Full System Testing
```bash
python3 test_system_simple.py
```

## Expected Results

When running the tests, you should see:

### Successful Indicators:
- ✅ Server health check passes
- ✅ Questions return responses
- ✅ Tool-based queries execute tools (for searches)
- ✅ Conversational queries provide detailed responses
- ✅ Response times are reasonable (<30 seconds per request)

### Response Types:
- **Tool-based responses**: Should show `tools_executed: true` and include search results
- **Conversational responses**: Should show `tools_executed: false` and include detailed text
- **Call-specific responses**: Should use call documents for answering

### Performance Expectations:
- **Greeting/Basic questions**: <5 seconds
- **Tool-based searches**: 5-15 seconds (depending on external APIs)
- **Complex queries**: 10-30 seconds

## Troubleshooting

### Common Issues:

1. **Server not responding**
   - Check if server is running: `curl http://localhost:8000/api/v2/conversation/health`
   - Start the server if needed

2. **Slow responses**
   - Normal for tool-based queries (depends on external APIs)
   - Check network connectivity
   - Monitor AI provider API status

3. **Tests timing out**
   - Use `test_basic_functionality.py` for quick verification
   - Increase timeout values in scripts if needed

4. **Unexpected responses**
   - Check AI provider configuration
   - Verify external API keys are valid
   - Review system logs for errors

## Integration into Development Workflow

### Before Making Changes:
1. Run `test_basic_functionality.py` to ensure system is working
2. Document expected behavior

### After Making Changes:
1. Run `test_system_quick.py` to verify key functionality
2. Run `test_basic_functionality.py` for quick verification
3. Review test results for any regressions

### For Major Updates:
1. Run full test suite with `test_system_simple.py`
2. Compare results with previous tests
3. Document any changes in behavior or performance

## Technical Notes

### Endpoints Tested:
- **Health Check**: `/api/v2/conversation/health`
- **Message**: `/api/v2/conversation/{conversation_id}/message`
- **Memory Management**: `/api/v2/conversation/{conversation_id}/memory`

### AI Intent Categories:
The system uses AI-only intent analysis to categorize questions into:
- `conversational`: General knowledge and guidance
- `search_calls`: Funding opportunity searches
- `search_projects`: Past project searches
- `call_document`: Specific call questions

### Response Generation:
- **Tool-based**: Uses external APIs (EU Portal, CORDIS)
- **Conversational**: Uses enhanced fallback responses with detailed knowledge
- **Call-specific**: Uses call document database with AI interpretation

## Conclusion

The V2 conversational AI system provides comprehensive coverage of European research funding queries through intelligent intent detection and appropriate response generation. The testing scripts ensure all major capabilities are functioning correctly and provide quick verification methods for ongoing development and maintenance.