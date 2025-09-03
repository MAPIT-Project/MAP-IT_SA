#!/usr/bin/env python3
"""Generate many questions per capability and test the simplified intent detector.

This uses the same priority-based intent logic used in app/services/rag_service.py
but runs locally so it doesn't import the whole application (avoids external deps).
"""

import sys

def determine_user_intent(question: str):
    q = question.lower()
    # 0. Procedural/admin phrases -> FAQ (highest priority)
    procedural_phrases = [
        'how to', 'how do i', 'how do', 'how can i', 'how can i register', 'how can i apply',
        'how to register', 'how to apply', 'register', 'registration',
        'application deadline', 'application deadlines', 'deadline', 'deadlines',
        'eligibility', 'eligibility criteria', 'eligibility requirements',
        'application process', 'evaluation process', 'evaluation criteria',
        'how is the grant evaluated', 'evaluated', 'scored', 'scoring',
        'what documents', 'what supporting', 'supporting documents', 'supporting document',
        'documents required', 'required documents', 'submit', 'submit a proposal',
        'consortium requirements', 'consortium', 'budget', 'reporting', 'duration',
        'how long', 'who can be', 'who can', 'coordinator', 'requirements for',
        'ethic', 'ethics', 'ethics issues', 'ethics in', 'ethics issues in'
    ]
    if any(phrase in q for phrase in procedural_phrases):
        return ("FAQ", 0.95)

    # 1. SEARCH_CALLS - funding opportunities
    call_keywords = [
        'open call', 'available call', 'funding opportunity', 'opportunities',
        'what calls', 'which calls', 'any calls', 'some calls', 'list calls',
        'show me calls', 'find calls', 'search calls', 'open grants', 'funding opportunities'
    ]
    if any(keyword in q for keyword in call_keywords):
        return ("SEARCH_CALLS", 0.95)

    generic_call_words = ['call', 'calls', 'funding', 'grant', 'grants', 'proposal', 'proposals']
    if any(word in q for word in generic_call_words):
        return ("SEARCH_CALLS", 0.90)

    # 2. SEARCH_PROJECTS - research/projects
    project_keywords = [
        'what projects', 'which projects', 'any projects', 'some projects',
        'show me projects', 'find projects', 'list projects', 'examples of projects',
        'funded projects', 'successful projects', 'research initiatives'
    ]
    if any(keyword in q for keyword in project_keywords):
        return ("SEARCH_PROJECTS", 0.95)

    generic_project_words = [
        'project', 'projects', 'research', 'initiative', 'initiatives',
        'who worked on', 'what has been done', 'previous work', 'existing solutions',
        'case studies', 'examples', 'implemented', 'developed'
    ]
    if any(word in q for word in generic_project_words):
        return ("SEARCH_PROJECTS", 0.90)

    # Fallback safe -> FAQ
    return ("FAQ", 0.80)


def make_question_sets():
    calls_questions = [
        "What are some open calls related to clean energy?",
        "Show me open calls for climate change",
        "What calls are available for AI research?",
        "Are there any funding opportunities for green energy?",
        "List calls for energy storage",
        "Find calls about hydrogen projects",
        "Any calls for battery technology?",
        "Open grants for renewable energy research?",
        "Which calls are currently open for clean energy pilots?",
        "What funding opportunities exist for solar power R&D?",
        "Show me calls for demonstration projects in energy",
        "Are there calls for large-scale energy demonstrators?"
    ]
    
    projects_questions = [
        "What AI projects have been funded in healthcare?",
        "Show me renewable energy research projects",
        "Previous work on quantum computing initiatives",
        "Examples of successful AI projects in transport",
        "Which projects focus on battery storage technology?",
        "List projects about hydrogen energy",
        "What research initiatives exist on energy efficiency?",
        "Find projects related to smart grids",
        "Who worked on EU projects for offshore wind?",
        "Provide examples of climate adaptation research projects",
        "What projects explored waste-to-energy solutions?",
        "Show projects on grid-scale storage demonstrations"
    ]
    
    faq_questions = [
        "What are the eligibility criteria for Horizon Europe?",
        "How do I apply to Horizon Europe funding?",
        "What is the evaluation process for EU grants?",
        "How to find and apply for relevant calls?",
        "What are the application deadlines for Horizon Europe calls?",
        "What are the consortium requirements for Horizon Europe?",
        "How can I register on the EU Funding & Tenders Portal?",
        "What documents are required to submit a proposal?",
        "How is the grant evaluated and scored?",
        "What are the rules for project budget and reporting?",
        "What is the duration of typical Horizon Europe projects?",
        "Who can be a project coordinator in EU grants?"
    ]
    
    tests = []
    for q in calls_questions:
        tests.append({'question': q, 'expected': 'SEARCH_CALLS'})
    for q in projects_questions:
        tests.append({'question': q, 'expected': 'SEARCH_PROJECTS'})
    for q in faq_questions:
        tests.append({'question': q, 'expected': 'FAQ'})
    return tests


def run_tests():
    tests = make_question_sets()
    total = len(tests)
    correct = 0
    details = []
    
    print("🧪 Running intent classification tests for generated questions")
    print("=" * 80)
    
    for i, t in enumerate(tests, 1):
        q = t['question']
        expected = t['expected']
        intent, conf = determine_user_intent(q)
        ok = (intent == expected)
        status = "PASS" if ok else "FAIL"
        if ok:
            correct += 1
        details.append({
            'question': q,
            'expected': expected,
            'got': intent,
            'confidence': conf,
            'status': status
        })
        print(f"{i:02d}. [{status}] Expected={expected:<15} Got={intent:<15} (conf={conf:.2f})")
        print(f"     Q: {q}")
    
    print("\n" + "=" * 80)
    print(f"Summary: {correct}/{total} correct ({correct/total*100:.1f}%)")
    
    fails = [d for d in details if d['status'] == 'FAIL']
    if fails:
        print("\nFailures:")
        for f in fails:
            print(f" - Q: {f['question']}")
            print(f"   Expected: {f['expected']}, Got: {f['got']}, Confidence: {f['confidence']}")
    else:
        print("\nAll generated questions classified correctly.")
    
    # Exit code: 0 if all correct, else 2
    sys.exit(0 if correct == total else 2)


if __name__ == "__main__":
    run_tests()
