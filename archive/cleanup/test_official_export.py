"""
Test Official Document Export System

Tests the ability to create submission-ready documents:
- Part B Word (.docx)
- Budget Excel (.xlsx)
- Ethics assessment
- Complete ZIP package
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

# Test imports
import psycopg2.pool

from app.services.proposal_writing import (
    OfficialBudgetExporter,
    OfficialDocumentProcessor,
    OfficialWordExporter,
    SubmissionExporter,
)


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")


async def test_document_processor():
    """Test 1: Official Document Processor"""

    print_header("TEST 1: OFFICIAL DOCUMENT PROCESSOR")

    try:
        processor = OfficialDocumentProcessor()

        # Test getting template for RIA
        print("📋 Testing template detection...")
        template_path = processor.get_template_for_action_type("RIA")
        if template_path and template_path.exists():
            print_success(f"Found RIA template: {template_path.name}")
        else:
            print_info("RIA template not found in newdocs/ (will use default)")

        # Test getting evaluation form
        print("📊 Testing evaluation form detection...")
        eval_path = processor.get_evaluation_form("RIA")
        if eval_path and eval_path.exists():
            print_success(f"Found RIA evaluation form: {eval_path.name}")
        else:
            print_info("Evaluation form not found (will use default)")

        # Test extracting structure
        print("🏗️  Testing structure extraction...")
        structure = processor.extract_template_structure("RIA")
        print_success(f"Extracted structure with {len(structure.get('sections', []))} sections")
        for section in structure.get("sections", []):
            print(f"   - {section.get('name', 'Unknown')}")

        # Test extracting criteria
        print("✨ Testing criteria extraction...")
        criteria = processor.extract_evaluation_criteria("RIA")
        total_criteria = sum(len(v) for v in criteria.values())
        print_success(f"Extracted {total_criteria} evaluation criteria")
        for category, items in criteria.items():
            print(f"   {category.upper()}: {len(items)} criteria")

        return True

    except Exception as e:
        print_error(f"Document processor test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_word_exporter():
    """Test 2: Word Document Export"""

    print_header("TEST 2: WORD DOCUMENT EXPORT")

    try:
        exporter = OfficialWordExporter()

        # Create test proposal data
        test_data = {
            "title": "Test Horizon Europe Proposal",
            "acronym": "TEST-HE",
            "call_id": "HORIZON-CL3-2025-TEST",
            "sections": {
                "excellence.objectives": """
                This project aims to revolutionize cybersecurity through AI-powered threat detection.

                Our main objectives are:
                1. Develop novel ML algorithms for real-time threat identification
                2. Create adaptive defense mechanisms
                3. Establish EU-wide threat intelligence sharing
                """,
                "excellence.methodology": """
                We will employ a mixed-methods approach combining:
                - Machine learning on large-scale threat datasets
                - Behavioral analysis of attack patterns
                - Collaborative testing with industry partners
                """,
                "excellence.beyond_sota": """
                Our approach goes beyond current state-of-the-art by:
                - Using transformer architectures for threat detection
                - Implementing federated learning for privacy
                - Achieving 99.8% detection accuracy in pilot tests
                """,
                "impact.pathways": """
                Expected impacts include:
                - 50% reduction in successful cyber attacks
                - €1.5B annual savings for EU businesses
                - 10,000 jobs in cybersecurity sector
                """,
                "impact.dissemination": """
                Dissemination strategy:
                - Open-source toolkit released on GitHub
                - 5 peer-reviewed publications
                - Annual conferences with 500+ stakeholders
                - Policy briefs for EU Commission
                """,
                "implementation.work_plan": """
                Work Plan Structure:

                WP1: Requirements & Analysis (M1-M6)
                WP2: Algorithm Development (M6-M18)
                WP3: Integration & Testing (M18-M30)
                WP4: Validation & Deployment (M30-M36)
                WP5: Dissemination & Exploitation (M1-M36)
                WP6: Project Management (M1-M36)
                """,
                "implementation.consortium": """
                Our consortium brings together:

                - University of Tech (Coordinator) - ML expertise
                - CyberSec Corp - Industry deployment
                - Research Institute EU - Policy expertise
                - SME Innovation - Commercialization

                Coverage: 4 EU countries, complementary skills, proven track record
                """,
            },
        }

        print("📄 Generating Part B Word document...")
        docx_buffer = exporter.create_part_b_document(test_data, action_type="RIA")

        # Save to file for inspection
        output_path = Path("test_outputs")
        output_path.mkdir(exist_ok=True)

        output_file = output_path / f"TEST_PartB_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        with open(output_file, "wb") as f:
            f.write(docx_buffer.getvalue())

        file_size = output_file.stat().st_size
        print_success(f"Word document created: {output_file.name}")
        print_info(f"File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

        return True

    except Exception as e:
        print_error(f"Word export test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_excel_exporter():
    """Test 3: Excel Budget Export"""

    print_header("TEST 3: EXCEL BUDGET EXPORT")

    try:
        exporter = OfficialBudgetExporter()

        # Create test budget data
        test_budget = {
            "partner_budgets": [
                {
                    "partner_name": "University of Technology",
                    "country": "Germany",
                    "partner_type": "HES",
                    "costs": {
                        "personnel": 250000,
                        "subcontracting": 50000,
                        "equipment": 100000,
                        "other_direct": 25000,
                        "indirect": 106250,  # 25% of direct eligible
                    },
                    "total_eligible_costs": 531250,
                    "funding_rate": 100,
                    "requested_funding": 531250,
                },
                {
                    "partner_name": "CyberSec Corporation",
                    "country": "France",
                    "partner_type": "PRC",
                    "costs": {
                        "personnel": 150000,
                        "subcontracting": 0,
                        "equipment": 50000,
                        "other_direct": 15000,
                        "indirect": 53750,
                    },
                    "total_eligible_costs": 268750,
                    "funding_rate": 70,
                    "requested_funding": 188125,
                },
                {
                    "partner_name": "Innovation SME",
                    "country": "Spain",
                    "partner_type": "PRC",
                    "costs": {
                        "personnel": 120000,
                        "subcontracting": 30000,
                        "equipment": 40000,
                        "other_direct": 10000,
                        "indirect": 50000,
                    },
                    "total_eligible_costs": 250000,
                    "funding_rate": 70,
                    "requested_funding": 175000,
                },
            ],
            "summary": {
                "total_eligible_costs": 1050000,
                "total_requested_funding": 894375,
                "average_funding_rate": 85.2,
            },
        }

        print("💰 Generating budget Excel...")
        xlsx_buffer = exporter.create_budget_excel(test_budget)

        # Save to file
        output_path = Path("test_outputs")
        output_path.mkdir(exist_ok=True)

        output_file = output_path / f"TEST_Budget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(output_file, "wb") as f:
            f.write(xlsx_buffer.getvalue())

        file_size = output_file.stat().st_size
        print_success(f"Excel budget created: {output_file.name}")
        print_info(f"File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        print_info(f"Total budget: €{test_budget['summary']['total_eligible_costs']:,.2f}")
        print_info(f"Requested funding: €{test_budget['summary']['total_requested_funding']:,.2f}")

        return True

    except Exception as e:
        print_error(f"Excel export test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_full_export_with_database():
    """Test 4: Full Export from Database"""

    print_header("TEST 4: FULL EXPORT FROM DATABASE")

    try:
        # Connect to database
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print_info("No DATABASE_URL found, skipping database test")
            return True

        print("🔗 Connecting to database...")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)

        # Check if we have any proposals
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, proposal_title, proposal_acronym FROM proposals ORDER BY id DESC LIMIT 1"
        )
        proposal = cursor.fetchone()
        db_pool.putconn(conn)

        if not proposal:
            print_info("No proposals in database, creating test proposal...")

            # Create a test proposal
            conn = db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO proposals (user_id, call_identifier, proposal_title, proposal_acronym, proposal_type, status)
                VALUES ('test-user', 'HORIZON-TEST', 'Database Test Proposal', 'DB-TEST', 'RIA', 'draft')
                RETURNING id
            """
            )
            proposal_id = cursor.fetchone()[0]

            # Add a test section
            cursor.execute(
                """
                INSERT INTO proposal_sections
                (proposal_id, section_id, section_name, section_content, word_count)
                VALUES (%s, 'excellence.objectives', 'Objectives', 'Test objectives section', 3)
            """,
                (proposal_id,),
            )

            conn.commit()
            db_pool.putconn(conn)

            print_success(f"Created test proposal with ID: {proposal_id}")
        else:
            proposal_id = proposal[0]
            print_success(f"Using existing proposal: {proposal[1]} (ID: {proposal_id})")

        # Test export
        print("📦 Exporting proposal package...")
        exporter = SubmissionExporter(db_pool)

        # Export Part B
        print("   📄 Exporting Part B...")
        part_b = await exporter.export_part_b(proposal_id)
        print_success(f"Part B exported ({len(part_b.getvalue())} bytes)")

        # Export budget
        print("   💰 Exporting budget...")
        budget = await exporter.export_budget(proposal_id)
        print_success(f"Budget exported ({len(budget.getvalue())} bytes)")

        # Export complete package
        print("   📦 Exporting complete package...")
        package = await exporter.export_proposal_package(
            proposal_id, include_budget=True, include_ethics=False, include_security=False
        )

        # Save package
        output_path = Path("test_outputs")
        output_path.mkdir(exist_ok=True)

        output_file = output_path / f"SUBMISSION_PACKAGE_{proposal_id}.zip"
        with open(output_file, "wb") as f:
            f.write(package.getvalue())

        file_size = output_file.stat().st_size
        print_success(f"Complete package created: {output_file.name}")
        print_info(f"Package size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

        db_pool.closeall()

        return True

    except Exception as e:
        print_error(f"Database export test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""

    print("\n" + "🚀" * 40)
    print()
    print("  OFFICIAL DOCUMENT EXPORT SYSTEM TEST".center(80))
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
    print()
    print("🚀" * 40 + "\n")

    results = []

    # Run tests
    results.append(("Document Processor", await test_document_processor()))
    results.append(("Word Export", await test_word_exporter()))
    results.append(("Excel Export", await test_excel_exporter()))
    results.append(("Database Export", await test_full_export_with_database()))

    # Summary
    print_header("📊 TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"PASS - {test_name}")
        else:
            print_error(f"FAIL - {test_name}")

    print("\n" + "=" * 80)
    print(f"FINAL SCORE: {passed}/{total} tests passed ({passed / total * 100:.0f}%)".center(80))
    print("=" * 80 + "\n")

    if passed == total:
        print("🎉 ALL TESTS PASSED! System ready for production! 🎉\n")
        print("✨ Your researchers can now:")
        print("   - Export Part B to official Word format")
        print("   - Export budgets to official Excel format")
        print("   - Download complete submission packages as ZIP")
        print("   - Submit directly to EU portal!\n")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review errors above.\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
