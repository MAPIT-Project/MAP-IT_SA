"""
Comprehensive Test Suite for Proposal Writing System

This script tests all components of the proposal writing assistant.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2.pool

from app.services.ai_intent_service import AIIntentService
from app.services.call_document_service import CallDocumentService
from app.services.proposal_writing import (
    BudgetAssistant,
    ComplianceChecker,
    EvaluationCriteriaMatcher,
    ProposalDraftGenerator,
    ProposalTemplateService,
    QualityImprover,
)

# Test configuration
TEST_CALL_ID = "HORIZON-CL3-2025-02-CS-ECCC-01"
TEST_PROJECT_IDEA = (
    "AI-powered early warning system for cybersecurity threats in critical infrastructure"
)


async def test_template_generation():
    """Test proposal template generation"""
    print("\n" + "=" * 80)
    print("TEST 1: TEMPLATE GENERATION")
    print("=" * 80)

    try:
        # Initialize services
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set - skipping")
            return False

        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
        call_doc_service = CallDocumentService(db_pool)
        template_service = ProposalTemplateService(db_pool, call_doc_service)

        print(f"\n📋 Generating template for {TEST_CALL_ID}...")

        template = template_service.generate_template(TEST_CALL_ID)
        await template

        print("\n✅ Template generated successfully!")
        print(f"   - Proposal Type: {template['proposal_type']}")
        print(f"   - Page Limit: {template['metadata']['page_limit']}")
        print(f"   - Sections: {len(template['structure']['sections'])}")

        print("\n📂 Section Structure:")
        for section in template["structure"]["sections"]:
            print(
                f"   {section['order']}. {section['name']} (max {section.get('page_limit', '?')} pages)"
            )
            for subsection in section.get("subsections", []):
                print(f"      - {subsection['name']}")

        print("\n📋 Evaluation Criteria Mapping:")
        for category, criteria in template["evaluation_criteria"].items():
            print(f"   {category.upper()}:")
            for criterion in criteria[:2]:  # Show first 2
                print(f"      - {criterion}")

        db_pool.closeall()
        return True

    except Exception as e:
        print(f"❌ Template generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_draft_generation():
    """Test section draft generation"""
    print("\n" + "=" * 80)
    print("TEST 2: DRAFT GENERATION")
    print("=" * 80)

    try:
        # Initialize services
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set - skipping")
            return False

        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
        call_doc_service = CallDocumentService(db_pool)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        draft_generator = ProposalDraftGenerator(call_doc_service, template_service)

        print("\n✍️ Generating draft for 'Objectives' section...")

        user_context = {
            "project_idea": TEST_PROJECT_IDEA,
            "research_area": "Cybersecurity, AI, Critical Infrastructure Protection",
            "main_objectives": [
                "Develop AI models for real-time threat detection",
                "Create early warning dashboard for operators",
                "Validate system in real critical infrastructure",
            ],
            "partners": [
                {"name": "TU Munich", "expertise": "AI and Machine Learning"},
                {"name": "Thales", "expertise": "Cybersecurity Solutions"},
                {"name": "CERN", "expertise": "Critical Infrastructure"},
            ],
            "budget": 3000000,
            "duration_months": 36,
        }

        draft_result = await draft_generator.generate_section_draft(
            call_id=TEST_CALL_ID, section_id="excellence.objectives", user_context=user_context
        )

        print("\n✅ Draft generated successfully!")
        print("\n📄 DRAFT TEXT:")
        print("-" * 80)
        print(
            draft_result["draft_text"][:500] + "..."
            if len(draft_result["draft_text"]) > 500
            else draft_result["draft_text"]
        )
        print("-" * 80)

        print("\n📊 Draft Statistics:")
        print(f"   - Word count: {draft_result['word_count']}")
        print(f"   - Estimated pages: {draft_result['estimated_pages']:.1f}")
        print(f"   - Quality score: {draft_result.get('quality_score', 0.7) * 100:.0f}%")

        print("\n📋 Evaluation Criteria Addressed:")
        for criterion in draft_result.get("evaluation_criteria_addressed", []):
            print(f"   ✅ {criterion}")

        print("\n💡 Improvement Suggestions:")
        for suggestion in draft_result.get("suggestions", []):
            print(f"   • [{suggestion.get('priority', 'info')}] {suggestion.get('text', '')}")

        db_pool.closeall()
        return True

    except Exception as e:
        print(f"❌ Draft generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_criteria_evaluation():
    """Test evaluation criteria matching"""
    print("\n" + "=" * 80)
    print("TEST 3: CRITERIA EVALUATION")
    print("=" * 80)

    try:
        criteria_matcher = EvaluationCriteriaMatcher()

        # Sample section text
        section_text = """
        The CYBER-SHIELD project aims to develop an innovative AI-powered early warning
        system for cybersecurity threats in critical infrastructure. Our objectives are:

        1. Develop advanced AI models capable of detecting cyber threats in real-time
        2. Create an intuitive early warning dashboard for infrastructure operators
        3. Validate the system in real critical infrastructure environments

        Our methodology combines machine learning, anomaly detection, and expert knowledge
        to achieve unprecedented accuracy in threat prediction. This approach goes beyond
        the current state of the art by integrating multiple data sources and using
        explainable AI techniques.
        """

        evaluation_criteria = [
            "Clarity and pertinence of objectives",
            "Soundness of methodology",
            "Credibility of approach",
            "Innovation beyond state of the art",
        ]

        print(f"\n🔍 Analyzing section against {len(evaluation_criteria)} criteria...")

        analysis = await criteria_matcher.analyze_section(
            section_text=section_text, evaluation_criteria=evaluation_criteria, call_id=TEST_CALL_ID
        )

        print("\n✅ Analysis complete!")
        print(f"\n📊 Overall Score: {analysis['overall_score'] * 100:.0f}%")

        print("\n📋 Criteria Coverage:")
        for criterion, data in analysis["criteria_coverage"].items():
            status = "✅" if data["addressed"] else "❌"
            print(f"\n   {status} {criterion}")
            print(f"      Strength: {data['strength'] * 100:.0f}%")
            if data.get("evidence"):
                print(f"      Evidence: {data['evidence'][:1]}")  # Show first evidence
            if data.get("gaps"):
                print(f"      Gaps: {data['gaps'][:1]}")  # Show first gap

        print("\n💡 Recommendations:")
        for rec in analysis.get("recommendations", [])[:3]:
            print(f"   • [{rec.get('priority', 'info')}] {rec.get('text', '')[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Criteria evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_budget_generation():
    """Test budget table generation"""
    print("\n" + "=" * 80)
    print("TEST 4: BUDGET GENERATION")
    print("=" * 80)

    try:
        budget_assistant = BudgetAssistant()

        project_params = {
            "duration_months": 36,
            "partners": [
                {
                    "name": "Technical University Munich",
                    "country": "DE",
                    "type": "HES",
                    "person_months": 48,
                    "avg_monthly_rate": 5500,
                    "equipment_costs": 200000,
                    "other_direct_costs": 50000,
                },
                {
                    "name": "Thales Security Solutions",
                    "country": "FR",
                    "type": "PRC",
                    "person_months": 36,
                    "avg_monthly_rate": 6000,
                    "equipment_costs": 100000,
                    "other_direct_costs": 30000,
                },
                {
                    "name": "CERN",
                    "country": "CH",
                    "type": "REC",
                    "person_months": 24,
                    "avg_monthly_rate": 6500,
                    "other_direct_costs": 40000,
                },
            ],
            "total_budget": 3000000,
        }

        print("\n💰 Generating budget for 3-partner consortium...")

        budget_result = await budget_assistant.generate_budget_table(
            call_id=TEST_CALL_ID, proposal_type="RIA", project_params=project_params
        )

        print("\n✅ Budget generated successfully!")

        print(f"\n{budget_result['budget_table_formatted']}")

        print("\n📊 Summary:")
        print(
            f"   - Total Eligible Costs: €{budget_result['summary']['total_eligible_costs']:,.2f}"
        )
        print(
            f"   - Total Requested Funding: €{budget_result['summary']['total_requested_funding']:,.2f}"
        )
        print(
            f"   - Average Funding Rate: {budget_result['summary']['average_funding_rate'] * 100:.1f}%"
        )

        print("\n✅ Compliance:")
        if budget_result["compliance"]["compliant"]:
            print("   ✓ Budget is compliant with call requirements")
        else:
            print("   ✗ Compliance issues found:")
            for issue in budget_result["compliance"]["issues"]:
                print(f"      - {issue}")

        if budget_result["compliance"]["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in budget_result["compliance"]["warnings"]:
                print(f"   - {warning}")

        return True

    except Exception as e:
        print(f"❌ Budget generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_compliance_check():
    """Test proposal compliance checking"""
    print("\n" + "=" * 80)
    print("TEST 5: COMPLIANCE CHECK")
    print("=" * 80)

    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set - skipping")
            return False

        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
        call_doc_service = CallDocumentService(db_pool)
        compliance_checker = ComplianceChecker(call_doc_service, db_pool)

        # Sample proposal data
        proposal_data = {
            "sections": {
                "excellence.objectives": "Sample objectives text..." * 100,  # ~300 words
                "excellence.methodology": "Sample methodology text..." * 150,  # ~450 words
                # Missing 'excellence.beyond_sota' - compliance issue!
                "impact.pathways": "Sample impact text..." * 100,
                "implementation.work_plan": "Sample work plan..." * 200,
            },
            "consortium": [
                {"name": "Uni A", "country": "DE", "type": "HES", "budget_share": 0.4},
                {"name": "Company B", "country": "FR", "type": "PRC", "budget_share": 0.6},
                # Only 2 entities - compliance issue!
            ],
            "budget": {
                "partner_budgets": [
                    {
                        "partner_name": "Uni A",
                        "costs": {
                            "personnel": 500000,
                            "equipment": 200000,
                            "other_direct": 50000,
                            "indirect": 187500,  # Should be 25% of eligible direct
                        },
                    }
                ]
            },
        }

        print("\n✅ Running compliance checks...")

        compliance_result = await compliance_checker.run_compliance_check(
            call_id=TEST_CALL_ID, proposal_data=proposal_data
        )

        print("\n📊 Compliance Report:")
        print(
            f"   Overall Compliant: {'✅ YES' if compliance_result['overall_compliant'] else '❌ NO'}"
        )
        print("\n   Summary:")
        print(f"   - Critical Issues: {compliance_result['summary']['critical_issues']}")
        print(f"   - High Priority Issues: {compliance_result['summary']['high_priority_issues']}")
        print(f"   - Warnings: {compliance_result['summary']['warnings']}")

        print("\n🚨 Action Items:")
        for action_group in compliance_result["action_items"]:
            print(f"\n   [{action_group['priority']}] {action_group['description']}")
            for item in action_group["items"][:3]:  # Show max 3
                print(f"      - {item}")

        db_pool.closeall()
        return True

    except Exception as e:
        print(f"❌ Compliance check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_quality_improvement():
    """Test quality analysis and improvement"""
    print("\n" + "=" * 80)
    print("TEST 6: QUALITY IMPROVEMENT")
    print("=" * 80)

    try:
        ai_service = AIIntentService()
        quality_improver = QualityImprover(ai_service)

        # Sample section with quality issues
        section_text = """
        We might try to develop a system that could potentially address some of the
        cybersecurity challenges. The project will possibly create something innovative
        and we hope to achieve good results. We will try to use advanced technology
        and possibly integrate various components that might help in threat detection.
        """

        print("\n🔍 Analyzing section quality...")

        analysis = await quality_improver.analyze_quality(
            section_text=section_text, section_type="excellence.objectives"
        )

        print("\n✅ Quality analysis complete!")
        print(f"\n📊 Overall Quality Score: {analysis['overall_quality_score'] * 100:.0f}%")

        print("\n📖 Readability:")
        print(f"   - Score: {analysis['readability']['score'] * 100:.0f}%")
        print(
            f"   - Avg sentence length: {analysis['readability']['avg_sentence_length']:.1f} words"
        )
        for issue in analysis["readability"]["issues"][:2]:
            print(f"   ⚠️ {issue}")

        print("\n📝 Terminology:")
        print(f"   - Score: {analysis['terminology']['score'] * 100:.0f}%")
        print(f"   - Missing key terms: {', '.join(analysis['terminology']['missing_terms'][:3])}")

        print("\n📐 Structure:")
        print(f"   - Score: {analysis['structure']['score'] * 100:.0f}%")
        for issue in analysis["structure"]["issues"]:
            print(f"   ⚠️ {issue}")

        print("\n💪 Impact Language:")
        print(f"   - Score: {analysis['impact_language']['score'] * 100:.0f}%")
        print(f"   - Weak phrases found: {analysis['impact_language']['weak_phrases_count']}")
        for issue in analysis["impact_language"]["issues"][:2]:
            print(f"   ⚠️ {issue}")

        print("\n💡 Improvement Suggestions:")
        for suggestion in analysis["improvement_suggestions"]:
            print(f"   • [{suggestion['type']}] {suggestion['suggestion']}")

        return True

    except Exception as e:
        print(f"❌ Quality improvement failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_conversational_interface():
    """Test proposal writing through conversation"""
    print("\n" + "=" * 80)
    print("TEST 7: CONVERSATIONAL INTERFACE")
    print("=" * 80)

    try:
        from app.services.conversation.conversation_manager import ConversationManager

        print("\n💬 Testing conversational proposal writing...")

        manager = ConversationManager()
        conv_id = 99999

        # Test template generation
        print(f"\n1️⃣ User: 'Generate a proposal template for {TEST_CALL_ID}'")
        response1 = await manager.process_message(
            conversation_id=conv_id,
            user_message=f"Generate a proposal template for {TEST_CALL_ID}",
            user_id=1,
            streaming=False,
        )

        print(f"   🤖 Response: {response1.get('response', '')[:200]}...")
        print(f"   📋 Mode: {response1.get('mode', 'normal')}")

        # Test draft generation
        print("\n2️⃣ User: 'Help me write the objectives section'")
        response2 = await manager.process_message(
            conversation_id=conv_id,
            user_message="Help me write the objectives section",
            user_id=1,
            streaming=False,
        )

        print(f"   🤖 Response: {response2.get('response', '')[:200]}...")

        print("\n✅ Conversational interface working!")
        return True

    except Exception as e:
        print(f"❌ Conversational interface failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("🧪 PROPOSAL WRITING SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test Call: {TEST_CALL_ID}")
    print(f"Project: {TEST_PROJECT_IDEA}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Template Generation", await test_template_generation()))
    results.append(("Draft Generation", await test_draft_generation()))
    results.append(("Criteria Evaluation", await test_criteria_evaluation()))
    results.append(("Budget Generation", await test_budget_generation()))
    results.append(("Compliance Check", await test_compliance_check()))
    results.append(("Quality Improvement", await test_quality_improvement()))
    results.append(("Conversational Interface", await test_conversational_interface()))

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{'=' * 80}")
    print(f"FINAL SCORE: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")
    print(f"{'=' * 80}\n")

    return passed == total


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
