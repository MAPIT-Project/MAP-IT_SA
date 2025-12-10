"""
Speculative Tool Executor

Starts executing likely-needed tools speculatively while the LLM is
still reasoning. This reduces latency for complex queries by overlapping
I/O operations with reasoning.

Key Features:
- Pattern-based speculation (identifies likely tools from query keywords)
- Non-blocking execution with asyncio tasks
- Automatic cancellation of unused speculative results
- Configurable timeout for speculative results
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)


class SpeculativeExecutor:
    """Execute likely tool calls speculatively to reduce latency."""

    # Common query patterns mapped to likely tools
    # Format: (keywords tuple) -> [list of tool names]
    SPECULATION_PATTERNS = {
        # Funding calls queries
        ('funding', 'calls', 'open', 'deadline', 'apply'): ['search_funding_calls'],
        ('hydrogen', 'energy', 'renewable', 'solar', 'wind', 'battery', 'green'): ['search_funding_calls', 'search_documents'],
        ('ai', 'artificial intelligence', 'machine learning', 'digital'): ['search_funding_calls', 'search_documents'],
        ('health', 'cancer', 'disease', 'medical', 'clinical'): ['search_funding_calls', 'search_documents'],
        ('quantum', 'computing', 'cybersecurity'): ['search_funding_calls', 'search_documents'],

        # Project queries
        ('projects', 'funded', 'cordis', 'similar'): ['search_projects'],
        ('find projects', 'show projects', 'projects about'): ['search_projects'],

        # Budget/consortium queries
        ('budget', 'cost', 'typical', 'average', 'how much'): ['get_budget_benchmark'],
        ('consortium', 'partners', 'composition', 'team'): ['get_consortium_patterns'],
        ('partner', 'experienced', 'find partner', 'collaborator'): ['find_experienced_partners'],

        # Statistics queries
        ('statistics', 'success rate', 'funding rate', 'how many'): ['get_programme_statistics'],
        ('country', 'germany', 'france', 'spain', 'italy', 'participation'): ['get_country_statistics'],

        # Country eligibility queries - use get_country_statistics for clear YES/NO answers
        ('can switzerland', 'can uk', 'can israel', 'can norway', 'switzerland participate', 'uk participate'): ['get_country_statistics'],
        ('is switzerland', 'is uk', 'is israel', 'is norway', 'switzerland eligible', 'uk eligible'): ['get_country_statistics'],

        # Comparison queries
        ('compare', 'difference', 'vs', 'versus', 'between'): ['compare_programmes'],

        # Document/eligibility queries (for general rules, not country-specific)
        ('consortium eligibility', 'eligibility requirement', 'eligibility rule', 'who can apply'): ['search_documents'],
        ('page limit', 'pages', 'format', 'template'): ['search_documents'],

        # History/trends
        ('history', 'trend', 'over time', 'years', 'timeline'): ['analyze_call_history'],
    }

    def __init__(self, tool_executor: Callable[[str, Dict], Awaitable[Any]]):
        """
        Initialize speculative executor.

        Args:
            tool_executor: Async function that executes a single tool
        """
        self.tool_executor = tool_executor
        self.speculation_cache: Dict[str, asyncio.Task] = {}
        self.speculation_results: Dict[str, Any] = {}
        self.max_speculative_calls = 3

    def identify_likely_tools(self, query: str) -> List[str]:
        """
        Identify tools that are likely needed for this query.

        Returns list of tool names (max 3) that might be needed.
        """
        query_lower = query.lower()
        likely_tools: Set[str] = set()

        for keywords, tools in self.SPECULATION_PATTERNS.items():
            # Check if any keyword matches
            if any(kw in query_lower for kw in keywords):
                likely_tools.update(tools)

        return list(likely_tools)[:self.max_speculative_calls]

    def _extract_keywords_from_query(self, query: str) -> str:
        """Extract key search terms from query."""
        # Remove common words and keep key terms
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'i', 'me',
            'my', 'we', 'our', 'you', 'your', 'what', 'which', 'who',
            'how', 'when', 'where', 'why', 'for', 'to', 'of', 'in', 'on',
            'at', 'by', 'with', 'about', 'find', 'show', 'get', 'tell',
            'give', 'need', 'want', 'looking', 'search', 'help'
        }

        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return ' '.join(keywords[:5])  # First 5 keywords

    def _generate_default_params(self, tool_name: str, query: str) -> Dict[str, Any]:
        """Generate reasonable default parameters for speculative execution."""
        keywords = self._extract_keywords_from_query(query)

        # Tool-specific parameter generation
        default_params = {
            'search_funding_calls': {
                'keywords': keywords,
                'status': 'open'
            },
            'search_projects': {
                'keywords': keywords
            },
            'search_documents': {
                'query': query[:200],  # Truncate for search
                'max_results': 10
            },
            'get_budget_benchmark': {
                'action_type': self._extract_action_type(query)
            },
            'get_consortium_patterns': {
                'action_type': self._extract_action_type(query)
            },
            'find_experienced_partners': {
                'keywords': keywords,
                'limit': 10
            },
            'get_programme_statistics': {
                'programme': self._extract_programme(query)
            },
            'get_country_statistics': {
                'country': self._extract_country(query)
            },
            'get_similar_funded_projects': {
                'query': query[:300],
                'limit': 5
            },
            'compare_programmes': {
                'programme_a': 'EIC',
                'programme_b': 'ERC'
            },
            'analyze_call_history': {
                'cluster': self._extract_cluster(query),
                'year_from': 2021,
                'year_to': 2025
            },
        }

        return default_params.get(tool_name, {'query': keywords})

    def _extract_action_type(self, query: str) -> str:
        """Extract action type from query."""
        query_lower = query.lower()
        if 'ria' in query_lower or 'research' in query_lower:
            return 'RIA'
        elif 'ia' in query_lower or 'innovation' in query_lower:
            return 'IA'
        elif 'csa' in query_lower or 'coordination' in query_lower:
            return 'CSA'
        elif 'erc' in query_lower:
            return 'ERC'
        elif 'eic' in query_lower:
            return 'EIC'
        return 'RIA'  # Default

    def _extract_programme(self, query: str) -> str:
        """Extract programme name from query."""
        query_lower = query.lower()
        programmes = {
            'eic': 'EIC Accelerator',
            'erc': 'ERC',
            'msca': 'MSCA',
            'cluster 1': 'Cluster 1',
            'cluster 2': 'Cluster 2',
            'cluster 3': 'Cluster 3',
            'cluster 4': 'Cluster 4',
            'cluster 5': 'Cluster 5',
            'cluster 6': 'Cluster 6',
            'health': 'Cluster 1',
            'digital': 'Cluster 4',
            'climate': 'Cluster 5',
            'food': 'Cluster 6',
        }
        for key, value in programmes.items():
            if key in query_lower:
                return value
        return 'Horizon Europe'

    def _extract_country(self, query: str) -> str:
        """Extract country from query."""
        query_lower = query.lower()
        countries = [
            'germany', 'france', 'spain', 'italy', 'netherlands', 'belgium',
            'austria', 'sweden', 'denmark', 'finland', 'poland', 'portugal',
            'ireland', 'greece', 'hungary', 'romania', 'czech', 'switzerland',
            'norway', 'uk', 'israel'
        ]
        for country in countries:
            if country in query_lower:
                return country.title()
        return 'Germany'  # Default

    def _extract_cluster(self, query: str) -> Optional[str]:
        """Extract cluster from query."""
        query_lower = query.lower()
        cluster_map = {
            'health': 'CL1', 'cl1': 'CL1',
            'culture': 'CL2', 'cl2': 'CL2', 'democracy': 'CL2',
            'security': 'CL3', 'cl3': 'CL3', 'civil': 'CL3',
            'digital': 'CL4', 'cl4': 'CL4', 'industry': 'CL4', 'space': 'CL4',
            'climate': 'CL5', 'cl5': 'CL5', 'energy': 'CL5', 'mobility': 'CL5',
            'food': 'CL6', 'cl6': 'CL6', 'bioeconomy': 'CL6',
        }
        for key, value in cluster_map.items():
            if key in query_lower:
                return value
        return None

    async def start_speculative_execution(
        self,
        query: str,
        context: str = ""
    ) -> Dict[str, asyncio.Task]:
        """
        Start speculative tool execution for likely-needed tools.

        Args:
            query: User's query
            context: Conversation context

        Returns:
            Dict mapping tool names to their asyncio tasks
        """
        likely_tools = self.identify_likely_tools(query)

        if not likely_tools:
            logger.debug("No speculative tools identified for query")
            return {}

        logger.info(f"🔮 Starting speculative execution for: {likely_tools}")

        tasks = {}
        for tool_name in likely_tools:
            # Generate default parameters based on query
            params = self._generate_default_params(tool_name, query)

            # Start execution as background task
            task = asyncio.create_task(
                self._execute_with_tracking(tool_name, params),
                name=f"speculative_{tool_name}"
            )
            tasks[tool_name] = task
            self.speculation_cache[tool_name] = task

        return tasks

    async def _execute_with_tracking(self, tool_name: str, params: Dict) -> Any:
        """Execute tool and track the result."""
        try:
            start = datetime.now()
            result = await self.tool_executor(tool_name, params)
            duration = (datetime.now() - start).total_seconds() * 1000

            # Store result for later use
            self.speculation_results[tool_name] = {
                'result': result,
                'params': params,
                'duration_ms': duration,
                'speculative': True
            }

            logger.debug(f"🔮 Speculative result ready: {tool_name} ({duration:.0f}ms)")
            return result
        except Exception as e:
            logger.warning(f"Speculative execution failed for {tool_name}: {e}")
            return None

    async def get_speculative_result(
        self,
        tool_name: str,
        timeout: float = 0.1,
        requested_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get result from speculative execution if available.

        Args:
            tool_name: Name of the tool
            timeout: Max time to wait (default 100ms)
            requested_params: Parameters being requested (for validation)

        Returns:
            Result dict if ready and params are compatible, None otherwise
        """
        # Check if we already have a cached result
        if tool_name in self.speculation_results:
            cached = self.speculation_results[tool_name]
            cached_params = cached.get('params', {})

            # Validate that speculative params are compatible with requested params
            # For search tools, keywords/query must overlap
            if requested_params and not self._params_compatible(tool_name, cached_params, requested_params):
                logger.debug(f"⚠️ Speculative params don't match for {tool_name}, skipping cache")
                return None

            logger.info(f"🎯 Using cached speculative result for: {tool_name}")
            return cached

        # Check if task is running
        task = self.speculation_cache.get(tool_name)
        if not task:
            return None

        try:
            # Wait briefly for result
            result = await asyncio.wait_for(
                asyncio.shield(task),  # Don't cancel if timeout
                timeout=timeout
            )

            logger.info(f"🎯 Speculative result ready for: {tool_name}")
            return {
                'result': result,
                'speculative': True
            }
        except asyncio.TimeoutError:
            logger.debug(f"⏳ Speculative result not ready: {tool_name}")
            return None
        except asyncio.CancelledError:
            logger.debug(f"🚫 Speculative task cancelled: {tool_name}")
            return None
        except Exception as e:
            logger.warning(f"Error getting speculative result: {e}")
            return None

    def cancel_unused_speculation(self, used_tools: Set[str]):
        """
        Cancel speculative tasks that weren't needed.

        Args:
            used_tools: Set of tool names that were actually used
        """
        cancelled = 0
        for tool_name, task in list(self.speculation_cache.items()):
            if tool_name not in used_tools and not task.done():
                task.cancel()
                cancelled += 1
                logger.debug(f"🚫 Cancelled unused speculation: {tool_name}")

        if cancelled:
            logger.info(f"🚫 Cancelled {cancelled} unused speculative task(s)")

        # Clear caches
        self.speculation_cache.clear()
        self.speculation_results.clear()

    def _params_compatible(self, tool_name: str, cached_params: Dict, requested_params: Dict) -> bool:
        """
        Check if cached speculative params are compatible with requested params.

        For search tools, we require significant keyword overlap.
        For statistics tools, we require exact parameter matches.
        """
        # Tools that require exact parameter match (country, programme, etc.)
        exact_match_tools = {
            'get_country_statistics': 'country',
            'get_programme_statistics': 'programme',
            'compare_programmes': None,  # Multiple params, just skip speculative cache
        }

        if tool_name in exact_match_tools:
            param_key = exact_match_tools[tool_name]
            if param_key is None:
                # For tools like compare_programmes, don't use speculative cache
                return False

            cached_val = cached_params.get(param_key, '').lower().strip()
            requested_val = requested_params.get(param_key, '').lower().strip()

            if cached_val != requested_val:
                logger.debug(f"Parameter mismatch for {tool_name}: cached '{cached_val}' != requested '{requested_val}'")
                return False

            return True

        # Search tools require keyword/query overlap
        search_tools = {'search_funding_calls', 'search_projects', 'search_documents',
                        'find_experienced_partners', 'get_similar_funded_projects'}

        if tool_name in search_tools:
            # Extract keywords from both param sets
            cached_keywords = set()
            requested_keywords = set()

            for key in ['keywords', 'query', 'topic']:
                cached_val = cached_params.get(key, '')
                req_val = requested_params.get(key, '')

                if isinstance(cached_val, list):
                    cached_keywords.update(w.lower() for w in cached_val)
                elif cached_val:
                    cached_keywords.update(cached_val.lower().split())

                if isinstance(req_val, list):
                    requested_keywords.update(w.lower() for w in req_val)
                elif req_val:
                    requested_keywords.update(req_val.lower().split())

            # Require at least 50% overlap or at least 2 common keywords
            if not cached_keywords or not requested_keywords:
                return False

            overlap = cached_keywords & requested_keywords
            overlap_ratio = len(overlap) / min(len(cached_keywords), len(requested_keywords))

            if overlap_ratio < 0.5 and len(overlap) < 2:
                logger.debug(f"Low keyword overlap ({overlap_ratio:.0%}): cached={cached_keywords}, requested={requested_keywords}")
                return False

        return True

    def clear_results(self):
        """Clear all cached speculation results. Call at start of new query."""
        self.speculation_results.clear()
        logger.debug("🗑️ Cleared speculative results cache")

    def get_speculation_stats(self) -> Dict[str, Any]:
        """Get statistics about speculative execution."""
        completed = sum(1 for t in self.speculation_cache.values() if t.done())
        pending = len(self.speculation_cache) - completed

        return {
            'total_speculative': len(self.speculation_cache),
            'completed': completed,
            'pending': pending,
            'cached_results': len(self.speculation_results)
        }
