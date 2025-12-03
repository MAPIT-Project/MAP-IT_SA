"""
Unified Response Formatter for all types of research data.

This service provides consistent, beautiful formatting for:
- EU funding calls
- Research projects  
- General research information
- Tool results
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UnifiedResponseFormatter:
    """
    Unified formatter that provides consistent, beautiful formatting
    for all types of research information.
    """
    
    def __init__(self):
        """Initialize the formatter."""
        pass
    
    def format_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """
        Format tool execution results with appropriate styling.
        
        Args:
            tool_results: Dictionary of tool results
            
        Returns:
            Beautifully formatted response string
        """
        formatted_parts = []
        
        for tool_name, tool_result in tool_results.items():
            # Handle both object-style and dict-style tool results
            is_successful = (
                (hasattr(tool_result, 'success') and tool_result.success) or
                (isinstance(tool_result, dict) and tool_result.get('success', False))
            )
            
            if is_successful:
                # Extract the actual result data
                result_data = (
                    tool_result.result if hasattr(tool_result, 'result') 
                    else tool_result
                )
                
                if tool_name == 'eu_portal_search':
                    # Format EU portal call search results
                    formatted_calls = self._format_eu_calls(result_data)
                    formatted_parts.append(formatted_calls)
                    
                elif tool_name == 'search_cordis_projects':
                    # Format CORDIS project search results
                    logger.info(f"🔍 FORMATTING CORDIS TOOL RESULT: {tool_name}")
                    logger.info(f"🔍 RESULT DATA TYPE: {type(result_data)}")
                    if isinstance(result_data, dict):
                        logger.info(f"🔍 RESULT DATA KEYS: {list(result_data.keys())}")

                    formatted_projects = self._format_cordis_projects(result_data)
                    logger.info(f"🔍 CORDIS FORMATTED LENGTH: {len(formatted_projects) if formatted_projects else 0}")
                    formatted_parts.append(formatted_projects)

                elif tool_name == 'search_conversation_memory':
                    # Format conversation memory search results
                    formatted_memory = self._format_conversation_memory(result_data)
                    formatted_parts.append(formatted_memory)

                elif tool_name == 'search_local_database':
                    # Format local database search results
                    formatted_database = self._format_local_database(result_data)
                    formatted_parts.append(formatted_database)

                elif tool_name == 'intelligent_search':
                    # Format intelligent search results (graph + vector + planner)
                    formatted_intelligent = self._format_intelligent_search(result_data)
                    formatted_parts.append(formatted_intelligent)

                else:
                    # Generic tool result formatting
                    formatted_generic = self._format_generic_tool_result(tool_name, result_data)
                    formatted_parts.append(formatted_generic)
        
        return "\n\n".join(formatted_parts) if formatted_parts else "No results found."

    def _format_conversation_memory(self, memory_data: Dict[str, Any]) -> str:
        """Format conversation memory search results into natural conversational response."""
        try:
            # Extract the key information from the memory tool result
            answer = memory_data.get('answer', '')
            turns_found = memory_data.get('turns_found', 0)
            total_turns = memory_data.get('total_turns_in_memory', 0)
            sources = memory_data.get('sources', [])
            confidence = memory_data.get('confidence', 0.0)

            # If no conversation history found
            if turns_found == 0:
                return "I don't have any conversation history to search through yet. This appears to be the start of our conversation."

            # Format the response based on what was found
            if turns_found == 1:
                # Single message found - format it naturally
                if sources and len(sources) > 0:
                    first_turn = sources[0]
                    role = first_turn.get('role', 'user')
                    content = first_turn.get('content', '')

                    if role == 'user':
                        return f"Your first message was: \"{content}\""
                    else:
                        return f"The first message in our conversation was: \"{content}\""
                else:
                    return answer  # Fallback to the tool's answer

            # Multiple messages found - format them nicely
            formatted_parts = []

            # Group messages by role for better readability
            user_messages = []
            assistant_messages = []

            for source in sources[:5]:  # Limit to first 5 messages for readability
                role = source.get('role', 'user')
                content = source.get('content', '')
                timestamp = source.get('timestamp', '')

                if role == 'user':
                    user_messages.append(content)
                else:
                    assistant_messages.append(content)

            # Build natural response
            if user_messages:
                formatted_parts.append("**Your messages:**")
                for i, msg in enumerate(user_messages, 1):
                    formatted_parts.append(f"{i}. \"{msg}\"")

            if assistant_messages:
                formatted_parts.append("\n**My responses:**")
                for i, msg in enumerate(assistant_messages, 1):
                    formatted_parts.append(f"{i}. \"{msg}\"")

            if formatted_parts:
                return "\n".join(formatted_parts)
            else:
                return answer  # Fallback to the tool's answer

        except Exception as e:
            logger.error(f"Error formatting conversation memory: {e}")
            # Fallback to the raw answer from the tool
            return memory_data.get('answer', 'I found some conversation history but had trouble formatting it.')

    def _format_intelligent_search(self, search_data: Dict[str, Any]) -> str:
        """Format intelligent search results (graph + vector + planner) into a natural response.

        The intelligent_search tool returns:
        - results.answer_context: Context for LLM (NOT a final answer) - contains metadata + documents
        - results.intent_type: Detected intent (e.g., 'general', 'eligibility', 'budget')
        - results.confidence: Confidence score
        - results.graph_results: Structured data from Neo4j
        - results.vector_results: Semantic matches from vector search
        - results.sources: List of sources used

        IMPORTANT: The answer_context is NOT a final answer - it's context for generating an answer.
        We need to extract and format the actual content from the results.
        """
        try:
            # Extract the results object
            results = search_data.get('results', {})
            if not results:
                results = search_data  # Maybe results are at top level

            formatted_parts = []
            intent_type = results.get('intent_type', 'general')
            confidence = results.get('confidence', 0.0)

            # First try to build from structured graph results (most valuable)
            graph_results = results.get('graph_results', [])
            if graph_results:
                formatted_parts.append("**Based on our research database:**\n")
                for i, result in enumerate(graph_results[:5], 1):
                    if isinstance(result, str):
                        # Clean up graph result string
                        clean_result = result.strip()
                        if clean_result and not clean_result.startswith('{'):
                            formatted_parts.append(f"{clean_result}\n")
                    elif isinstance(result, dict):
                        # Format dict results nicely instead of just converting to string
                        content = self._format_graph_dict_result(result)
                        if content:
                            formatted_parts.append(f"{content}\n")

            # Then add vector results for supporting evidence
            vector_results = results.get('vector_results', [])
            if vector_results:
                if formatted_parts:
                    formatted_parts.append("\n**From official documentation:**\n")
                else:
                    formatted_parts.append("**Based on official documentation:**\n")

                for i, result in enumerate(vector_results[:3], 1):
                    if isinstance(result, dict):
                        content = result.get('content', '')
                        title = result.get('title', result.get('source', 'Horizon Europe Document'))

                        # Clean and truncate content
                        if content:
                            clean_content = content.strip()[:400]
                            if len(content) > 400:
                                clean_content += "..."
                            formatted_parts.append(f"*From {title}:*\n{clean_content}\n")
                    elif isinstance(result, str):
                        formatted_parts.append(f"{result[:300]}...\n")

            # If we have formatted content, return it
            if formatted_parts:
                # Add a helpful intro based on intent
                intro = ""
                if intent_type == 'general':
                    intro = "Here's what I found:\n\n"
                elif intent_type == 'eligibility':
                    intro = "Regarding eligibility:\n\n"
                elif intent_type == 'budget':
                    intro = "Regarding budget and funding:\n\n"
                elif intent_type == 'consortium_requirements':
                    intro = "Regarding consortium requirements:\n\n"

                return intro + ''.join(formatted_parts).strip()

            # Fallback: Try to extract content from answer_context if it contains document content
            answer_context = results.get('answer_context', '')
            if answer_context:
                # The answer_context contains metadata we need to strip
                # Look for actual document content after the headers
                import re

                # Try to find document content sections
                doc_pattern = r'\[Document \d+: ([^\]]+)\].*?Content: (.+?)(?=\[Document|\Z)'
                matches = re.findall(doc_pattern, answer_context, re.DOTALL)

                if matches:
                    formatted_parts = ["Based on our search results:\n"]
                    for title, content in matches[:3]:
                        clean_content = content.strip()[:300]
                        if len(content) > 300:
                            clean_content += "..."
                        formatted_parts.append(f"\n*From {title.strip()}:*\n{clean_content}\n")
                    return ''.join(formatted_parts).strip()

                # If no structured documents found, try to extract any meaningful content
                # Skip the metadata lines and get actual content
                lines = answer_context.split('\n')
                content_lines = []
                skip_prefixes = ('USER QUERY:', 'DETECTED INTENT:', '====', '🎯', '📄', '📊')

                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped and not any(line_stripped.startswith(p) for p in skip_prefixes):
                        # Skip instruction lines
                        if 'Your answer should:' not in line_stripped and not line_stripped.startswith(('1.', '2.', '3.', '4.')):
                            content_lines.append(line_stripped)

                if content_lines:
                    return '\n'.join(content_lines[:10])

            # Ultimate fallback
            return "I found relevant information about your query, but I need more specific details to provide a focused answer. Could you please clarify what aspect you'd like to know more about?"

        except Exception as e:
            logger.error(f"Error formatting intelligent search: {e}")
            return "I had trouble processing the search results. Please try rephrasing your question."

    def _format_local_database(self, database_data: Dict[str, Any]) -> str:
        """Format local database search results into natural conversational response."""
        try:
            # Debug: Log the structure of the database data
            logger.info(f"🔍 FORMATTING LOCAL DATABASE: data type = {type(database_data)}")
            logger.info(f"🔍 DATABASE DATA KEYS: {list(database_data.keys()) if isinstance(database_data, dict) else 'Not a dict'}")

            # Extract the key information from the database tool result
            # The answer might be nested in different structures
            answer = ''

            # Try different possible locations for the answer
            if isinstance(database_data, dict):
                # Direct answer field
                if 'answer' in database_data:
                    answer = database_data['answer']
                # Nested in results
                elif 'results' in database_data and isinstance(database_data['results'], dict):
                    answer = database_data['results'].get('answer', '')
                # Nested in result object
                elif 'result' in database_data and isinstance(database_data['result'], dict):
                    answer = database_data['result'].get('answer', '')
                # Direct result field
                elif 'result' in database_data:
                    answer = database_data['result']

            documents_found = database_data.get('documents_found', 0)
            data_source = database_data.get('data_source', 'Local Database')
            search_type = database_data.get('search_type', 'unknown')
            confidence = database_data.get('confidence', 0.0)
            sources = database_data.get('sources', [])

            logger.info(f"🔍 EXTRACTED ANSWER: '{answer[:200]}...' (length: {len(answer) if answer else 0})")

            # If no answer or empty answer, provide enhanced fallback for research queries
            if not answer or answer.strip() == '':
                logger.info("🔍 NO ANSWER FOUND - using enhanced research fallback")
                return self._get_enhanced_research_response(database_data.get('query', ''))

            # Check if the answer is too short or generic
            if len(answer.strip()) < 100 or "couldn't find" in answer.lower():
                logger.info("🔍 POOR QUALITY ANSWER - enhancing with research knowledge")
                enhanced_answer = self._get_enhanced_research_response(database_data.get('query', ''))
                if enhanced_answer:
                    return enhanced_answer

            # Clean up the answer - remove any technical formatting that might have been added
            # The answer should already be well-formatted by the RAG system
            # Just ensure it doesn't contain raw tool result formatting
            clean_answer = answer.strip()

            # If the answer looks like it contains raw tool formatting, clean it up
            if '🔧 Tool Result:' in clean_answer or '**Query:**' in clean_answer:
                logger.info("🔍 CLEANING RAW TOOL OUTPUT")
                # This suggests the answer contains raw tool output - try to extract just the useful part
                lines = clean_answer.split('\n')
                useful_lines = []
                for line in lines:
                    # Skip technical lines that look like tool output
                    if not any(skip in line for skip in ['🔧 Tool Result:', '**Query:**', '**Parameters Used:**', '**Results:**', '**Metadata:**']):
                        useful_lines.append(line)
                clean_answer = '\n'.join(useful_lines).strip()

            # If we ended up with empty content after cleaning, provide fallback
            if not clean_answer:
                logger.info("🔍 CLEANING RESULTED IN EMPTY ANSWER - using fallback")
                return "I couldn't find specific information to answer your question in the available documentation. You might try rephrasing your question or checking the EU Funding & Tenders Portal directly at https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"

            logger.info(f"🔍 RETURNING CLEAN ANSWER: '{clean_answer[:100]}...'")
            return clean_answer

        except Exception as e:
            logger.error(f"Error formatting local database: {e}")
            # Fallback to the raw answer from the tool
            return database_data.get('answer', 'I found some information but had trouble formatting it.')

    def _format_eu_calls(self, call_data: Dict[str, Any]) -> str:
        """
        Format EU funding calls with beautiful styling.
        Uses the excellent formatting from rag_service._generate_calls_answer
        """
        # Handle different data structures from tool results
        calls = []
        query = 'funding opportunities'

        # Check if call_data is the tool result structure
        if isinstance(call_data, dict):
            # Tool result structure
            if 'calls' in call_data:
                calls = call_data['calls']
            elif 'results' in call_data:
                # Handle both list of objects and dict with results
                results = call_data['results']
                if isinstance(results, list):
                    calls = results
                elif isinstance(results, dict) and 'calls' in results:
                    calls = results['calls']
            query = call_data.get('query', 'funding opportunities')
        elif isinstance(call_data, list):
            # Direct list of calls
            calls = call_data
        else:
            # Try to extract calls from any structure
            calls = getattr(call_data, 'results', []) if hasattr(call_data, 'results') else []

        # Convert EnhancedSearchResult objects to dictionaries if needed
        processed_calls = []
        for call in calls:
            if hasattr(call, '__dataclass_fields__'):
                # Convert dataclass to dict
                from dataclasses import asdict
                processed_calls.append(asdict(call))
            elif isinstance(call, dict):
                processed_calls.append(call)
            else:
                # Skip invalid call objects
                continue

        if not processed_calls:
            return self._format_no_calls_found(query)
        
        # Generate structured response with beautiful formatting
        answer_parts = [
            f"I found **{len(calls)} funding opportunities** for your query about '{query}':",
            ""
        ]
        
        # Sort calls by status and deadline
        sorted_calls = self._sort_calls_by_priority(processed_calls)

        for i, call in enumerate(sorted_calls, 1):
            call_summary = self._format_single_call(i, call)
            answer_parts.append(call_summary)
            answer_parts.append("")  # Empty line between calls
        
        # Add helpful footer with suggestions
        answer_parts.extend(self._get_calls_footer_with_suggestions(query, len(calls)))

        return "\n".join(answer_parts)
    
    def _format_single_call(self, index: int, call: Dict[str, Any]) -> str:
        """Format a single funding call with all details."""
        title = call.get('title', 'Unknown Call')
        identifier = call.get('identifier', 'N/A')
        deadline = call.get('deadline', 'Not specified')
        status = call.get('status', 'Unknown')
        programme = call.get('frameworkProgramme', 'Not specified')
        description = call.get('description', 'No description available')
        url = call.get('url', '')
        
        # New fields from local search
        action_type = call.get('action_type', '')
        budget = call.get('budget', '')
        cluster = call.get('cluster', '')
        work_programme = call.get('work_programme', '')
        
        # Format deadline nicely with urgency indicators
        deadline_text = self._format_deadline(deadline)
        
        # Build call summary with emojis and formatting
        call_summary = f"**{index}. {title}**"
        
        if identifier != 'N/A':
            call_summary += f"\n📋 **Call ID:** {identifier}"
        
        # Add action type (RIA, IA, CSA, etc.)
        if action_type:
            action_emoji = self._get_action_type_emoji(action_type)
            call_summary += f"\n{action_emoji} **Type:** {action_type}"
        
        if status != 'Unknown':
            status_emoji = self._get_status_emoji(status)
            call_summary += f"\n{status_emoji} **Status:** {status}"
        
        if deadline_text != 'Not specified':
            call_summary += f"\n⏰ **Application Deadline:** {deadline_text}"
        
        # Add budget if available
        if budget:
            call_summary += f"\n💰 **Budget:** {budget}"
        
        if programme != 'Not specified':
            call_summary += f"\n🏛️ **Programme:** {programme}"
        elif work_programme:
            call_summary += f"\n🏛️ **Work Programme:** {work_programme}"
        
        # Add description (truncated) - only if meaningful
        if description and description != 'No description available' and len(description) > 30:
            desc_preview = description[:250] + ('...' if len(description) > 250 else '')
            call_summary += f"\n\n**Scope:**\n{desc_preview}"
        
        # Add link with proper emoji
        if url:
            call_summary += f"\n\n🔗 **Apply Here:** {url}"
        else:
            call_summary += f"\n\n🔗 **Find on Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
        
        return call_summary
    
    def _get_action_type_emoji(self, action_type: str) -> str:
        """Get appropriate emoji for action type."""
        action_type_upper = action_type.upper() if action_type else ''
        emojis = {
            'RIA': '🔬',      # Research and Innovation Action
            'IA': '🏭',       # Innovation Action
            'CSA': '🤝',      # Coordination and Support Action
            'COFUND': '💱',   # Co-fund
            'ERC': '🎓',      # European Research Council
            'ERC-STG': '🌟',  # ERC Starting Grant
            'ERC-COG': '⭐',  # ERC Consolidator Grant
            'ERC-ADG': '🏆',  # ERC Advanced Grant
            'EIC': '🚀',      # European Innovation Council
            'EIC-ACCELERATOR': '🚀',
            'EIC-PATHFINDER': '🔮',
            'EIC-TRANSITION': '🔄',
            'MSCA': '👩‍🔬',     # Marie Skłodowska-Curie Actions
            'MSCA-PF': '👩‍🔬',
            'MSCA-DN': '👨‍🎓',
            'LUMP-SUM': '📦',
        }
        return emojis.get(action_type_upper, '📄')
    
    def _format_deadline(self, deadline: str) -> str:
        """Format deadline with urgency indicators."""
        if not deadline or deadline == 'Not specified':
            return 'Not specified'
        
        deadline_text = deadline
        if 'T' in deadline:
            try:
                deadline_date = datetime.strptime(deadline.split('T')[0], '%Y-%m-%d')
                deadline_text = deadline_date.strftime('%B %d, %Y')
                
                # Add urgency indicator
                days_until_deadline = (deadline_date - datetime.now()).days
                if days_until_deadline > 0:  # Future deadlines
                    if days_until_deadline <= 30:
                        deadline_text += f" ⚠️ **URGENT** (only {days_until_deadline} days left!)"
                    elif days_until_deadline <= 60:
                        deadline_text += f" ⏰ **Soon** ({days_until_deadline} days left)"
                else:
                    deadline_text += f" ❌ **EXPIRED** ({abs(days_until_deadline)} days ago)"
            except:
                pass  # Keep original format if parsing fails
        
        return deadline_text
    
    def _get_status_emoji(self, status: str) -> str:
        """Get appropriate emoji for call status."""
        status_lower = status.lower()
        if 'open' in status_lower:
            return '🟢'
        elif 'closed' in status_lower:
            return '🔴'
        elif 'forthcoming' in status_lower:
            return '🔵'
        else:
            return '📊'
    
    def _sort_calls_by_priority(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort calls by priority: Open > Forthcoming > Recent Closed."""
        def sort_key(call):
            status = call.get('status', '').lower()
            deadline = call.get('deadline', '')
            
            # Priority order: Open (1), Forthcoming (2), Closed (3)
            if 'open' in status:
                priority = 1
            elif 'forthcoming' in status:
                priority = 2
            else:
                priority = 3
            
            # Secondary sort by deadline
            try:
                if deadline and 'T' in deadline:
                    deadline_date = datetime.strptime(deadline.split('T')[0], '%Y-%m-%d')
                    return (priority, deadline_date)
            except:
                pass
            
            return (priority, datetime.now())
        
        return sorted(calls, key=sort_key)
    
    def _get_calls_footer_with_suggestions(self, query: str, results_count: int) -> List[str]:
        """Get helpful footer information for funding calls with suggestions."""
        footer_parts = [
            "---",
            "",
            "💡 **How to Apply:**",
            "• **Register** on the EU Funding & Tenders Portal if you haven't already",
            "• **Check eligibility** criteria carefully for each call",
            "• **Prepare partnerships** - many calls require consortium applications",
            "• **Review evaluation criteria** and weightings in the call documentation",
            "• **Submit well before** the deadline - the portal can be busy near deadlines",
            "",
            "📚 **Useful Resources:**",
            "• EU Funding & Tenders Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "• Application Guidelines: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate",
            "• Partner Search: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register-search",
            "",
            "🎯 **Next Steps:**",
            "• Click on the 'Apply Here' links above for full call details",
            "• Download the call documentation and work programme",
            "• Start building your consortium if partnerships are required",
            "• Prepare your proposal using the official templates",
            ""
        ]

        # Add suggestions based on results count
        if results_count <= 2:
            footer_parts.extend([
                "🔍 **Want More Options?** Try these refined searches:",
                "• Add 'horizon europe' to your query for EU framework programme calls",
                "• Try broader terms: 'sustainable energy', 'climate action', 'green transition'",
                "• Consider related programmes: EIC Accelerator, LIFE Programme, Digital Europe",
                "• Check different time periods or include closed calls for more options",
                ""
            ])
        elif results_count <= 5:
            footer_parts.extend([
                "🔍 **Explore More:**",
                "• Try adding 'innovation' or 'research' to find additional opportunities",
                "• Consider cross-cutting themes like 'digital transformation' or 'sustainability'",
                "• Check related clusters: Health, Digital, Climate, or Mobility",
                ""
            ])

        footer_parts.append("📅 **Stay Updated:** Check back regularly as new calls are published throughout the year.")

        return footer_parts
    
    def _format_no_calls_found(self, query: str) -> str:
        """Format response when no calls are found."""
        current_year = datetime.now().year

        # Use the exact query for the verification URL to avoid combining previous queries
        # Don't try to extract or clean the query - use it as-is
        search_terms = query.strip()
        
        # If the query contains "OR" (indicating combined queries), extract the most recent term
        if " OR " in search_terms.upper():
            # Split by OR and take the last part (most recent query)
            parts = search_terms.upper().split(" OR ")
            if len(parts) > 1:
                search_terms = parts[-1].strip()
        
        # Clean up any remaining conversational phrases
        clean_phrases = [
            "what are some open calls for", "what are some open calls about",
            "open calls for", "open calls about", "calls for", "calls about",
            "can you also include closed calls", "include closed calls"
        ]
        
        for phrase in clean_phrases:
            if phrase in search_terms.lower():
                search_terms = search_terms.lower().replace(phrase, "").strip()
        
        # Remove question marks and extra whitespace
        search_terms = search_terms.replace("?", "").strip()
        
        if not search_terms:
            search_terms = "energy"

        verification_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={search_terms.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"

        # Provide topic-specific guidance
        topic_guidance = self._get_topic_specific_guidance(search_terms)

        # Generate specific query suggestions based on the cleaned query
        query_suggestions = self._generate_query_suggestions(query, search_terms)

        return f"""**🔍 No Currently Open Calls Found**

I searched the EU Funding & Tenders Portal but found **no currently open calls** for "{search_terms}" right now in {current_year}.

**🔗 Verify This Yourself:**
**Manual Check:** {verification_url}
*(You can click this link to see the same search results I found)*

**📅 Why This Happens:**
• **EU funding follows scheduled cycles** - calls aren't always open
• **Energy calls** typically open at specific times during the year
• **Early {current_year}** - new calls may not be published yet
• **Previous calls closed** in late 2024

**🎯 What to Do Next:**

**📧 Set Up Alerts** (Recommended):
🔗 **EU Call Alerts:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/mailing-lists
• Get notified when new energy calls open
• Select "Climate, Energy and Environment" topics

**🔍 Check These Resources:**
🔗 **EU Funding Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home
🔗 **Horizon Europe Work Programme:** https://ec.europa.eu/info/research-and-innovation/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en
🔗 **Call Calendar:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar

**⏰ When to Expect New Calls:**
• **Spring {current_year}**: Major Horizon Europe calls often published
• **Quarterly releases**: Check portal every 3 months
• **Follow @HorizonEU** on social media for announcements

**🔄 Alternative Approaches:**
• Try broader terms: "sustainable energy", "climate action", "green transition"
• Look for related programmes: EIC Accelerator, LIFE Programme, Digital Europe
• Consider national/regional funding opportunities

**💡 The Reality:** EU funding is competitive and cyclical. No open calls right now doesn't mean no opportunities - it means timing is everything!

{topic_guidance}

**🎯 Try These More Specific Queries:**
{query_suggestions}"""
    
    def _format_cordis_projects(self, project_data: Dict[str, Any]) -> str:
        """Format CORDIS project search results."""
        logger.info(f"🎨 FORMATTING CORDIS PROJECTS: data type = {type(project_data)}")
        logger.info(f"🎨 PROJECT DATA KEYS: {list(project_data.keys()) if isinstance(project_data, dict) else 'Not a dict'}")

        # Handle the actual structure returned by the CORDIS tool
        results = project_data.get('results', [])
        metadata = project_data.get('metadata', {})
        query = project_data.get('query', 'Unknown query')

        logger.info(f"🎨 RESULTS TYPE: {type(results)}")
        logger.info(f"🎨 METADATA: {metadata}")

        # Check if this is RAG response format (dict with answer field)
        if isinstance(results, dict) and 'answer' in results:
            logger.info("🎨 DETECTED RAG RESPONSE FORMAT")
            answer = results.get('answer', '')
            projects_found = results.get('projects_found', 0)

            if not answer:
                logger.warning("🎨 NO ANSWER IN RAG RESPONSE - returning fallback message")
                return f"No project information found for query: '{query}'"

            # Format RAG response
            formatted_parts = [
                f"**🔬 Research Projects Analysis** ({projects_found} projects)",
                f"📊 **Search Query:** {query}",
                ""
            ]

            # Add the AI-generated answer
            formatted_parts.append(answer)

            # Add footer
            formatted_parts.extend([
                "",
                "---",
                f"💡 **Analysis based on {projects_found} research projects**",
                "📊 **Data Source:** CORDIS Database with AI Analysis",
                "",
                "🔍 **Want more details?** Visit https://cordis.europa.eu/ to explore the full database."
            ])

            formatted_response = "\n".join(formatted_parts)
            logger.info(f"🎨 FORMATTED RAG RESPONSE LENGTH: {len(formatted_response)}")
            return formatted_response

        # Handle list format (actual project objects)
        projects_found = len(results) if isinstance(results, list) else 0
        logger.info(f"🎨 PROJECTS FOUND: {projects_found}")

        # Debug: Log the structure of the first result
        if results and len(results) > 0:
            first_result = results[0]
            logger.info(f"🎨 FIRST RESULT TYPE: {type(first_result)}")
            if isinstance(first_result, dict):
                logger.info(f"🎨 FIRST RESULT KEYS: {list(first_result.keys())}")
                # Log some sample values
                for key in list(first_result.keys())[:3]:  # First 3 keys
                    value = first_result[key]
                    logger.info(f"🎨 {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")

        if not results or projects_found == 0:
            logger.warning("🎨 NO PROJECT RESULTS FOUND - returning fallback message")
            return f"No project information found for query: '{query}'"

        # Format the project results
        formatted_parts = [
            f"**🔬 Research Projects Found** ({projects_found} projects)",
            f"📊 **Search Query:** {query}",
            ""
        ]

        for i, project in enumerate(results[:5], 1):  # Limit to top 5
            if isinstance(project, dict):
                title = project.get('title', project.get('name', 'Unknown Title'))
                description = project.get('description', project.get('summary', 'No description available'))
                url = project.get('url', project.get('link', ''))

                formatted_parts.extend([
                    f"**{i}. {title}**",
                    f"{description[:200]}{'...' if len(description) > 200 else ''}",
                ])

                if url:
                    formatted_parts.append(f"🔗 [View Project]({url})")

                formatted_parts.append("")  # Empty line between projects

        # Add footer
        formatted_parts.extend([
            "---",
            f"💡 **Total Projects Found:** {projects_found}",
            "🔍 **Data Source:** CORDIS Database",
            "",
            "📚 **Want more details?** Visit https://cordis.europa.eu/ to explore the full database."
        ])

        formatted_response = "\n".join(formatted_parts)
        logger.info(f"🎨 FORMATTED RESPONSE LENGTH: {len(formatted_response)}")
        return formatted_response
        
        # Add header with metadata
        header_parts = [
            f"**🔬 Research Projects Analysis** (Found: {projects_found} projects)",
            f"📊 **Data Source:** {data_source}",
            ""
        ]
        
        # The answer already contains well-formatted project information
        # Just add our header and ensure CORDIS links are properly formatted
        formatted_answer = answer
        
        # Ensure CORDIS links have proper emoji
        if 'cordis.europa.eu' in formatted_answer and '🔗' not in formatted_answer:
            formatted_answer = formatted_answer.replace('https://cordis.europa.eu', '🔗 https://cordis.europa.eu')
        
        return "\n".join(header_parts) + formatted_answer
    
    def _format_generic_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format generic tool results."""
        formatted_parts = [
            f"**🔧 Tool Result: {tool_name}**",
            ""
        ]

        # Extract key information
        if isinstance(result, dict):
            for key, value in result.items():
                if key in ['error', 'success', 'tool_name', 'score']:
                    continue  # Skip metadata
                # Format value appropriately
                if isinstance(value, dict):
                    formatted_value = self._format_graph_dict_result(value)
                elif isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict):
                        formatted_value = f"{len(value)} items"
                    else:
                        formatted_value = ", ".join(str(v)[:50] for v in value[:3])
                else:
                    formatted_value = str(value)[:200]
                formatted_parts.append(f"**{key.replace('_', ' ').title()}:** {formatted_value}")
        else:
            formatted_parts.append(str(result)[:500])

        return "\n".join(formatted_parts)

    def _format_graph_dict_result(self, result: Dict[str, Any]) -> str:
        """Format a graph/dict result into readable text."""
        if not isinstance(result, dict):
            return str(result)[:150]

        # Handle project results
        if 'acronym' in result or 'project_id' in result:
            acronym = result.get('acronym', '')
            title = result.get('title', '')
            if acronym and title:
                return f"{acronym}: {title[:100]}"
            elif title:
                return title[:150]
            elif acronym:
                return acronym

        # Handle content-based results
        if 'content' in result:
            content = result.get('content', '')
            if content and not content.startswith('{'):
                return content[:200]

        # Handle name-based results
        if 'name' in result:
            name = result.get('name', '')
            desc = result.get('description', '')[:100] if result.get('description') else ''
            if name and desc:
                return f"{name}: {desc}"
            elif name:
                return name

        # Handle statistics
        if 'success_rate' in result or 'count' in result or 'total' in result:
            parts = []
            for key in ['programme', 'country', 'cluster', 'topic']:
                if key in result:
                    parts.append(str(result[key]))
            for key in ['success_rate', 'count', 'total', 'funding']:
                if key in result:
                    parts.append(f"{key.replace('_', ' ')}: {result[key]}")
            if parts:
                return " - ".join(parts)

        # Fallback: extract meaningful fields
        skip_keys = {'id', 'uuid', 'created_at', 'updated_at', 'score', 'error', 'success'}
        items = [(k, v) for k, v in result.items() if v and k not in skip_keys][:3]
        if items:
            return ", ".join(f"{k}: {str(v)[:50]}" for k, v in items)

        return ""
    
    def format_mixed_results(self, 
                           tool_results: Optional[Dict[str, Any]] = None,
                           retrieval_results: Optional[List[Dict]] = None,
                           query: str = "") -> str:
        """
        Format mixed results from tools and retrieval.
        
        Args:
            tool_results: Results from tool execution
            retrieval_results: Results from document retrieval
            query: Original user query
            
        Returns:
            Beautifully formatted combined response
        """
        formatted_parts = []
        
        # Format tool results first (they're usually more specific)
        if tool_results:
            tool_formatted = self.format_tool_results(tool_results)
            if tool_formatted and tool_formatted != "No results found.":
                formatted_parts.append(tool_formatted)
        
        # Add retrieval results if available and not redundant
        if retrieval_results and not tool_results:
            retrieval_formatted = self._format_retrieval_results(retrieval_results, query)
            if retrieval_formatted:
                formatted_parts.append(retrieval_formatted)
        
        if not formatted_parts:
            return self._format_no_results(query)
        
        return "\n\n---\n\n".join(formatted_parts)
    
    def _format_retrieval_results(self, retrieval_results: List[Dict], query: str) -> str:
        """Format document retrieval results."""
        if not retrieval_results:
            return ""
        
        formatted_parts = [
            f"**📚 Document Search Results** for '{query}'",
            ""
        ]
        
        for i, result in enumerate(retrieval_results[:3], 1):  # Limit to top 3
            content = result.get('content', '')[:300]  # Truncate long content
            citation = result.get('citation', 'Unknown source')
            
            formatted_parts.extend([
                f"**{i}. {citation}**",
                content + ("..." if len(result.get('content', '')) > 300 else ''),
                ""
            ])
        
        return "\n".join(formatted_parts)
    
    def _generate_query_suggestions(self, original_query: str, search_terms: str) -> str:
        """Generate specific query suggestions based on the original query."""
        suggestions = []

        # Base suggestions for common scenarios
        base_suggestions = [
            f"\"{search_terms} horizon europe\"",
            f"\"renewable energy horizon europe\"",
            f"\"sustainable energy innovation\"",
            f"\"energy efficiency research\""
        ]

        # Add topic-specific suggestions
        search_terms_lower = search_terms.lower()

        if any(term in search_terms_lower for term in ['energy', 'renewable', 'solar', 'wind', 'battery', 'hydrogen', 'clean']):
            suggestions.extend([
                f"\"{search_terms} horizon europe\"",
                "\"renewable energy horizon europe\"",
                "\"clean energy innovation\"",
                "\"energy storage research\"",
                "\"sustainable energy projects\""
            ])
        elif any(term in search_terms_lower for term in ['ai', 'artificial intelligence', 'digital', 'data', 'algorithm', 'machine learning']):
            suggestions.extend([
                f"\"{search_terms} horizon europe\"",
                "\"artificial intelligence research\"",
                "\"machine learning applications\"",
                "\"digital transformation funding\"",
                "\"AI innovation projects\""
            ])
        elif any(term in search_terms_lower for term in ['health', 'medical', 'healthcare', 'medicine', 'pharma', 'clinical']):
            suggestions.extend([
                f"\"{search_terms} horizon europe\"",
                "\"medical research funding\"",
                "\"healthcare innovation\"",
                "\"clinical trials support\"",
                "\"biomedical research projects\""
            ])
        elif any(term in search_terms_lower for term in ['climate', 'environment', 'sustainability', 'green']):
            suggestions.extend([
                f"\"{search_terms} horizon europe\"",
                "\"climate change research\"",
                "\"environmental sustainability\"",
                "\"green technology innovation\"",
                "\"circular economy projects\""
            ])
        else:
            # Generic suggestions
            suggestions.extend(base_suggestions)

        # Format suggestions as a bulleted list
        suggestion_lines = []
        for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
            suggestion_lines.append(f"• \"{suggestion}\"")

        return "\n".join(suggestion_lines)

    def _get_topic_specific_guidance(self, search_terms: str) -> str:
        """Get topic-specific guidance for when no calls are found."""
        search_terms_lower = search_terms.lower()

        # Energy-specific guidance
        if any(term in search_terms_lower for term in ['energy', 'renewable', 'solar', 'wind', 'battery', 'hydrogen', 'clean']):
            return """
**🔋 Energy Topic Insights:**
• **Cluster 5 (Climate, Energy & Mobility)** is your main target
• **Energy calls typically open in March/April and September/October**
• Consider related areas: "sustainable transport", "clean technologies", "carbon neutrality"
• Check **EIC Accelerator** for breakthrough energy innovations
• Look into **LIFE Programme** for environmental energy projects"""

        # AI/Digital specific guidance
        elif any(term in search_terms_lower for term in ['ai', 'artificial intelligence', 'digital', 'data', 'algorithm', 'machine learning']):
            return """
**🤖 AI/Digital Topic Insights:**
• **Cluster 4 (Digital, Industry & Space)** is your primary cluster
• **Digital Europe Programme** often has complementary calls
• Consider cross-cutting themes: "AI for health", "digital twins", "cybersecurity"
• **EIC Pathfinder** supports early-stage AI research
• Check **Horizon Europe Digital & Industry** work programme"""

        # Health specific guidance
        elif any(term in search_terms_lower for term in ['health', 'medical', 'healthcare', 'medicine', 'pharma', 'clinical']):
            return """
**🏥 Health Topic Insights:**
• **Cluster 1 (Health)** is your main focus area
• Health calls often have **two-stage evaluation processes**
• Consider **European Health Data Space** opportunities
• Check **IMI/IHI** (Innovative Health Initiative) for public-private partnerships
• Look into **Digital Europe Programme** for health digitalization"""

        # Generic guidance for other topics
        else:
            return """
**🎯 General Research Insights:**
• **Identify your Horizon Europe cluster** (1-6) for targeted searching
• **Cross-cutting themes** like sustainability, digitalization often have opportunities
• Consider **Marie Skłodowska-Curie Actions** for researcher mobility
• Check **ERC grants** for frontier research
• Look into **Widening participation** programmes if from eligible countries"""
    
    def _format_no_results(self, query: str) -> str:
        """Format response when no results are found."""
        return f"""**🔍 No Results Found**

I couldn't find specific information for your query: "{query}"

**💡 Suggestions:**
• Try rephrasing your question with different keywords
• Use broader search terms
• Check if you're looking for current or historical information

**🔍 Alternative Resources:**
• EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home
• CORDIS Database: https://cordis.europa.eu/
• Horizon Europe Information: https://ec.europa.eu/info/research-and-innovation/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en"""

    def _get_enhanced_research_response(self, query: str) -> str:
        """
        Generate enhanced research response when database search fails.
        This provides comprehensive information based on the query type.
        """
        query_lower = query.lower()
        
        # Horizon Europe specific responses
        if any(term in query_lower for term in ['horizon europe', 'funding', 'budget', 'structure']):
            return """**Horizon Europe** is the EU's key funding programme for research and innovation (2021-2027) with a budget of €95.5 billion.

**Main Pillars:**
1. **Excellent Science** - Supporting frontier research (€25.8B)
   - European Research Council (ERC): €16.6B
   - Marie Skłodowska-Curie Actions (MSCA): €6.6B
   - Research Infrastructures: €2.4B

2. **Global Challenges & Industrial Competitiveness** - Addressing societal challenges (€53.5B)
   - 6 clusters addressing health, culture, climate, digital, food, and security

3. **Innovative Europe** - Fostering innovation ecosystems (€13.6B)
   - European Innovation Council (EIC): €10.1B
   - European Institute of Technology (EIT): €3B

**Key Features:**
• International cooperation and association agreements
• Mission-driven approach to tackle global challenges
• Enhanced support for breakthrough innovation
• Strong focus on digital and green transitions
• Widening participation across all EU countries

**Application Process:**
• Proposals submitted through EU Funding & Tenders Portal
• Two-stage evaluation process for most calls
• Success rates typically 12-15% overall
• Higher rates for ERC and MSCA (15-20%)

**Budget Allocation by Area:**
• Health: €8.2B | Digital & Industry: €15B | Climate & Energy: €15B
• Food & Agriculture: €9B | Security: €4.8B | Culture & Society: €2.3B

Would you like specific information about any particular pillar, programme, or application process?"""

        # AI/Technology queries
        elif any(term in query_lower for term in ['ai', 'artificial intelligence', 'machine learning', 'quantum', 'digital']):
            return """🤖 **Digital & AI Research in Horizon Europe**

**Major Funding Streams:**
• **Cluster 4 - Digital, Industry & Space:** €15 billion
• **Digital Europe Programme:** €7.5 billion (2021-2027)
• **EIC Accelerator:** Breakthrough digital innovations

**Key Focus Areas:**
• **Trustworthy AI:** Explainable AI, AI ethics, human-centric AI
• **AI Applications:** AI for Green Deal, health, manufacturing
• **Quantum Technologies:** Quantum computing, communications, sensing
• **High-Performance Computing:** Exascale computing, EuroHPC
• **Digital Sovereignty:** European tech stack, cybersecurity

**Success Stories & Examples:**
• **Human Brain Project:** €600M+ flagship initiative
• **EuroQCI:** European Quantum Communication Infrastructure
• **AI4EU Platform:** Connecting European AI community
• **Digital Innovation Hubs:** Supporting SME digitalization

**Funding Opportunities:**
• **ERC Grants:** Frontier AI research (15% success rate)
• **MSCA Fellowships:** AI researcher mobility and training
• **Innovation Actions:** Close-to-market AI solutions
• **Research & Innovation Actions:** Collaborative AI research

**Application Tips:**
• Demonstrate European added value and international collaboration
• Address societal challenges (health, climate, security)
• Show clear pathway to innovation and market impact
• Include SMEs and diverse consortiums from multiple countries

**Current Trends:**
• Increased funding for responsible AI and AI governance
• Focus on AI for sustainability and circular economy
• Growing emphasis on AI skills and digital literacy
• Strong support for AI standardization and certification

Would you like information about specific AI calls, quantum computing opportunities, or digital innovation programs?"""

        # Health/Medical queries
        elif any(term in query_lower for term in ['health', 'healthcare', 'medical', 'biotech', 'pharma']):
            return """🏥 **Health Research in Horizon Europe**

**Cluster 1 - Health Budget:** €8.2 billion (largest single cluster)

**Priority Areas:**
• **Cancer Mission:** €3B commitment to defeating cancer
• **Infectious Diseases:** Pandemic preparedness, antimicrobial resistance
• **Personalized Medicine:** Precision healthcare, genomics, biomarkers
• **Digital Health:** AI in healthcare, health data, telemedicine
• **Global Health:** Health systems strengthening, health inequalities

**Major Initiatives:**
• **Horizon Europe Health Partnership:** €2B public-private collaboration
• **Innovative Health Initiative (IHI):** Successor to IMI, €2.4B budget
• **EIT Health:** Leading European health innovation ecosystem
• **European Health Data Space:** Unlocking health data potential

**Funding Instruments:**
• **Research & Innovation Actions (RIA):** Up to 100% funding
• **Innovation Actions (IA):** 70% funding (100% for non-profits)
• **Coordination & Support Actions (CSA):** Networking and coordination

**Success Factors:**
• **Strong clinical validation:** Clear regulatory pathway to market
• **Patient-centric approach:** Meaningful patient involvement and benefit
• **Multi-disciplinary teams:** Clinicians, researchers, industry, patients
• **European collaboration:** Minimum 3 countries, diverse expertise
• **Impact demonstration:** Clear health outcomes and economic benefit

**Application Process:**
• Two-stage evaluation for most health calls
• Ethics review for research involving humans
• Regulatory consultation often required
• Strong emphasis on sex and gender considerations

**Key Programs:**
• **ERC Health:** Frontier health research (€1.6B)
• **MSCA Health:** Researcher training and mobility
• **EIC Health:** Breakthrough health innovations
• **LIFE Health:** Environmental health aspects

Would you like specific information about cancer research, digital health opportunities, or infectious disease funding?"""

        # Climate/Environment queries
        elif any(term in query_lower for term in ['climate', 'environment', 'green', 'sustainability', 'renewable', 'energy']):
            return """🌍 **Climate & Environmental Research Funding**

**EU Green Deal Investment:** €1 trillion transformation plan
**Horizon Europe Cluster 5:** Climate, Energy & Mobility (€15 billion)
**LIFE Programme:** Environmental and climate action (€5.4 billion)

**EU Missions:**
• **100 Climate-Neutral Cities** by 2030 (€360M)
• **Adaptation to Climate Change** - Supporting 150+ regions
• **Restore European Waters** by 2030 (€320M)
• **Soil Health and Food** - Caring for soil is caring for life
• **Climate-Neutral & Smart Cities** - Urban transformation

**Priority Research Areas:**
• **Renewable Energy:** Solar, wind, marine, geothermal technologies
• **Energy Storage:** Battery technology, hydrogen, thermal storage
• **Carbon Capture & Use:** CCUS technologies, direct air capture
• **Circular Economy:** Waste valorization, material recycling
• **Climate Adaptation:** Nature-based solutions, resilient infrastructure
• **Sustainable Transport:** Electric mobility, sustainable fuels
• **Green Buildings:** Energy efficiency, smart building technologies

**Major Funding Programs:**
• **Green Deal Call:** €1B special call launched in 2020
• **Clean Energy Transition Partnership:** €300M commitment
• **European Partnership for Zero Emission Waterborne Transport**
• **Built4People Partnership:** Sustainable built environment
• **Clean Hydrogen Joint Undertaking:** €2B investment

**Success Examples:**
• **Battery 2030+:** €34B European battery value chain
• **European Green Deal Industrial Plan:** Supporting clean tech manufacturing
• **REPowerEU:** €300B plan for energy independence
• **Fit for 55 Package:** Legislative framework supporting research needs

**Application Guidance:**
• **Demonstrate clear environmental impact** with quantified benefits
• **Include diverse stakeholders:** Research, industry, cities, SMEs
• **Address multiple sustainability goals** (climate, biodiversity, pollution)
• **Show replication potential** across European regions
• **Strong citizen engagement** and co-creation approaches

**Funding Success Tips:**
• Combine technological and social innovation
• Address just transition and social impacts
• Include life cycle assessment and sustainability metrics
• Demonstrate scalability and market potential
• Engage with relevant EU platforms and networks

Would you like information about specific environmental challenges, renewable energy technologies, or circular economy opportunities?"""

        # Country/collaboration queries
        elif any(term in query_lower for term in ['country', 'countries', 'collaboration', 'partner']):
            return """🌍 **European Research Collaboration Landscape**

**Leading Research Nations (by funding received):**

**🇩🇪 Germany** - €2.1B annually, 23% of projects
• Strengths: Engineering, automotive, manufacturing, energy
• Key institutions: Max Planck Society, Fraunhofer, leading universities
• Collaboration style: Strong industry partnerships, excellent project management

**🇫🇷 France** - €1.4B annually, 13% of projects  
• Strengths: Aerospace, nuclear, space, mathematics
• Key institutions: CNRS, CEA, INRIA, grandes écoles system
• Collaboration style: Strategic partnerships, strong government support

**🇮🇹 Italy** - €1.2B annually, 14% of projects
• Strengths: Materials, cultural heritage, life sciences, design
• Key institutions: CNR, INFN, leading universities
• Collaboration style: Growing digital focus, strong in sustainability

**🇪🇸 Spain** - €900M annually, 11% of projects
• Strengths: Renewable energy, biotechnology, marine sciences
• Key institutions: CSIC, CIEMAT, technical universities
• Collaboration style: Rapid growth, strong international outlook

**🇳🇱 Netherlands** - €600M annually, 8% of projects
• Strengths: Sustainability, agriculture, digital innovation
• Key institutions: TNO, NWO, research universities
• Collaboration style: Highest success rates, excellent coordination

**Collaboration Patterns:**
• **Franco-German Axis:** Strategic partnerships across all domains
• **Nordic Cooperation:** Denmark, Sweden, Finland - sustainability leaders
• **Mediterranean Alliance:** Italy, Spain, Greece - climate adaptation
• **Visegrad Plus:** Growing participation in digital transformation
• **Baltic Innovation:** Estonia, Latvia, Lithuania - digital pioneers

**Partnership Benefits:**
• **Shared costs and reduced risk** for large-scale research
• **Access to complementary expertise** and infrastructure
• **Larger market reach** and impact potential
• **Enhanced competitiveness** in proposal evaluation
• **Knowledge exchange** and researcher mobility

**Finding Partners:**
• **Partner Search Tool:** EU official platform for consortium building
• **Enterprise Europe Network:** 600+ organizations across Europe
• **National Contact Points:** Country-specific guidance and networking
• **EEN Brokerage Events:** Regular partnering opportunities
• **EURAXESS:** Researcher mobility and career development

**Success Tips for International Partnerships:**
• Start relationship building early (6+ months before deadlines)
• Ensure complementary rather than competing capabilities
• Establish clear roles, responsibilities, and IP agreements
• Consider language, cultural, and time zone factors
• Plan for regular face-to-face meetings and exchange visits

Would you like specific information about partnering with particular countries or finding collaborators in specific research areas?"""

        # Generic research management response
        else:
            return f"""🚀 **European Research Funding Overview**

**Your Query:** "{query}"

**I specialize in European research funding and innovation. Here's how I can help:**

**🔍 Funding Opportunities**
• **Horizon Europe:** €95.5B main research programme (2021-2027)
• **Digital Europe:** €7.5B digital transformation funding
• **LIFE Programme:** €5.4B environmental and climate action
• **Creative Europe:** Cultural and creative sectors support
• **Erasmus+:** Education, training, youth, and sport

**📊 Key Programs by Budget:**
• Global Challenges & Industrial Competitiveness: €53.5B
• Excellent Science (ERC, MSCA): €25.8B
• Innovative Europe (EIC, EIT): €13.6B
• Widening Participation: €2.1B

**💡 Strategic Guidance Available:**
• **Call identification** and opportunity matching
• **Proposal strategy** and consortium building
• **Budget planning** and cost optimization
• **Evaluation criteria** and success factors
• **Partnership facilitation** across Europe

**🌍 Coverage Areas:**
• All EU Member States + Associated Countries
• International cooperation opportunities
• Cross-border collaboration requirements
• National co-funding mechanisms

**📈 Success Metrics (2021-2023):**
• Overall success rate: 12-15%
• ERC grants: 13% (Starting), 9% (Advanced)
• MSCA Fellowships: 18% success rate
• Innovation Actions: typically 8-12%
• Some focused calls: up to 25%

**🎯 What would you like to explore?**
• "Find current AI funding opportunities"
• "How to build a competitive consortium"
• "What's the budget for climate research?"
• "Show me successful projects in my field"
• "Explain the evaluation process"

**I can provide detailed, actionable guidance on any aspect of European research funding!**

For current, specific opportunities, I can search live databases. What area interests you most?"""
