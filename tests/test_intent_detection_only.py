#!/usr/bin/env python3
"""
Simple test script to verify the simplified intent detection works correctly.
This tests just the intent detection logic without requiring full dependencies.
"""

def test_intent_detection():
    """Test the simplified intent detection logic."""
    
    print("🧪 TESTING SIMPLIFIED INTENT DETECTION")
    print("=" * 60)
    
    # Simulate the simplified intent detection logic
    def determine_user_intent_simplified(question: str):
        """FIXED simplified intent detection logic (matches the RAG service)."""
        question_lower = question.lower()
        
        # FIXED: More precise detection with proper priority ordering
        
        # 1. SEARCH_CALLS - Look for funding opportunities (HIGH PRIORITY)
        call_keywords = [
            'open call', 'available call', 'funding opportunity', 'opportunities',
            'what calls', 'which calls', 'any calls', 'some calls', 'list calls',
            'show me calls', 'find calls', 'search calls'
        ]
        
        # Strong call indicators
        if any(keyword in question_lower for keyword in call_keywords):
            return ("SEARCH_CALLS", 0.95)
        
        # Generic call/funding words - but check for procedural context
        generic_call_words = ['call', 'calls', 'funding', 'grant', 'grants', 'proposal', 'proposals']
        if any(word in question_lower for word in generic_call_words):
            # Check if this is asking ABOUT calls (search) vs asking HOW TO with calls (FAQ)
            procedural_context = ['how to', 'how do i', 'what is the process', 'what are the steps',
                                'eligibility criteria', 'application process', 'evaluation criteria',
                                'requirements for', 'how can i apply', 'evaluation process', 'process']
            
            if not any(proc in question_lower for proc in procedural_context):
                return ("SEARCH_CALLS", 0.9)
        
        # 2. SEARCH_PROJECTS - Look for research projects
        project_keywords = [
            'what projects', 'which projects', 'any projects', 'some projects',
            'show me projects', 'find projects', 'list projects', 'examples of projects',
            'funded projects', 'successful projects', 'research initiatives'
        ]
        
        # Strong project indicators
        if any(keyword in question_lower for keyword in project_keywords):
            return ("SEARCH_PROJECTS", 0.95)
        
        # Generic project words - but check for procedural context
        generic_project_words = ['project', 'projects', 'research', 'initiative', 'initiatives',
                               'who worked on', 'what has been done', 'previous work', 'existing solutions',
                               'case studies', 'examples', 'implemented', 'developed']
        
        if any(word in question_lower for word in generic_project_words):
            procedural_context = ['how to', 'how do i', 'what is the process', 'what are the steps',
                                'eligibility criteria', 'application process', 'evaluation criteria',
                                'requirements for', 'how can i apply']
            
            if not any(proc in question_lower for proc in procedural_context):
                return ("SEARCH_PROJECTS", 0.9)
        
        # 3. FAQ (default) - All procedural/policy questions
        return ("FAQ", 0.8)
    
    # Test cases for the 3 allowed functions
    test_cases = [
        # FAQ queries - should detect FAQ
        {
            'question': "What are the eligibility criteria for Horizon Europe?",
            'expected_intent': 'FAQ',
            'description': 'FAQ about eligibility'
        },
        {
            'question': "How do I apply to Horizon Europe funding?",
            'expected_intent': 'FAQ',
            'description': 'FAQ about application process'
        },
        {
            'question': "What is the evaluation process for EU grants?",
            'expected_intent': 'FAQ',
            'description': 'FAQ about evaluation'
        },
        {
            'question': "How to find and apply for relevant calls?",
            'expected_intent': 'FAQ',
            'description': 'FAQ about call procedures'
        },
        
        # Project search queries - should detect SEARCH_PROJECTS
        {
            'question': "What AI projects have been funded in healthcare?",
            'expected_intent': 'SEARCH_PROJECTS',
            'description': 'Looking for specific projects'
        },
        {
            'question': "Show me renewable energy research projects",
            'expected_intent': 'SEARCH_PROJECTS',
            'description': 'Research project search'
        },
        {
            'question': "Previous work on quantum computing initiatives",
            'expected_intent': 'SEARCH_PROJECTS',
            'description': 'Past initiatives search'
        },
        {
            'question': "Examples of successful AI projects",
            'expected_intent': 'SEARCH_PROJECTS',
            'description': 'Project examples'
        },
        
        # Call search queries - should detect SEARCH_CALLS
        {
            'question': "What calls are available for AI research?",
            'expected_intent': 'SEARCH_CALLS',
            'description': 'Available calls search'
        },
        {
            'question': "Show me open calls for climate change",
            'expected_intent': 'SEARCH_CALLS',
            'description': 'Open calls search'
        },
        {
            'question': "Are there any funding opportunities for green energy?",
            'expected_intent': 'SEARCH_CALLS',
            'description': 'Funding opportunities'
        },
        {
            'question': "I need funding for my AI healthcare project",
            'expected_intent': 'SEARCH_CALLS',
            'description': 'Looking for funding'
        },
        {
            'question': "What are some open calls related to clean energy?",
            'expected_intent': 'SEARCH_CALLS',
            'description': 'THE FAILING CASE - open calls search'
        },
        
        # Edge cases - mixed keywords
        {
            'question': "What are the eligibility criteria for project calls?",
            'expected_intent': 'FAQ',
            'description': 'FAQ overrides calls (eligibility criteria)'
        },
        {
            'question': "How do I apply for research grants?",
            'expected_intent': 'FAQ',
            'description': 'FAQ overrides grants (how do I apply)'
        }
    ]
    
    print(f"\n🔍 Testing {len(test_cases)} queries...")
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        question = test_case['question']
        expected_intent = test_case['expected_intent']
        description = test_case['description']
        
        print(f"\n📝 Test {i}: {description}")
        print(f"   Question: {question}")
        
        # Test intent detection
        intent, confidence = determine_user_intent_simplified(question)
        print(f"   🎯 Intent: {intent} (confidence: {confidence:.2f})")
        
        intent_correct = (intent == expected_intent)
        if intent_correct:
            print(f"   ✅ CORRECT (expected {expected_intent})")
        else:
            print(f"   ❌ WRONG (expected {expected_intent}, got {intent})")
        
        results.append({
            'question': question,
            'expected_intent': expected_intent,
            'actual_intent': intent,
            'intent_correct': intent_correct,
            'description': description
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INTENT DETECTION TEST RESULTS")
    print("=" * 60)
    
    intent_correct_count = sum(1 for r in results if r['intent_correct'])
    total_tests = len(results)
    
    print(f"Intent Detection: {intent_correct_count}/{total_tests} correct ({intent_correct_count/total_tests*100:.1f}%)")
    
    # Show results by category
    faq_tests = [r for r in results if r['expected_intent'] == 'FAQ']
    project_tests = [r for r in results if r['expected_intent'] == 'SEARCH_PROJECTS']
    call_tests = [r for r in results if r['expected_intent'] == 'SEARCH_CALLS']
    
    faq_correct = sum(1 for r in faq_tests if r['intent_correct'])
    project_correct = sum(1 for r in project_tests if r['intent_correct'])
    call_correct = sum(1 for r in call_tests if r['intent_correct'])
    
    print(f"\nBy category:")
    print(f"  FAQ: {faq_correct}/{len(faq_tests)} correct ({faq_correct/len(faq_tests)*100:.1f}%)")
    print(f"  SEARCH_PROJECTS: {project_correct}/{len(project_tests)} correct ({project_correct/len(project_tests)*100:.1f}%)")
    print(f"  SEARCH_CALLS: {call_correct}/{len(call_tests)} correct ({call_correct/len(call_tests)*100:.1f}%)")
    
    # Show failures
    failures = [r for r in results if not r['intent_correct']]
    if failures:
        print(f"\n❌ {len(failures)} FAILURES:")
        for f in failures:
            print(f"  • {f['description']}")
            print(f"    Question: {f['question']}")
            print(f"    Expected: {f['expected_intent']}, Got: {f['actual_intent']}")
    
    success = (intent_correct_count == total_tests)
    
    if success:
        print("\n🎉 ALL INTENT DETECTION TESTS PASSED!")
        print("\n✅ Intent detection correctly classifies queries into 3 categories:")
        print("   1. FAQ: Questions about procedures, policies, eligibility, how-to")
        print("   2. SEARCH_PROJECTS: Looking for existing/past research projects")
        print("   3. SEARCH_CALLS: Looking for funding opportunities/open calls")
    else:
        print(f"\n❌ {len(failures)} tests failed. Intent detection needs adjustment.")
    
    return success

if __name__ == "__main__":
    success = test_intent_detection()
    exit(0 if success else 1)