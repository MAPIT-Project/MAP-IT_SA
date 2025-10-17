"""
Analyze the EU terminology in generated content
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.proposal_writing import (
    ProposalTemplateService,
    ProposalDraftGenerator
)
from app.services.call_document_service import CallDocumentService
import psycopg2.pool

# Test configuration
TEST_CALL_ID = "HORIZON-CL3-2025-02-CS-ECCC-01"
TEST_PROJECT = {
    'title': 'AI-GUARD: AI-driven GEneralised Resilience Defence for Critical Infrastructures',
    'idea': 'AI-powered early warning system for cybersecurity threats in critical infrastructure with explainable AI',
    'research_area': 'Cybersecurity, Artificial Intelligence, Critical Infrastructure Protection',
    'main_objectives': [
        'Develop novel AI algorithms for real-time cyber threat detection in critical infrastructure',
        'Create an intuitive early warning dashboard with explainable AI recommendations',
        'Validate the system in 3 real critical infrastructure sites across Europe',
        'Establish best practices and guidelines for AI-based cybersecurity systems'
    ],
    'partners': [
        {'name': 'Technical University Munich', 'expertise': 'AI and Machine Learning'},
        {'name': 'Thales Security Solutions', 'expertise': 'Cybersecurity Solutions'},
        {'name': 'CERN', 'expertise': 'Critical Infrastructure'},
        {'name': 'University of Barcelona', 'expertise': 'Explainable AI and HCI'}
    ],
    'budget': 3500000,
    'duration_months': 36
}

async def analyze_content():
    """Analyze EU terminology in generated content"""
    
    try:
        # Initialize services
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
        call_doc_service = CallDocumentService(db_pool)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        draft_generator = ProposalDraftGenerator(call_doc_service, template_service)
        
        # Generate a section
        print("Generating content for analysis...")
        draft_result = await draft_generator.generate_section_draft(
            call_id=TEST_CALL_ID,
            section_id='excellence.objectives',
            user_context=TEST_PROJECT
        )
        
        content = draft_result['draft_text']
        
        # Comprehensive EU terminology list
        eu_terms = {
            'Basic EU Terms': [
                'TRL', 'Technology Readiness Level', 'work package', 'WP', 'deliverable', 'milestone',
                'consortium', 'impact', 'excellence', 'implementation', 'Key Performance Indicator', 'KPI',
                'European Commission', 'Horizon Europe', 'EU added value', 'strategic alignment',
                'innovation', 'state of the art', 'SOTA', 'dissemination', 'exploitation', 'communication'
            ],
            'Advanced EU Terminology': [
                'risk management', 'data management', 'ethics', 'gender', 'sustainability', 'open science',
                'intellectual property', 'IPR', 'standardization', 'certification', 'validation', 'demonstration',
                'European Green Deal', 'Digital Europe Programme', 'European Research Area', 'ERA',
                'UN Sustainable Development Goals', 'SDGs', 'European values', 'fundamental rights',
                'Data Protection Regulation', 'GDPR', 'Cybersecurity Act', 'NIS Directive',
                'European Innovation Council', 'EIC', 'European Institute of Innovation and Technology', 'EIT',
                'single market', 'digital sovereignty', 'strategic autonomy', 'European Digital Strategy',
                'cross-border', 'multi-country', 'SME', 'Small and Medium-sized Enterprise',
                'public-private partnership', 'PPP', 'stakeholder', 'end-user', 'policy maker',
                'regulation', 'directive', 'standard', 'framework', 'guideline', 'best practice'
            ],
            'EU Strategies & Policies': [
                'European Digital Strategy', 'European Green Deal', 'Digital Europe Programme', 
                'European Research Area', 'Cybersecurity Strategy', 'single market', 
                'digital sovereignty', 'strategic autonomy', 'European values', 'fundamental rights'
            ],
            'Impact & Value Terms': [
                'EU added value', 'European value', 'European impact', 'contribution to Europe',
                'benefit to EU', 'European citizens', 'European society', 'European economy',
                'European resilience', 'European competitiveness', 'European leadership'
            ]
        }
        
        print("\n" + "="*80)
        print("🔍 EU TERMINOLOGY ANALYSIS")
        print("="*80)
        
        content_lower = content.lower()
        found_terms = []
        missing_terms = []
        
        for category, terms in eu_terms.items():
            print(f"\n📂 {category}:")
            print("-" * 40)
            
            category_found = 0
            category_total = len(terms)
            
            for term in terms:
                if term.lower() in content_lower:
                    print(f"   ✅ {term}")
                    found_terms.append(term)
                    category_found += 1
                else:
                    print(f"   ❌ {term}")
                    missing_terms.append(term)
            
            percentage = (category_found / category_total * 100) if category_total > 0 else 0
            print(f"\n   Coverage: {category_found}/{category_total} ({percentage:.0f}%)")
        
        # Overall statistics
        total_terms = sum(len(terms) for terms in eu_terms.values())
        total_found = len(found_terms)
        overall_percentage = (total_found / total_terms * 100) if total_terms > 0 else 0
        
        print(f"\n" + "="*80)
        print(f"📊 OVERALL EU TERMINOLOGY COVERAGE")
        print("="*80)
        print(f"Total Terms: {total_found}/{total_terms}")
        print(f"Overall Coverage: {overall_percentage:.0f}%")
        
        # Show content preview
        print(f"\n" + "="*80)
        print(f"📄 CONTENT PREVIEW (First 500 words)")
        print("="*80)
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)
        
        # Identify most important missing terms
        print(f"\n" + "="*80)
        print(f"🎯 PRIORITY MISSING TERMS FOR 100% ALIGNMENT")
        print("="*80)
        
        priority_terms = [
            'European Green Deal', 'Digital Europe Programme', 'European Research Area', 
            'GDPR', 'Cybersecurity Act', 'single market', 'digital sovereignty', 
            'strategic autonomy', 'EU added value', 'European values', 'European citizens',
            'cross-border', 'multi-country', 'SME', 'stakeholder', 'European Digital Strategy'
        ]
        
        for term in priority_terms:
            if term.lower() not in content_lower:
                print(f"   🚨 {term}")
        
        db_pool.closeall()
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(analyze_content())
    sys.exit(0 if success else 1)