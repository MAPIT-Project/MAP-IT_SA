# MAPIT Tools Development Skill

A Claude Code skill for developing tools in the MAPIT AI agentic system.

## Overview

This skill provides comprehensive patterns, templates, and guidelines for creating and modifying tools in the MAPIT AI system. It covers:

- Tool file structure and patterns
- Hybrid Graph+SQL architecture
- RRF (Reciprocal Rank Fusion) for result merging
- Tool registration in ToolAwareAgent
- Error handling and graceful degradation
- Testing patterns

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill documentation with all patterns |
| `templates/tool_template.py` | Copy-paste template for new tools |

## Quick Start

### Creating a New Tool

1. **Copy the template**:
   ```bash
   cp .claude/skills/mapit-tools/templates/tool_template.py app/services/tools/my_tool.py
   ```

2. **Replace placeholders**:
   - `{ToolClassName}` → Your class name (e.g., `MyNewTool`)
   - `{tool_name}` → Tool identifier (e.g., `my_new_tool`)
   - `{main_method_name}` → Main method (e.g., `find_something`)
   - `{TOOL_NAME}` → Display name in docstring
   - `{TOOL_DESCRIPTION}` → Brief description

3. **Export in `__init__.py`**:
   ```python
   from .my_tool import MyNewTool, my_new_tool_execute
   ```

4. **Register in ToolAwareAgent** (see SKILL.md for details)

## Key Patterns

### Hybrid Architecture

Most tools use a hybrid Graph+SQL architecture:
- **Graph (Neo4j)**: Relationship traversal, pre-aggregated stats, pattern discovery
- **SQL (PostgreSQL)**: Keyword filtering, detailed data, full-text search
- **Parallel execution**: Both queries run simultaneously
- **RRF fusion**: Results merged using Reciprocal Rank Fusion

### Parameter Fallbacks

LLMs use inconsistent parameter names, so always handle fallbacks:

```python
cluster = (
    params.get('cluster') or
    params.get('cluster_code') or
    params.get('pillar')
)
```

### Graceful Degradation

Services may be unavailable; tools should work with SQL-only:

```python
self._graph_service = None
try:
    from ..data_intelligence.graph_service import GraphSearchService
    self._graph_service = GraphSearchService()
except Exception:
    logger.warning("Graph unavailable, using SQL-only mode")
```

## Usage in Claude Code

When Claude Code encounters a task involving MAPIT tools, it should:

1. Read `SKILL.md` for patterns
2. Follow the step-by-step integration guide
3. Use the template as a starting point
4. Run the checklist before committing

## Tool Categories

| Category | Use For |
|----------|---------|
| `STATISTICS` | Metrics, success rates, aggregations |
| `DOCUMENTS` | Vector search, text retrieval |
| `CALLS` | Funding call search |
| `PROJECTS` | CORDIS project search |
| `COMPARISON` | Cross-reference tools |
| `PROPOSAL` | Budget, timeline, proposal writing |

See SKILL.md for complete documentation.
