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
            if hasattr(tool_result, 'success') and tool_result.success:
                if tool_name == 'eu_portal_search':
                    # Format EU portal call search results
                    formatted_calls = self._format_eu_calls(tool_result.result)
                    formatted_parts.append(formatted_calls)
                    
                elif tool_name == 'search_cordis_projects':
                    # Format CORDIS project search results
                    formatted_projects = self._format_cordis_projects(tool_result.result)
                    formatted_parts.append(formatted_projects)
                    
                else:
                    # Generic tool result formatting
                    formatted_generic = self._format_generic_tool_result(tool_name, tool_result.result)
                    formatted_parts.append(formatted_generic)
        
        return "\n\n".join(formatted_parts) if formatted_parts else "No results found."
    
    def _format_eu_calls(self, call_data: Dict[str, Any]) -> str:
        """
        Format EU funding calls with beautiful styling.
        Uses the excellent formatting from rag_service._generate_calls_answer
        """
        calls = call_data.get('calls', [])
        query = call_data.get('query', 'funding opportunities')
        
        if not calls:
            return self._format_no_calls_found(query)
        
        # Generate structured response with beautiful formatting
        answer_parts = [
            f"I found **{len(calls)} funding opportunities** for your query about '{query}':",
            "",
            "⚠️ **IMPORTANT**: These are REAL funding opportunities from official EU sources.",
            ""
        ]
        
        # Sort calls by status and deadline
        sorted_calls = self._sort_calls_by_priority(calls)
        
        for i, call in enumerate(sorted_calls, 1):
            call_summary = self._format_single_call(i, call)
            answer_parts.append(call_summary)
            answer_parts.append("")  # Empty line between calls
        
        # Add helpful footer
        answer_parts.extend(self._get_calls_footer())
        
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
        
        # Format deadline nicely with urgency indicators
        deadline_text = self._format_deadline(deadline)
        
        # Build call summary with emojis and formatting
        call_summary = f"**{index}. {title}**"
        
        if identifier != 'N/A':
            call_summary += f"\n📋 **Call ID:** {identifier}"
        
        if status != 'Unknown':
            status_emoji = self._get_status_emoji(status)
            call_summary += f"\n{status_emoji} **Status:** {status}"
        
        if deadline_text != 'Not specified':
            call_summary += f"\n⏰ **Application Deadline:** {deadline_text}"
        
        if programme != 'Not specified':
            call_summary += f"\n🏛️ **Programme:** {programme}"
        
        # Add description (truncated)
        if description and description != 'No description available':
            desc_preview = description[:300] + ('...' if len(description) > 300 else '')
            call_summary += f"\n\n**Call Description:**\n{desc_preview}"
        
        # Add link with proper emoji
        if url:
            call_summary += f"\n\n🔗 **Apply Here:** {url}"
        else:
            call_summary += f"\n\n🔗 **Find on Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
        
        return call_summary
    
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
    
    def _get_calls_footer(self) -> List[str]:
        """Get helpful footer information for funding calls."""
        return [
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
            "",
            "🔍 **Need more specific calls?** Try refining your search with more specific keywords, research areas, or check back regularly as new calls are published throughout the year."
        ]
    
    def _format_no_calls_found(self, query: str) -> str:
        """Format response when no calls are found."""
        current_year = datetime.now().year
        
        # Extract search terms for verification URL and better messaging
        search_terms = query.lower()
        for phrase in ["what are some open calls for", "what are some open calls about", "open calls for", "open calls about", "calls for", "calls about"]:
            search_terms = search_terms.replace(phrase, "").strip()
        search_terms = search_terms.replace("?", "").strip()
        
        if not search_terms:
            search_terms = "energy"
        
        verification_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={search_terms.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
        
        # Provide topic-specific guidance
        topic_guidance = self._get_topic_specific_guidance(search_terms)
        
        return f"""**🔍 No Currently Open Calls Found**

I searched the EU Funding & Tenders Portal but found **no currently open calls** for "{query}" right now in {current_year}.

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

{topic_guidance}"""
    
    def _format_cordis_projects(self, project_data: Dict[str, Any]) -> str:
        """Format CORDIS project search results."""
        answer = project_data.get('answer', '')
        projects_found = project_data.get('projects_found', 0)
        data_source = project_data.get('data_source', 'CORDIS')
        
        if not answer:
            return "No project information found."
        
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
                if key in ['error', 'success', 'tool_name']:
                    continue  # Skip metadata
                formatted_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        else:
            formatted_parts.append(str(result))
        
        return "\n".join(formatted_parts)
    
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
