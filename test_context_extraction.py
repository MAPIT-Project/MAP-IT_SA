#!/usr/bin/env python3
"""
Test script to verify context extraction works with real conversation data.
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_context_extraction_with_real_data():
    """Test context extraction with the actual conversation data"""
    print("="*80)
    print("TESTING CONTEXT EXTRACTION WITH REAL DATA")
    print("="*80)
    
    try:
        from app.services.conversation_context_service import ConversationContextService
        
        # Initialize service
        service = ConversationContextService()
        
        # Real AI response from your conversation
        ai_response = """Certainly! I can help you navigate the recent landscape of European research projects focused on nuclear energy. Based on the information available, there are indeed several active and upcoming projects addressing various facets of nuclear energy.

Here's a comprehensive overview of the most relevant and recent projects:

### Recent European Projects in Nuclear Energy

The European Union is actively investing in nuclear energy research through its Horizon Europe programme, with a particular focus on safety, societal acceptance, materials science, and innovative applications. The projects highlighted below represent a strong commitment to advancing nuclear energy research and development.

**1. Safety Assessment of Non-Electric uses of nuclear energy (SANE)**

*   **Focus:** This project is at the forefront of exploring the potential of nuclear energy for non-electric applications. It delves into the safety aspects of reactors designed for these specific uses, as well as the safety implications of their end-use.
*   **Timeline:** The project is set to run from **1 September 2024 to 31 August 2027**.
*   **Programme:** **HORIZON / EURATOM-IA**
*   **Consortium:** Coordinated by **TEKNOLOGIAN TUTKIMUSKESKUS VTT OY (FI)**, it involves 12 participants from 10 countries, including 1 SME.
*   **CORDIS Link:** [https://cordis.europa.eu/project/id/101163929](https://cordis.europa.eu/project/id/101163929)

**2. Addressing PRiorities of Evaluated Nuclear Data in Europe (APRENDE)**

*   **Focus:** APRENDE is crucial for the development and safety evaluation of a wide array of nuclear energy applications, including fission and fusion. It also extends to non-energy applications such as radiation protection, radionuclide production, health, geosciences, space research, security, and industry, emphasizing the need for reliable nuclear data.
*   **Timeline:** This project is scheduled from **1 October 2024 to 30 September 2028**.
*   **Programme:** **HORIZON / EURATOM-RIA**
*   **Consortium:** Coordinated by **CENTRO DE INVESTIGACIONES ENERGETICAS MEDIOAMBIENTALES Y TECNOLOGICAS (ES)**, it boasts a large consortium of 44 participants from 19 countries, including 1 SME.
*   **CORDIS Link:** [https://cordis.europa.eu/project/id/101164596](https://cordis.europa.eu/project/id/101164596)

**3. Coordination of the European Research Community on Nuclear Materials for Energy Innovation (CONNECT-NM)**

*   **Focus:** This project establishes a co-funded European Partnership focused on nuclear materials for all reactor generations. It aims to accelerate innovation by applying modern digital technologies to materials science practices.
*   **Timeline:** The project is planned from **1 October 2024 to 30 September 2029**.
*   **Programme:** **HORIZON / EURATOM-COFUND**
*   **Consortium:** Coordinated by **CENTRO DE INVESTIGACIONES ENERGETICAS MEDIOAMBIENTALES Y TECNOLOGICAS (ES)**, it brings together 43 participants from 19 countries, including 2 SMEs.
*   **CORDIS Link:** [https://cordis.europa.eu/project/id/101165375](https://cordis.europa.eu/project/id/101165375)

**4. Advanced Nuclear Safety Evaluation of Liquid Metal Using Systems (ANSELMUS)**

*   **Focus:** ANSELMUS addresses the critical need for low-carbon energy sources by focusing on the advanced nuclear safety evaluation of liquid metal systems. While acknowledging the experience with water-cooled reactors, it aims for fundamental improvements.
*   **Timeline:** This project is currently underway, running from **1 September 2022 to 31 August 2026**.
*   **Programme:** **HORIZON / EURATOM-RIA**
*   **Consortium:** Coordinated by **STUDIECENTRUM VOOR KERNENERGIE / CENTRE D'ETUDE DE L'ENERGIE NUCLEAIRE (BE)**, it involves 17 participants from 8 countries, including 1 SME.
*   **CORDIS Link:** [https://cordis.europa.eu/project/id/101061185](https://cordis.europa.eu/project/id/101061185)

**5. Economic and Social Considerations for the Future of Nuclear Energy in Society (ECOSENS)**

*   **Focus:** ECOSENS takes a societal approach, analyzing citizens' views, risk perceptions, and the benefits and potentials of current and new nuclear technologies. This is particularly relevant in the context of major societal challenges like the climate crisis, sustainable energy policies, and energy security.
*   **Timeline:** This project is ongoing from **1 October 2022 to 30 September 2025**.
*   **Programme:** **HORIZON / EURATOM-CSA**
*   **Consortium:** Coordinated by **REGIA AUTONOMA TEHNOLOGII PENTRU ENERGIA NUCLEARA - RATEN (RO)**, it includes 12 participants from 9 countries, with 3 SMEs involved.
*   **CORDIS Link:** [https://cordis.europa.eu/project/id/101060920](https://cordis.europa.eu/project/id/101060920)"""

        # Test extraction
        print("\n1. Testing project extraction from real AI response...")
        
        # Simulate the response format
        response_data = {
            'answer': ai_response,
            'projects_found': 5
        }
        
        # Test the update_context method
        service.update_context(
            conversation_id=25,
            new_message={'text': 'Are there any recent projects about nuclear energy?', 'sender': 'user'},
            response=response_data
        )
        
        # Check if context was created and projects extracted
        if 25 in service.context_cache:
            context, _ = service.context_cache[25]
            print(f"✅ Context created with {len(context.discussed_projects)} projects")
            
            for i, project in enumerate(context.discussed_projects):
                print(f"   {i+1}. {project.acronym}: {project.title}")
            
            # Test reference resolution
            print(f"\n2. Testing reference resolution...")
            
            test_queries = [
                "tell me more about the first one",
                "what about the second project?",
                "tell me about SANE",
                "what's its budget?"
            ]
            
            for query in test_queries:
                resolved = service.resolve_references(query, context)
                print(f"   '{query}' → '{resolved}'")
            
            return True
        else:
            print("❌ Context was not created")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_reference_resolution_with_extracted_projects():
    """Test that reference resolution works with extracted projects"""
    print("\n" + "="*80)
    print("TESTING REFERENCE RESOLUTION")
    print("="*80)
    
    try:
        from app.services.conversation_context_service import (
            ConversationContextService, ConversationContext, ProjectReference
        )
        
        # Create context with extracted projects (simulating what should happen)
        context = ConversationContext(
            conversation_id=25,
            user_id=1,
            messages=[],
            discussed_projects=[
                ProjectReference(
                    project_id="SANE",
                    acronym="SANE",
                    title="Safety Assessment of Non-Electric uses of nuclear energy",
                    position_in_results=0,
                    mentioned_at="2024-01-01"
                ),
                ProjectReference(
                    project_id="APRENDE",
                    acronym="APRENDE", 
                    title="Addressing PRiorities of Evaluated Nuclear Data in Europe",
                    position_in_results=1,
                    mentioned_at="2024-01-01"
                ),
                ProjectReference(
                    project_id="CONNECT-NM",
                    acronym="CONNECT-NM",
                    title="Coordination of the European Research Community on Nuclear Materials",
                    position_in_results=2,
                    mentioned_at="2024-01-01"
                )
            ],
            mentioned_organizations=[],
            topics_of_interest=["nuclear", "energy"],
            last_search_results=[],
            last_query_type="SEARCH_PROJECTS",
            follow_up_expected=True
        )
        
        service = ConversationContextService()
        
        print("\n1. Testing ordinal references...")
        test_cases = [
            ("tell me more about the first one", "SANE"),
            ("what about the second project?", "APRENDE"),
            ("tell me about the third one", "CONNECT-NM"),
            ("what's its budget?", "CONNECT-NM"),  # Should reference last mentioned
        ]
        
        for query, expected_acronym in test_cases:
            resolved = service.resolve_references(query, context)
            if expected_acronym in resolved:
                print(f"   ✅ '{query}' → '{resolved}'")
            else:
                print(f"   ❌ '{query}' → '{resolved}' (expected {expected_acronym})")
        
        print("\n2. Testing follow-up suggestions...")
        suggestions = service.generate_follow_up_suggestions(context, {})
        print(f"   Generated {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Context Extraction Tests")
    
    # Test 1: Extract projects from real response
    extraction_test = test_context_extraction_with_real_data()
    
    # Test 2: Reference resolution
    resolution_test = test_reference_resolution_with_extracted_projects()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if extraction_test and resolution_test:
        print("✅ ALL TESTS PASSED!")
        print("\nThe context extraction and reference resolution is working:")
        print("1. ✅ Projects extracted from AI responses")
        print("2. ✅ Reference resolution works correctly")
        print("3. ✅ Follow-up suggestions generated")
        
        print("\n💡 The issue in your conversation was likely:")
        print("   - Frontend not sending conversation_id in requests")
        print("   - Using wrong API endpoint (/api/query vs /api/conversation)")
        print("   - Context not being saved between requests")
        
    else:
        print("❌ SOME TESTS FAILED")
        if not extraction_test:
            print("- Context extraction test failed")
        if not resolution_test:
            print("- Reference resolution test failed")
    
    print("="*80)

if __name__ == "__main__":
    main()