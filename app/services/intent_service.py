from typing import Tuple
import os


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
            'deadline', 'topic', 'tenders', 'funding & tenders', 'funding and tenders'
        ]
        if any(c in q for c in call_triggers) or ("open" in q and "call" in q):
            return ("SEARCH_CALLS", 0.93)

        project_triggers = ['project', 'projects', 'acronym', 'rcn', 'case study']
        # Strengthen calls vs projects: if generic call/funding words + domain term exist, prefer SEARCH_CALLS
        generic_call_words = ['call', 'calls', 'funding', 'grant', 'grants', 'proposal', 'proposals']
        domain_terms = ['ai', 'artificial intelligence', 'energy', 'clean energy', 'renewable', 'digital', 'health', 'smes', 'hydrogen', 'battery', 'digital transformation']
        if any(w in q for w in generic_call_words) and any(t in q for t in domain_terms):
            return ("SEARCH_CALLS", 0.9)

        if any(p in q for p in project_triggers):
            return ("SEARCH_PROJECTS", 0.9)

        # LLM classification with strict 2-line output
        provider = (os.getenv("DEFAULT_AI_PROVIDER") or "gemini").lower()
        prompt = f"""You classify a single user question into exactly one label:

Labels:
- FAQ: procedural/how-to/eligibility/where-to-find
- SEARCH_PROJECTS: existing/past projects, examples, case studies
- SEARCH_CALLS: open calls/funding opportunities/topics/deadlines

Rules:
- Output EXACTLY 2 lines, no extra text.
- Line 1: CLASSIFICATION: <FAQ|SEARCH_PROJECTS|SEARCH_CALLS>
- Line 2: CONFIDENCE: <0.0-1.0>
- Prefer FAQ for procedural wording; prefer SEARCH_CALLS when asking for open calls/opportunities.

Question: "{question}"""

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


