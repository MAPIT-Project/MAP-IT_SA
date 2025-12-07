import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import DictCursor
import os


logger = logging.getLogger(__name__)
@dataclass
class ProjectReference:
    """Reference to a project discussed in conversation"""
    project_id: str
    acronym: str
    title: str
    position_in_results: int
    mentioned_at: str
    framework_programme: str = None
    
@dataclass
class ConversationContext:
    """Complete context for a conversation"""
    conversation_id: int
    user_id: int
    messages: List[Dict[str, Any]]
    discussed_projects: List[ProjectReference]
    mentioned_organizations: List[str]
    topics_of_interest: List[str]
    last_search_results: List[Dict[str, Any]]
    last_query_type: str
    follow_up_expected: bool
    
    def to_dict(self):
        return {
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'message_count': len(self.messages),
            'projects_discussed': len(self.discussed_projects),
            'current_topics': self.topics_of_interest[:3] if self.topics_of_interest else []
        }
    
    def get_recent_messages(self, count: int = 5) -> List[Dict]:
        """Get recent messages for prompt context"""
        return self.messages[-count:] if self.messages else []
    
    def find_project_by_reference(self, reference: str) -> Optional[ProjectReference]:
        """Find a project by various references (ordinal, name, pronoun)"""
        reference_lower = reference.lower()
        
        # Check for ordinal references
        ordinal_map = {
            'first': 0, '1st': 0,
            'second': 1, '2nd': 1,
            'third': 2, '3rd': 2,
            'fourth': 3, '4th': 3,
            'fifth': 4, '5th': 4,
            'last': -1, 'latest': -1
        }
        
        for ordinal, index in ordinal_map.items():
            if ordinal in reference_lower:
                if 0 <= index < len(self.discussed_projects):
                    return self.discussed_projects[index]
                elif index == -1 and self.discussed_projects:
                    return self.discussed_projects[-1]
        
        # Check for acronym or title match
        for project in self.discussed_projects:
            if (project.acronym.lower() in reference_lower or 
                reference_lower in project.title.lower()):
                return project
        
        # Check for "it", "that", "the project" - return most recent
        if reference_lower in ['it', 'that', 'the project', 'this project']:
            return self.discussed_projects[-1] if self.discussed_projects else None
        
        return None


class ConversationContextService:
    """Service for managing conversation context"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.context_cache = {}  # Simple in-memory cache
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def load_context(self, conversation_id: int) -> ConversationContext:
        """Load conversation context from database"""
        
        # Check cache first
        if conversation_id in self.context_cache:
            cached_context, timestamp = self.context_cache[conversation_id]
            if datetime.now() - timestamp < timedelta(minutes=30):
                return cached_context
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        try:
            # Get conversation info
            cursor.execute("""
                SELECT c.*,
                       COUNT(m.id) as message_count
                FROM conversation c
                LEFT JOIN message m ON c.id = m."conversation_id"
                WHERE c.id = %s
                GROUP BY c.id
            """, (conversation_id,))
            
            conv_data = cursor.fetchone()
            if not conv_data:
                # Create a minimal context for new conversations
                return ConversationContext(
                    conversation_id=conversation_id,
                    user_id=0,
                    messages=[],
                    discussed_projects=[],
                    mentioned_organizations=[],
                    topics_of_interest=[],
                    last_search_results=[],
                    last_query_type='UNKNOWN',
                    follow_up_expected=False
                )
            
            # Get recent messages
            cursor.execute("""
                SELECT id, text, sender, "created_at"
                FROM message
                WHERE "conversation_id" = %s
                ORDER BY "created_at" DESC
                LIMIT 20
            """, (conversation_id,))
            
            messages = [dict(row) for row in cursor.fetchall()]
            messages.reverse()  # Put in chronological order
            
            # Extract context from messages
            context = self._extract_context_from_messages(
                conversation_id,
                conv_data['user_id'],
                messages
            )
            
            # Cache the context
            self.context_cache[conversation_id] = (context, datetime.now())
            
            return context
            
        finally:
            cursor.close()
            conn.close()
    
    def _extract_context_from_messages(
        self, 
        conversation_id: int,
        user_id: int,
        messages: List[Dict]
    ) -> ConversationContext:
        """Extract context information from message history"""
        
        discussed_projects = []
        mentioned_organizations = set()
        topics = set()
        last_search_results = []
        last_query_type = None
        
        for msg in messages:
            text = msg['text']
            
            # Extract project mentions (simple pattern matching)
            # Look for patterns like "project ACRONYM" or "ACRONYM project"
            project_pattern = r'\b([A-Z]{3,}(?:-[A-Z]+)*)\b'
            potential_acronyms = re.findall(project_pattern, text)
            
            for acronym in potential_acronyms:
                # Check if this looks like a project acronym
                if len(acronym) >= 3 and acronym not in ['API', 'SQL', 'JSON', 'HTTP', 'CORDIS', 'RAG']:
                    # Try to extract more info from surrounding text
                    title_match = re.search(
                        rf'{acronym}[:\s-]+([^.!?\n]+)',
                        text
                    )
                    title = title_match.group(1) if title_match else acronym
                    
                    # Check if we already have this project
                    if not any(p.acronym == acronym for p in discussed_projects):
                        discussed_projects.append(ProjectReference(
                            project_id=acronym,
                            acronym=acronym,
                            title=title,
                            position_in_results=len(discussed_projects),
                            mentioned_at=msg['created_at'].isoformat() if isinstance(msg['created_at'], datetime) else str(msg['created_at'])
                        ))
            
            # Extract organization mentions
            org_pattern = r'(?:coordinated by|led by|participant[s]?:?)\s+([A-Z][A-Za-z\s&]+(?:University|Institute|Centre|Center|GmbH|Ltd|Inc|Corporation|Company|Foundation))'
            orgs = re.findall(org_pattern, text, re.IGNORECASE)
            mentioned_organizations.update(orgs)
            
            # Extract topics (simple keyword extraction)
            topic_keywords = ['nuclear', 'energy', 'renewable', 'solar', 'wind', 
                            'research', 'innovation', 'technology', 'climate',
                            'environment', 'health', 'digital', 'AI', 'quantum']
            
            for keyword in topic_keywords:
                if keyword.lower() in text.lower():
                    topics.add(keyword)
            
            # Check for query type indicators
            if 'SEARCH_PROJECTS' in text or 'projects found' in text:
                last_query_type = 'SEARCH_PROJECTS'
            elif 'SEARCH_CALLS' in text or 'calls found' in text:
                last_query_type = 'SEARCH_CALLS'
            elif 'FAQ' in text:
                last_query_type = 'FAQ'
        
        return ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            discussed_projects=discussed_projects,
            mentioned_organizations=list(mentioned_organizations),
            topics_of_interest=list(topics),
            last_search_results=last_search_results,
            last_query_type=last_query_type or 'UNKNOWN',
            follow_up_expected=True if discussed_projects else False
        )
    
    def resolve_references(self, message: str, context: ConversationContext) -> Tuple[str, bool]:
        """
        Resolve references in user message to concrete entities.
        Returns (resolved_message, needs_detailed_lookup)
        """
        
        resolved = message
        needs_detailed_lookup = False
        
        # Pattern for "tell me more about X"
        more_pattern = r'tell me (?:more )?about (the )?(first|second|third|fourth|fifth|last|latest|it|that|this)( one| project)?'
        match = re.search(more_pattern, resolved, re.IGNORECASE)
        
        if match:
            reference = match.group(2)
            project = context.find_project_by_reference(reference)
            if project:
                resolved = resolved.replace(
                    match.group(0),
                    f'tell me more about {project.acronym} ({project.title})'
                )
                needs_detailed_lookup = True  # This requires detailed project data
        
        # Pattern for "what about its X" or "what is the X of Y"
        its_pattern = r'what (?:about )?(?:its|the) (\w+)'
        match = re.search(its_pattern, resolved, re.IGNORECASE)
        
        if match and context.discussed_projects:
            last_project = context.discussed_projects[-1]
            attribute = match.group(1).lower()
            
            if attribute in ['budget', 'cost', 'funding']:
                resolved = f"What is the budget of {last_project.acronym} project?"
                needs_detailed_lookup = True
            elif attribute in ['consortium', 'partners', 'participants']:
                resolved = f"What is the consortium composition of {last_project.acronym} project?"
                needs_detailed_lookup = True
            else:
                resolved = resolved.replace(
                    'its', f"{last_project.acronym}'s"
                ).replace(
                    'the project', last_project.acronym
                )
                needs_detailed_lookup = True
        
        # Direct budget questions
        budget_pattern = r'what (?:is )?(?:the )?budget (?:of )?(\w+)'
        match = re.search(budget_pattern, resolved, re.IGNORECASE)
        if match:
            needs_detailed_lookup = True
        
        # Pattern for "show me similar projects"
        if 'similar' in resolved.lower() and context.discussed_projects:
            last_project = context.discussed_projects[-1]
            resolved = f"Find projects similar to {last_project.acronym} in the {' '.join(context.topics_of_interest)} domain"
        
        return resolved, needs_detailed_lookup
    
    def update_context(self, conversation_id: int, new_message: Dict, response: Dict):
        """Update context with new information"""
        
        # Get or create context
        if conversation_id in self.context_cache:
            context, _ = self.context_cache[conversation_id]
        else:
            # Create new context if not exists
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=0,
                messages=[],
                discussed_projects=[],
                mentioned_organizations=[],
                topics_of_interest=[],
                last_search_results=[],
                last_query_type='UNKNOWN',
                follow_up_expected=False
            )
        
        # Add new message to history
        context.messages.append(new_message)
        
        # Extract projects from response - IMPROVED EXTRACTION
        if 'answer' in response:
            answer = response['answer']
            
            # Extract projects using multiple patterns
            projects_extracted = []
            
            # Pattern 1: **ACRONYM: Full Project Title**
            pattern1 = re.findall(r'\*\*([A-Z][A-Z0-9-]+):\s*([^*\n]+)\*\*', answer)
            for i, (acronym, title) in enumerate(pattern1):
                if len(acronym) >= 3 and acronym not in ['HORIZON', 'EURATOM', 'RIA', 'CSA', 'FOCUS', 'DURATION', 'PROGRAMME', 'CONSORTIUM', 'CORDIS']:
                    projects_extracted.append({
                        'position': i,
                        'title': title.strip(),
                        'acronym': acronym.strip(),
                        'id': acronym.strip()
                    })
            
            # Pattern 2: **Project Name (ACRONYM)**
            if not projects_extracted:
                pattern2 = re.findall(r'\*\*([^*]+?)\s*\(([A-Z][A-Z0-9-]+)\)\*\*', answer)
                for i, (title, acronym) in enumerate(pattern2):
                    if len(acronym) >= 3:
                        projects_extracted.append({
                            'position': i,
                            'title': title.strip(),
                            'acronym': acronym.strip(),
                            'id': acronym.strip()
                        })
            
            # Pattern 3: Bullet points with **ACRONYM**
            if not projects_extracted:
                # Look for bullet points like "*   **DISTENDER: ...**"
                pattern3 = re.findall(r'\*\s+\*\*([A-Z][A-Z0-9-]+):\s*([^*\n]+)\*\*', answer)
                for i, (acronym, title) in enumerate(pattern3):
                    if len(acronym) >= 3 and acronym not in ['HORIZON', 'EURATOM', 'RIA', 'CSA', 'FOCUS', 'DURATION', 'PROGRAMME', 'CONSORTIUM', 'CORDIS']:
                        projects_extracted.append({
                            'position': i,
                            'title': title.strip(),
                            'acronym': acronym.strip(),
                            'id': acronym.strip()
                        })
            
            # Pattern 4: **ACRONYM** standalone
            if not projects_extracted:
                pattern4 = re.findall(r'\*\*([A-Z][A-Z0-9-]+)\*\*', answer)
                for i, acronym in enumerate(pattern4):
                    if len(acronym) >= 3 and acronym not in ['HORIZON', 'EURATOM', 'RIA', 'CSA', 'FOCUS', 'DURATION', 'PROGRAMME', 'CONSORTIUM', 'CORDIS']:
                        projects_extracted.append({
                            'position': i,
                            'title': acronym,
                            'acronym': acronym,
                            'id': acronym
                        })
            
            # Pattern 5: Look for numbered project sections
            if not projects_extracted:
                pattern5 = re.findall(r'\*\*(\d+)\.\s*([^*\n]+)\*\*', answer)
                for i, (num, title) in enumerate(pattern5):
                    # Try to extract acronym from title
                    acronym_match = re.search(r'\(([A-Z][A-Z0-9-]+)\)', title)
                    acronym = acronym_match.group(1) if acronym_match else f"PROJECT_{num}"
                    
                    projects_extracted.append({
                        'position': int(num) - 1,
                        'title': title.strip(),
                        'acronym': acronym,
                        'id': acronym
                    })
            
            # Add extracted projects to context
            for proj_data in projects_extracted:
                # Check if we already have this project
                if not any(p.acronym == proj_data['acronym'] for p in context.discussed_projects):
                    context.discussed_projects.append(ProjectReference(
                        project_id=proj_data['id'],
                        acronym=proj_data['acronym'],
                        title=proj_data['title'],
                        position_in_results=proj_data['position'],
                        mentioned_at=datetime.now().isoformat(),
                        framework_programme='N/A'
                    ))
            
            logger.info(f"🔍 Extracted {len(projects_extracted)} projects from response")
            for proj in projects_extracted:
                logger.info(f"   - {proj['position'] + 1}. {proj['acronym']}: {proj['title'][:50]}...")
        
        # Update cache
        self.context_cache[conversation_id] = (context, datetime.now())
    
    def generate_follow_up_suggestions(
        self, 
        context: ConversationContext,
        last_response: Dict
    ) -> List[str]:
        """Generate contextual follow-up suggestions"""
        
        suggestions = []
        
        if context.discussed_projects:
            last_project = context.discussed_projects[-1]
            
            # Project-specific suggestions
            suggestions.extend([
                f"Tell me more about {last_project.acronym}'s consortium partners",
                f"What is the budget of {last_project.acronym}?",
                f"Find similar projects to {last_project.acronym}"
            ])
            
            # Framework-specific suggestions
            if last_project.framework_programme and last_project.framework_programme != 'N/A':
                suggestions.append(
                    f"Show me other {last_project.framework_programme} projects"
                )
        
        # Topic-based suggestions
        if context.topics_of_interest:
            topic = context.topics_of_interest[0]
            suggestions.append(f"Find more recent {topic} projects")
        
        # General suggestions based on last query type
        if context.last_query_type == 'SEARCH_PROJECTS':
            suggestions.extend([
                "Show me projects from different countries",
                "Find projects with larger consortiums",
                "What are the most recent projects in this area?"
            ])
        
        return suggestions[:4]  # Return top 4 suggestions