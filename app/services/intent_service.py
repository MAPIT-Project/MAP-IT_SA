from typing import Tuple, Any
import os
import re


class IntentService:
    """Centralized intent detection with deterministic prompt and minimal overrides."""

    @staticmethod
    def determine_intent(question: str) -> Tuple[str, float]:
        # High-precision overrides
        q = (question or "").strip().lower()
        if not q:
            return ("FAQ", 0.5)

        procedural = [
            'how to', 'how do i', 'how can i', 'where can i find', 'where to find',
            'eligibility', 'application process', 'documents required', 'supporting documents',
            'ethics', 'guidelines', 'register on the portal', 'how to apply'
        ]
        if any(p in q for p in procedural):
            return ("FAQ", 0.92)

        call_triggers = [
            'open calls', 'calls for proposals', 'funding opportunities', 'grant opportunities',
            'deadline', 'topic', 'tenders', 'funding & tenders', 'funding and tenders',
            'calls about', 'calls for', 'calls related to', 'available calls', 'current calls'
        ]
        if any(c in q for c in call_triggers) or ("open" in q and "call" in q):
            return ("SEARCH_CALLS", 0.93)

        # Single domain terms should be treated as project searches
        single_domain_terms = [
            'energy', 'ai', 'artificial intelligence', 'healthcare', 'quantum', 'nuclear',
            'renewable', 'sustainable', 'climate', 'digital', 'robotics', 'biotechnology',
            'nanotechnology', 'materials', 'transport', 'mobility', 'agriculture', 'food',
            'water', 'environment', 'space', 'security', 'health', 'medical', 'pharma',
            'chemistry', 'physics', 'engineering', 'technology', 'innovation', 'research'
        ]

        # Check if query is a single domain term (1-3 words, no procedural keywords)
        query_words = q.split()
        is_single_domain_query = (
            len(query_words) <= 3 and
            not any(p in q for p in procedural) and
            not any(c in q for c in call_triggers) and
            any(term in q for term in single_domain_terms)
        )

        if is_single_domain_query:
            return ("SEARCH_PROJECTS", 0.95)

        project_triggers = ['project', 'projects', 'acronym', 'rcn', 'case study']
        # Strengthen calls vs projects: if generic call/funding words + domain term exist, prefer SEARCH_CALLS
        generic_call_words = ['call', 'calls', 'funding', 'grant', 'grants', 'proposal', 'proposals']
        domain_terms = ['ai', 'artificial intelligence', 'energy', 'clean energy', 'renewable', 'digital', 'health', 'smes', 'hydrogen', 'battery', 'digital transformation']
        if any(w in q for w in generic_call_words) and any(t in q for t in domain_terms):
            return ("SEARCH_CALLS", 0.9)

        if any(p in q for p in project_triggers):
            return ("SEARCH_PROJECTS", 0.9)

        # Advanced AI classification with detailed context and examples
        provider = (os.getenv("DEFAULT_AI_PROVIDER") or "gemini").lower()
        prompt = f"""You are an expert intent classifier for Horizon Europe research funding queries. Analyze the user's question and determine the most appropriate intent category.

INTENT CATEGORIES:

1. FAQ - Procedural/How-to Questions:
   - Questions about application processes, eligibility, documentation, guidelines
   - "How to apply for funding", "What documents are required", "Eligibility criteria"
   - Portal registration, submission procedures, evaluation processes
   - Budget rules, consortium requirements, ethical guidelines

2. SEARCH_PROJECTS - Existing/Completed Projects:
   - Questions about specific research projects, case studies, examples
   - "Find projects about nuclear energy", "Show me AI research projects"
   - Project details, consortium partners, budgets, outcomes
   - "What projects exist in quantum computing", "Case studies of successful projects"
   - Looking for inspiration, best practices, existing research
   - Single domain terms like "energy", "AI", "healthcare" → SEARCH_PROJECTS (not FAQ)

3. SEARCH_CALLS - Open Funding Opportunities:
   - Questions about current calls for proposals, funding opportunities
   - "Open calls for AI research", "Funding deadlines this month"
   - Topics, deadlines, budget allocations, application windows
   - "What opportunities exist for renewable energy", "Current tenders"
   - Future planning, upcoming deadlines, available funding

ANALYSIS FRAMEWORK:

1. FIRST, analyze the question's primary goal:
   - Is the user seeking information about HOW to do something? → FAQ
   - Is the user looking for EXAMPLES of existing work? → SEARCH_PROJECTS
   - Is the user looking for OPPORTUNITIES to apply? → SEARCH_CALLS

2. CONSIDER KEYWORDS AND CONTEXT:
   - "how to", "process", "guidelines", "requirements" → FAQ
   - "projects", "examples", "case studies", "show me" → SEARCH_PROJECTS
   - "calls", "opportunities", "deadlines", "funding" → SEARCH_CALLS
   - Single domain words like "energy", "AI", "healthcare" → SEARCH_PROJECTS (not FAQ)

3. CONFIDENCE SCORING:
   - 0.9-1.0: Clear, unambiguous intent with strong keyword signals
   - 0.7-0.89: Some ambiguity but strong leaning toward one category
   - 0.5-0.69: Moderate ambiguity, could go either way
   - Below 0.5: Highly ambiguous, default to FAQ

4. EDGE CASES:
   - If question contains both project and call keywords, prioritize based on primary verb:
     "Find projects with open calls" → SEARCH_PROJECTS (primary: find projects)
     "Show me calls with project examples" → SEARCH_CALLS (primary: show me calls)
   - Generic questions without clear intent: "Tell me about Horizon Europe" → FAQ
   - Single domain terms: "energy", "AI", "quantum" → SEARCH_PROJECTS (users want project examples)

OUTPUT FORMAT:
CLASSIFICATION: <FAQ|SEARCH_PROJECTS|SEARCH_CALLS>
CONFIDENCE: <0.0-1.0>

QUESTION: "{question}"

ANALYZE THOROUGHLY AND PROVIDE YOUR CLASSIFICATION:"""

        try:
            response_text = None
            if provider == "openai" and os.getenv("OPENAI_API_KEY"):
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    resp = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                    )
                    response_text = resp.choices[0].message.content
                except Exception:
                    response_text = None
            elif os.getenv("GEMINI_API_KEY"):
                try:
                    from google import genai as google_genai_sdk
                    from google.genai import types
                    client = google_genai_sdk.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
                    gen_config = types.GenerateContentConfig(temperature=0.0)
                    resp = client.models.generate_content(
                        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
                        contents=contents,
                        config=gen_config
                    )
                    response_text = resp.text
                except Exception:
                    response_text = None

            intent, confidence = "FAQ", 0.5
            if response_text:
                lines = [l.strip() for l in response_text.strip().split('\n') if l.strip()][:2]
                for line in lines:
                    if line.startswith("CLASSIFICATION:"):
                        label = line.replace("CLASSIFICATION:", "").strip()
                        if label in ("FAQ", "SEARCH_PROJECTS", "SEARCH_CALLS"):
                            intent = label
                    elif line.startswith("CONFIDENCE:"):
                        try:
                            val = float(line.replace("CONFIDENCE:", "").strip())
                            confidence = max(0.0, min(1.0, val))
                        except Exception:
                            confidence = 0.5
            return (intent, confidence)
        except Exception:
            return ("FAQ", 0.5)

    
    @staticmethod
    def determine_intent_with_context(question: str, context: Any) -> Tuple[str, float]:
        """
        Determine intent using conversation context for improved accuracy.
        context should be a ConversationContext object or similar.
        """
        # First try high-precision overrides
        intent, confidence = IntentService.determine_intent(question)
        
        # Use context to refine intent detection
        if hasattr(context, 'discussed_projects') and context.discussed_projects:
            # If user is asking about previously discussed projects, prefer SEARCH_PROJECTS
            project_patterns = [
                r'tell me more about',
                r'what about',
                r'what is',
                r'budget',
                r'consortium',
                r'partners',
                r'similar'
            ]
            
            if any(re.search(pattern, question.lower()) for pattern in project_patterns):
                # Check if this could be about a specific project
                for project in context.discussed_projects:
                    if (project.acronym.lower() in question.lower() or
                        any(word in question.lower() for word in project.title.lower().split())):
                        return ("SEARCH_PROJECTS", max(confidence, 0.95))
        
        if hasattr(context, 'last_query_type'):
            # If last query was about projects and this seems related, prefer projects
            if (context.last_query_type == 'SEARCH_PROJECTS' and
                any(word in question.lower() for word in ['more', 'another', 'similar', 'other'])):
                return ("SEARCH_PROJECTS", max(confidence, 0.85))
            
            # If last query was about calls and this seems related, prefer calls
            if (context.last_query_type == 'SEARCH_CALLS' and
                any(word in question.lower() for word in ['more', 'another', 'similar', 'other'])):
                return ("SEARCH_CALLS", max(confidence, 0.85))
        
        if hasattr(context, 'topics_of_interest') and context.topics_of_interest:
            # If question contains topics of interest, prefer SEARCH_PROJECTS
            for topic in context.topics_of_interest:
                if topic.lower() in question.lower():
                    return ("SEARCH_PROJECTS", max(confidence, 0.8))
        
        return (intent, confidence)

