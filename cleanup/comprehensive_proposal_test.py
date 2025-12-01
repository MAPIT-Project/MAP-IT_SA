"""
Comprehensive End-to-End Test for Proposal Writing System

This test will verify EVERYTHING works correctly.
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Test imports
print("🧪 Testing imports...")

try:
    from app.services.proposal_writing import (
        ProposalTemplateService,
        ProposalDraftGenerator,
        EvaluationCriteriaMatcher,
        BudgetAssistant,
        ComplianceChecker,
        QualityImprover
    )
    print("   ✅ All proposal writing services imported")
except Exception as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

try:
    from app.services.call_document_service import CallDocumentService
    print("   ✅ CallDocumentService imported")
except Exception as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

try:
    from app.services.ai_intent_service import AIIntentService
    print("   ✅ AIIntentService imported")
except Exception as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

try:
    import psycopg2.pool
    print("   ✅ Database driver imported")
except Exception as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Configuration
TEST_CALL_ID = "HORIZON-CL3-2025-02-CS-ECCC-01"

async def test_1_database_connection():
    """Test 1: Database connection"""
    print("\n" + "="*80)
    print("TEST 1: DATABASE CONNECTION")
    print("="*80)
    
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        print(f"🔗 Connecting to database...")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT COUNT(*) FROM proposals")
        count = cursor.fetchone()[0]
        
        print(f"✅ Database connected successfully")
        print(f"   Current proposals: {count}")
        
        db_pool.putconn(conn)
        db_pool.closeall()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_2_template_service():
    """Test 2: Template generation"""
    print("\n" + "="*80)
    print("TEST 2: TEMPLATE GENERATION")
    print("="*80)
    
    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)
        
        call_doc_service = CallDocumentService(db_pool)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        
        print(f"📋 Generating template for {TEST_CALL_ID}...")
        
        template = template_service.generate_template(TEST_CALL_ID)
        
        print(f"✅ Template generated successfully")
        print(f"   Type: {template['proposal_type']}")
        print(f"   Sections: {len(template['structure']['sections'])}")
        print(f"   Page limit: {template['metadata']['page_limit']}")
        
        # Verify structure
        assert 'structure' in template
        assert 'evaluation_criteria' in template
        assert len(template['structure']['sections']) > 0
        
        db_pool.closeall()
        
        return True
        
    except Exception as e:
        print(f"❌ Template generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_3_draft_generation():
    """Test 3: Draft generation"""
    print("\n" + "="*80)
    print("TEST 3: DRAFT GENERATION")
    print("="*80)
    
    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)
        
        call_doc_service = CallDocumentService(db_pool)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        draft_generator = ProposalDraftGenerator(call_doc_service, template_service)
        
        print(f"✍️ Generating draft for objectives section...")
        
        user_context = {
            'project_idea': 'AI-powered cybersecurity early warning system',
            'research_area': 'Cybersecurity, AI',
            'main_objectives': ['Develop AI models', 'Create dashboard', 'Validate system'],
            'budget': 3000000,
            'duration_months': 36
        }
        
        draft = await draft_generator.generate_section_draft(
            call_id=TEST_CALL_ID,
            section_id='excellence.objectives',
            user_context=user_context
        )
        
        print(f"✅ Draft generated successfully")
        print(f"   Word count: {draft['word_count']}")
        print(f"   Quality score: {draft.get('quality_score', 0)*100:.0f}%")
        print(f"   Draft preview: {draft['draft_text'][:150]}...")
        
        # Verify
        assert draft['word_count'] > 100
        assert 'draft_text' in draft
        
        db_pool.closeall()
        
        return True
        
    except Exception as e:
        print(f"❌ Draft generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_4_budget_generation():
    """Test 4: Budget generation"""
    print("\n" + "="*80)
    print("TEST 4: BUDGET GENERATION")
    print("="*80)
    
    try:
        budget_assistant = BudgetAssistant()
        
        print(f"💰 Generating budget table...")
        
        project_params = {
            'duration_months': 36,
            'partners': [
                {
                    'name': 'TU Munich',
                    'country': 'DE',
                    'type': 'HES',
                    'person_months': 48,
                    'avg_monthly_rate': 5500
                },
                {
                    'name': 'Thales',
                    'country': 'FR',
                    'type': 'PRC',
                    'person_months': 36,
                    'avg_monthly_rate': 6000
                }
            ]
        }
        
        budget = await budget_assistant.generate_budget_table(
            call_id=TEST_CALL_ID,
            proposal_type='RIA',
            project_params=project_params
        )
        
        print(f"✅ Budget generated successfully")
        print(f"   Total eligible: €{budget['summary']['total_eligible_costs']:,.2f}")
        print(f"   Total funding: €{budget['summary']['total_requested_funding']:,.2f}")
        print(f"   Partners: {len(budget['partner_budgets'])}")
        
        # Verify
        assert budget['summary']['total_eligible_costs'] > 0
        assert len(budget['partner_budgets']) == 2
        
        return True
        
    except Exception as e:
        print(f"❌ Budget generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_5_criteria_matching():
    """Test 5: Evaluation criteria matching"""
    print("\n" + "="*80)
    print("TEST 5: CRITERIA MATCHING")
    print("="*80)
    
    try:
        criteria_matcher = EvaluationCriteriaMatcher()
        
        print(f"🔍 Analyzing criteria coverage...")
        
        test_text = """
        The CYBER-SHIELD project aims to develop innovative AI models for threat detection.
        Our methodology combines machine learning with expert knowledge.
        We will validate the system in real critical infrastructure sites.
        """
        
        criteria = [
            "Clarity of objectives",
            "Soundness of methodology",
            "Credibility of approach"
        ]
        
        analysis = await criteria_matcher.analyze_section(
            section_text=test_text,
            evaluation_criteria=criteria,
            call_id=TEST_CALL_ID
        )
        
        print(f"✅ Criteria analysis complete")
        print(f"   Overall score: {analysis['overall_score']*100:.0f}%")
        print(f"   Criteria analyzed: {len(analysis['criteria_coverage'])}")
        
        # Verify
        assert 'overall_score' in analysis
        assert 'criteria_coverage' in analysis
        
        return True
        
    except Exception as e:
        print(f"❌ Criteria matching failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_6_quality_improvement():
    """Test 6: Quality improvement"""
    print("\n" + "="*80)
    print("TEST 6: QUALITY IMPROVEMENT")
    print("="*80)
    
    try:
        ai_service = AIIntentService()
        quality_improver = QualityImprover(ai_service)
        
        print(f"🎨 Analyzing section quality...")
        
        test_text = """
        We might try to develop a system. It could potentially work well.
        The project will possibly achieve some results.
        """
        
        analysis = await quality_improver.analyze_quality(
            section_text=test_text,
            section_type='excellence.objectives'
        )
        
        print(f"✅ Quality analysis complete")
        print(f"   Overall quality: {analysis['overall_quality_score']*100:.0f}%")
        print(f"   Readability: {analysis['readability']['score']*100:.0f}%")
        print(f"   Suggestions: {len(analysis['improvement_suggestions'])}")
        
        # Verify
        assert 'overall_quality_score' in analysis
        assert 'improvement_suggestions' in analysis
        
        return True
        
    except Exception as e:
        print(f"❌ Quality improvement failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_7_api_integration():
    """Test 7: API integration check"""
    print("\n" + "="*80)
    print("TEST 7: API INTEGRATION")
    print("="*80)
    
    try:
        # Check if routes are importable
        from app.api.proposal_routes import router
        
        print(f"✅ Proposal routes imported successfully")
        
        # Check main app
        from app.main import app
        
        # Verify proposal routes are registered
        routes = [route.path for route in app.routes]
        proposal_routes = [r for r in routes if 'proposal' in r]
        
        print(f"✅ Main app has {len(proposal_routes)} proposal endpoints:")
        for route in proposal_routes[:5]:
            print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ API integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_8_end_to_end():
    """Test 8: End-to-end workflow"""
    print("\n" + "="*80)
    print("TEST 8: END-TO-END WORKFLOW")
    print("="*80)
    
    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # 1. Create a proposal
        print("1️⃣ Creating test proposal...")
        cursor.execute("""
            INSERT INTO proposals (
                call_identifier, proposal_title, proposal_type, status
            ) VALUES (%s, %s, %s, %s) RETURNING id
        """, (TEST_CALL_ID, 'End-to-End Test Proposal', 'RIA', 'draft'))
        
        proposal_id = cursor.fetchone()[0]
        print(f"   ✅ Created proposal ID: {proposal_id}")
        
        # 2. Add a section
        print("2️⃣ Adding proposal section...")
        cursor.execute("""
            INSERT INTO proposal_sections (
                proposal_id, section_id, section_name, section_content
            ) VALUES (%s, %s, %s, %s) RETURNING id
        """, (proposal_id, 'excellence.objectives', 'Objectives', 'Test objectives content'))
        
        section_id = cursor.fetchone()[0]
        print(f"   ✅ Created section ID: {section_id}")
        
        # 3. Check proposal overview
        print("3️⃣ Checking proposal overview...")
        cursor.execute("""
            SELECT proposal_title, section_count, total_words
            FROM proposal_overview WHERE id = %s
        """, (proposal_id,))
        
        overview = cursor.fetchone()
        print(f"   ✅ Overview: {overview[0]}, {overview[1]} sections, {overview[2]} words")
        
        # 4. Clean up
        print("4️⃣ Cleaning up...")
        cursor.execute("DELETE FROM proposals WHERE id = %s", (proposal_id,))
        
        conn.commit()
        db_pool.putconn(conn)
        db_pool.closeall()
        
        print(f"✅ End-to-end workflow complete")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀"*40)
    print("\n  COMPREHENSIVE PROPOSAL WRITING SYSTEM TEST")
    print(f"\n  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "🚀"*40 + "\n")
    
    tests = [
        ("Database Connection", test_1_database_connection),
        ("Template Generation", test_2_template_service),
        ("Draft Generation", test_3_draft_generation),
        ("Budget Generation", test_4_budget_generation),
        ("Criteria Matching", test_5_criteria_matching),
        ("Quality Improvement", test_6_quality_improvement),
        ("API Integration", test_7_api_integration),
        ("End-to-End Workflow", test_8_end_to_end),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"FINAL SCORE: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is fully operational! 🎉\n")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review errors above.\n")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

