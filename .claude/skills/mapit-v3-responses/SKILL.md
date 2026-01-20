# MAPIT V3 Response Formatting Skill

This skill documents V3 response formatting patterns, SSE event types, emoji conventions, and API enrichment triggers.

## Core Components

| Component | File | Purpose |
|-----------|------|---------|
| V3ResponseFormatter | `app/services/response/v3_response_formatter.py` | Post-processor for tool results |
| conversation_routes_v3 | `app/api/conversation_routes_v3.py` | SSE streaming endpoints |
| CallEnrichmentService | `app/services/call_enrichment_service.py` | On-demand API enrichment |

---

## Emoji Conventions

### Type Icons (Funding Call Action Types)

```python
TYPE_ICONS = {
    'RIA': '🔬',      # Research and Innovation Action
    'IA': '🚀',       # Innovation Action
    'CSA': '🤝',      # Coordination & Support Action
    'COFUND': '💱',   # Co-funded
    'ERC': '🎓',      # European Research Council
    'ERC-STG': '🎓',  # ERC Starting Grant
    'ERC-COG': '🎓',  # ERC Consolidator Grant
    'ERC-ADG': '🎓',  # ERC Advanced Grant
    'ERC-POC': '🎓',  # ERC Proof of Concept
    'MSCA': '👨‍🔬',    # Marie Skłodowska-Curie Actions
    'MSCA-PF': '👨‍🔬', # MSCA Postdoctoral Fellowship
    'MSCA-DN': '👨‍🔬', # MSCA Doctoral Network
    'LUMP-SUM': '📦', # Lump-sum funding
    'PCP': '🔧',      # Pre-Commercial Procurement
    'PPI': '🛒',      # Public Procurement of Innovative
    'default': '📄',  # Generic document
}
```

### Status Icons

```python
STATUS_ICONS = {
    'open': '🟢',     # Currently accepting applications
    'upcoming': '🟡', # Will open soon
    'closed': '🔴',   # No longer accepting
    'default': '📊',  # Unknown status
}
```

### Field Icons

```python
FIELD_ICONS = {
    'call_id': '📋',
    'programme': '🏛️',
    'deadline': '⏰',
    'budget': '💰',
    'summary': '📝',
    'link': '🔗',
    'project_id': '🔢',
    'duration': '📅',
    'coordinator': '🏢',
    'publications': '📚',
    'deliverables': '📦',
    'impact': '🎯',
}
```

### Valid Action Types (for icon assignment)

```python
VALID_ACTION_TYPES = {
    'RIA', 'IA', 'CSA', 'COFUND',
    'ERC', 'ERC-STG', 'ERC-COG', 'ERC-ADG', 'ERC-POC',
    'MSCA', 'MSCA-PF', 'MSCA-DN', 'MSCA-SE', 'MSCA-COFUND',
    'LUMP-SUM', 'PCP', 'PPI'
}

# Only show type icon if it's a valid type (filters out numeric IDs)
call_type_upper = call_type.upper() if call_type else ''
is_valid_type = call_type_upper in VALID_ACTION_TYPES
```

---

## Call Formatting Structure

### Single Call Format

```markdown
**{index}. {title}**
📋 **Call ID:** {call_id}
🔬 **Type:** {call_type}
🟢 **Status:** {status}
⏰ **Deadline:** {formatted_deadline}
🏛️ **Programme:** {cluster_or_programme}
💰 **Budget:** {formatted_budget}

📝 **Summary:** {concise_summary}

🔗 **Apply:** {url}

---
```

### Field Extraction (with fallbacks)

```python
def _extract_call_fields(call: Dict) -> Dict:
    """Extract fields with fallback handling."""
    return {
        'title': call.get('title') or 'Untitled Call',
        'call_id': (call.get('call_id') or call.get('topic_code')
                   or call.get('topic_id') or ''),
        'call_type': call.get('type') or call.get('action_type') or '',
        'status': (call.get('status') or 'open').lower(),
        'deadline': (call.get('deadline') or call.get('application_deadline') or ''),
        'cluster': (call.get('cluster') or call.get('programme')
                   or call.get('work_programme') or ''),
        'budget': call.get('budget') or call.get('estimated_budget') or '',
        'url': call.get('url') or call.get('portal_url') or '',
    }
```

### Summary Extraction Priority

1. `description` field (if clean and ≥50 chars)
2. `expected_outcome` (usually structured)
3. `scope` (as fallback)
4. `objective` (last resort)

```python
def _extract_summary(call: Dict) -> str:
    """Extract concise summary from call data."""
    # Priority order
    for field in ['description', 'expected_outcome', 'scope', 'objective']:
        content = call.get(field, '')
        if content and len(content) >= 50:
            return _clean_summary(content)
    return "See official portal for full details."
```

### Summary Cleaning

```python
def _clean_summary(text: str) -> str:
    """Clean and truncate summary text."""
    import re

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')

    # Remove common noise prefixes
    noise_prefixes = ['Expected Outcome:', 'Scope:', 'Description:']
    for prefix in noise_prefixes:
        text = text.replace(prefix, '')

    # Normalize whitespace
    text = ' '.join(text.split())

    # Truncate at sentence boundary (~250 chars)
    if len(text) > 250:
        # Find last sentence end before limit
        truncated = text[:250]
        last_period = truncated.rfind('.')
        if last_period > 150:
            return truncated[:last_period + 1]
        return truncated + '...'

    return text
```

### Budget Formatting

```python
def _format_budget(budget: Any) -> str:
    """Format budget for display."""
    if isinstance(budget, (int, float)):
        if budget >= 1_000_000:
            return f"EUR {budget/1_000_000:.2f} million"
        elif budget >= 1_000:
            return f"EUR {budget/1_000:.0f}K"
        else:
            return f"EUR {budget:,.0f}"

    # String handling - ensure EUR prefix
    if isinstance(budget, str):
        if not budget.upper().startswith('EUR'):
            return f"EUR {budget}"
        return budget

    return "See call documentation"
```

### Deadline Formatting

```python
def _format_deadline(deadline: Any) -> str:
    """Format deadline for display."""
    from datetime import datetime

    if isinstance(deadline, datetime):
        return deadline.strftime("%d %b %Y")

    if isinstance(deadline, str):
        # Try ISO formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ']:
            try:
                dt = datetime.strptime(deadline[:19], fmt[:len(deadline)])
                return dt.strftime("%d %b %Y")
            except ValueError:
                continue

    return "Check official portal for deadline"
```

### URL Generation

```python
def _get_apply_url(call: Dict) -> str:
    """Generate apply URL."""
    # Use provided URL if available
    url = call.get('url') or call.get('portal_url')
    if url:
        return url

    # Generate for Horizon Europe calls
    call_id = call.get('call_id') or call.get('topic_code')
    if call_id and call_id.startswith('HORIZON'):
        return f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}"

    return ""
```

---

## Project Formatting Structure

### Single Project Format

```markdown
**{index}. {acronym}: {title}**
🔢 **Project ID:** {id}
🏛️ **Programme:** {programme}
🟢 **Status:** {status}
📅 **Duration:** {start_date} → {end_date}
💰 **EU Contribution:** {formatted_contribution}
🏢 **Coordinator:** {coordinator}

**Objective:** {objective_summary}

📚 **Key Publications:** (max 3)
  • {pub_title} - *{authors}* ({journal}) [DOI](url)

📦 **Key Deliverables:** (max 3)
  • {deliv_title} ({type}) [View](url)

📊 **Impact:** {publications_count} publications, {deliverables_count} deliverables

🔗 **Details:** https://cordis.europa.eu/project/id/{project_id}

---
```

### Project Status Icons

```python
def _get_project_status_icon(status: str) -> str:
    status_lower = (status or '').lower()
    if status_lower in ['ongoing', 'active', 'signed']:
        return '🟢'
    elif status_lower in ['closed', 'completed', 'terminated']:
        return '✅'
    return '📊'
```

---

## SSE Event Types

### Event Flow

```
1. status: "processing"       → Initial request received
2. conversation_name          → Generated name (first message only)
3. status: "context_loaded"   → History retrieved
4. status: "agent_starting"   → Agent beginning
5. agent_thinking             → Agent reasoning (per iteration)
6. tool_call                  → Before tool execution
7. tool_result                → After tool execution
8. status: "synthesizing"     → Converting to response
9. status: "streaming_response" → Beginning to stream
10. token                     → Response text chunks
11. complete                  → Final metadata
12. error                     → If exception occurs
```

### Event Structures

#### Status Event
```json
{
    "type": "status",
    "stage": "processing|context_loaded|agent_starting|synthesizing|streaming_response",
    "message": "Processing your query..."
}
```

#### Agent Thinking Event
```json
{
    "type": "agent_thinking",
    "stage": "reasoning",
    "iteration": 1,
    "thought": "I need to search for funding calls about hydrogen",
    "action": "call_tools"
}
```

#### Tool Call Event
```json
{
    "type": "tool_call",
    "stage": "executing_tool",
    "tool_name": "search_funding_calls",
    "parameters": {"keywords": "hydrogen", "status": "open"},
    "reasoning": "User asked about hydrogen funding opportunities"
}
```

#### Tool Result Event
```json
{
    "type": "tool_result",
    "stage": "tool_complete",
    "tool_name": "search_funding_calls",
    "success": true,
    "result_count": 15,
    "result_summary": "Found 15 open calls for hydrogen research",
    "execution_time_ms": 234
}
```

#### Token Event
```json
{
    "type": "token",
    "content": "I found **15 funding opportunities**"
}
```

#### Complete Event
```json
{
    "type": "complete",
    "metadata": {
        "architecture": "simplified_v3",
        "confidence": 0.85,
        "tools_used": ["search_funding_calls"],
        "iterations": 2,
        "processing_time_ms": 2500,
        "reasoning_steps": [...]
    }
}
```

#### Error Event
```json
{
    "type": "error",
    "error": "Database connection failed",
    "stage": "error"
}
```

### SSE Wire Format

```python
import json

def format_sse_event(event: Dict) -> str:
    """Format event for SSE transmission."""
    return f"data: {json.dumps(event)}\n\n"

# Valid event types
VALID_EVENT_TYPES = [
    'status', 'progress', 'conversation_name', 'agent_thinking',
    'tool_call', 'tool_result', 'token', 'complete', 'error'
]
```

---

## API Enrichment Triggers

### When to Enrich

```python
def _needs_enrichment(call: Dict) -> bool:
    """Determine if call needs API enrichment."""
    # Missing or very short scope
    scope = call.get('scope') or call.get('description') or ''
    if len(scope) < 50:
        return True

    # Missing deadline (CRITICAL)
    if not call.get('deadline'):
        return True

    # Missing status
    if not call.get('status'):
        return True

    return False
```

### Completeness Check

```python
def _is_complete(call: Dict) -> bool:
    """Check if call data is complete."""
    # Required fields
    for field in ['scope', 'title']:
        value = call.get(field, '')
        if not value or len(str(value)) < 20:
            return False

    # Deadline is REQUIRED
    if not call.get('deadline'):
        return False

    return True
```

### Enrichment Service Flow

```
1. Check local database first (funding_calls table)
2. If incomplete → Fetch from EU Portal API
3. Merge API data with local data
4. Cache enriched data locally
5. Return enriched result
6. Fallback: Return local data if API fails
```

### API Endpoints

```python
EU_PORTAL_SEARCH = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_PORTAL_TOPIC = "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"
```

---

## Result Deduplication

### Merging Multiple Tool Results

```python
def format_from_tool_results(tool_results: Dict[str, Any], query: str = "") -> Optional[str]:
    """Merge and format results from multiple tools."""
    all_calls = []
    all_projects = []
    seen_call_ids = set()
    seen_project_ids = set()

    for tool_name, result in tool_results.items():
        if not isinstance(result, dict):
            continue

        # Deduplicate calls
        if 'calls' in result and isinstance(result['calls'], list):
            for call in result['calls']:
                call_id = call.get('call_id') or call.get('topic_code') or ''
                if call_id and call_id not in seen_call_ids:
                    seen_call_ids.add(call_id)
                    all_calls.append(call)

        # Deduplicate projects
        if 'projects' in result and isinstance(result['projects'], list):
            for project in result['projects']:
                project_id = str(project.get('id') or project.get('project_id') or '')
                if project_id and project_id not in seen_project_ids:
                    seen_project_ids.add(project_id)
                    all_projects.append(project)

    # Format (prefer calls over projects)
    if all_calls:
        return format_funding_calls(all_calls, query)
    if all_projects:
        return format_projects(all_projects, query)
    return None
```

---

## Response Footer (Application Guidance)

```python
APPLICATION_FOOTER = """
---

💡 **How to Apply:**
• **Register** on the EU Funding & Tenders Portal if you haven't already
• **Check eligibility** criteria carefully for each call
• **Prepare partnerships** - many calls require consortium applications
• **Review evaluation criteria** and weightings in the call documentation
• **Submit well before** the deadline - the portal can be busy near deadlines

📚 **Useful Resources:**
• [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• [How to Participate Guide](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)

🎯 **Next Steps:**
• Click on the 'Apply' links above for full call details
• Download the call documentation and work programme
• Start building your consortium if partnerships are required
"""
```

---

## Context Window Management

```python
# Token limits for context management
CONTEXT_LIMITS = {
    'max_context_chars': 100000,      # ~25k tokens
    'max_tool_result_chars': 5000,    # Per result
    'max_observation_chars': 1500,    # Per reasoning step
    'max_document_chars': 600,        # Per document in synthesis
    'max_documents_per_result': 10,
    'max_calls_per_result': 15,
    'max_projects_per_result': 10,
    'reserved_for_response': 4000,
}
```

---

## Complete Formatting Example

### Input (Tool Result)

```python
tool_results = {
    'search_funding_calls': {
        'success': True,
        'calls': [
            {
                'call_id': 'HORIZON-CL5-2026-D3-02-01',
                'title': 'Advanced biofuels and renewable fuels',
                'type': 'RIA',
                'status': 'open',
                'deadline': '2026-02-05',
                'cluster': 'Cluster 5 - Climate, Energy and Mobility',
                'budget': 20000000,
                'description': 'This topic focuses on advanced biofuels...'
            }
        ]
    }
}
```

### Output (Formatted Markdown)

```markdown
I found **1 funding opportunity** for your query:

**1. Advanced biofuels and renewable fuels**
📋 **Call ID:** HORIZON-CL5-2026-D3-02-01
🔬 **Type:** RIA
🟢 **Status:** Open
⏰ **Deadline:** 05 Feb 2026
🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
💰 **Budget:** EUR 20.00 million

📝 **Summary:** This topic focuses on advanced biofuels...

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-CL5-2026-D3-02-01

---

💡 **How to Apply:**
...
```

---

## Streaming Implementation Pattern

```python
async def stream_response(conversation_id: str, message: str):
    """Stream V3 response with SSE events."""
    import json

    # Initial status
    yield f"data: {json.dumps({'type': 'status', 'stage': 'processing'})}\n\n"

    # Process with agent
    async for event in agent.process_query_streaming(message):
        event_type = event.get('type', '')

        if event_type in VALID_EVENT_TYPES:
            yield f"data: {json.dumps(event)}\n\n"

        # Add small delay for smooth streaming
        if event_type == 'token':
            await asyncio.sleep(0.01)  # 10ms delay

    # Final complete event
    yield f"data: {json.dumps({'type': 'complete', 'metadata': {...}})}\n\n"
```
