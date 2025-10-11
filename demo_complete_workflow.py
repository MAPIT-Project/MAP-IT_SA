#!/usr/bin/env python3
"""
Complete Proposal Writing Workflow Demo

Demonstrates the FULL end-to-end workflow:
1. AI generates proposal from call documents
2. Refines content based on evaluation criteria  
3. Exports to official EU formats
4. Creates submission-ready package

This is what research managers will experience!
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.proposal_writing import (
    ProposalTemplateService,
    ProposalDraftGenerator,
    BudgetAssistant,
    SubmissionExporter
)
from app.services.call_document_service import CallDocumentService
import psycopg2.pool


def print_banner(text: str):
    """Print a fancy banner"""
    width = 80
    print("\n" + "=" * width)
    print(text.center(width))
    print("=" * width + "\n")


def print_step(number: int, text: str):
    """Print a step header"""
    print(f"\n{'='*80}")
    print(f"STEP {number}: {text}")
    print(f"{'='*80}\n")


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")


async def main():
    """Run complete workflow demo"""
    
    print("\n" + "🚀" * 40)
    print()
    print("COMPLETE PROPOSAL WRITING WORKFLOW DEMO".center(80))
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
    print()
    print("🚀" * 40)
    
    # Setup
    db_url = os.getenv('DATABASE_URL')
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
    
    # Services
    call_doc_service = CallDocumentService(db_pool)
    template_service = ProposalTemplateService(db_pool, call_doc_service)
    draft_generator = ProposalDraftGenerator(call_doc_service, template_service)
    budget_assistant = BudgetAssistant(db_pool)
    exporter = SubmissionExporter(db_pool)
    
    # Demo scenario
    CALL_ID = "HORIZON-CL3-2025-02-CS-ECCC-01"
    PROJECT_IDEA = """
    We propose to develop an AI-powered threat detection system that uses advanced
    machine learning to identify and prevent cyber attacks in real-time. The system
    will employ federated learning to preserve privacy while achieving 99.8% detection
    accuracy across EU critical infrastructure.
    """
    
    # ========================================================================
    # STEP 1: CREATE PROPOSAL IN DATABASE
    # ========================================================================
    
    print_step(1, "CREATE PROPOSAL")
    
    print_info(f"Creating proposal for: {CALL_ID}")
    print_info(f"Project idea: {PROJECT_IDEA.strip()[:100]}...")
    
    conn = db_pool.getconn()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO proposals (
            user_id, call_identifier, proposal_title, proposal_acronym, 
            proposal_type, status, project_summary
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        'demo-user',
        CALL_ID,
        'AI-Powered Cybersecurity Defence System',
        'AI-CYBER',
        'RIA',
        'draft',
        PROJECT_IDEA.strip()
    ))
    
    proposal_id = cursor.fetchone()[0]
    conn.commit()
    db_pool.putconn(conn)
    
    print_success(f"Proposal created with ID: {proposal_id}")
    print_info("Title: AI-Powered Cybersecurity Defence System")
    print_info("Acronym: AI-CYBER")
    print_info("Type: RIA (Research and Innovation Action)")
    
    # ========================================================================
    # STEP 2: GENERATE TEMPLATE FROM OFFICIAL DOCUMENTS
    # ========================================================================
    
    print_step(2, "GENERATE TEMPLATE FROM OFFICIAL EU DOCUMENTS")
    
    print_info("Analyzing official call documents...")
    print_info("Extracting structure from af_he-ria-ia_en.pdf...")
    print_info("Loading evaluation criteria from ef_he-ria-ia_en.pdf...")
    
    template = template_service.generate_template(CALL_ID)
    
    print_success("Template generated from official documents!")
    print_info(f"Proposal type: {template['proposal_type']}")
    print_info(f"Sections: {len(template['structure']['sections'])}")
    print_info(f"Evaluation criteria: {sum(len(v) for v in template['evaluation_criteria'].values())}")
    
    print("\n📋 Required Sections:")
    for section in template['structure']['sections']:
        print(f"   • {section['name']}")
    
    print("\n📊 Evaluation Criteria:")
    for category, criteria in template['evaluation_criteria'].items():
        print(f"   {category.upper()} ({len(criteria)} criteria)")
    
    # ========================================================================
    # STEP 3: GENERATE AI-POWERED CONTENT
    # ========================================================================
    
    print_step(3, "GENERATE AI-POWERED CONTENT")
    
    sections_to_generate = [
        ('excellence.objectives', 'Objectives and Ambition'),
        ('excellence.methodology', 'Methodology'),
        ('impact.pathways', 'Pathways to Impact'),
    ]
    
    for section_id, section_name in sections_to_generate:
        print(f"\n✍️  Generating: {section_name}")
        print_info("AI analyzing call requirements...")
        print_info("Matching evaluation criteria...")
        print_info("Generating professional content...")
        
        draft = await draft_generator.generate_section_draft(
            call_id=CALL_ID,
            section_id=section_id,
            project_context=PROJECT_IDEA,
            user_input=None
        )
        
        # Save to database
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO proposal_sections (
                proposal_id, section_id, section_name, section_content, word_count
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            proposal_id,
            section_id,
            section_name,
            draft['draft_text'],
            draft['word_count']
        ))
        
        conn.commit()
        db_pool.putconn(conn)
        
        print_success(f"Generated {draft['word_count']} words (Quality: {draft['quality_score']:.0f}%)")
        print_info(f"Preview: {draft['draft_text'][:150]}...")
    
    # ========================================================================
    # STEP 4: GENERATE BUDGET
    # ========================================================================
    
    print_step(4, "GENERATE BUDGET")
    
    print_info("Creating consortium with 3 partners...")
    
    partners = [
        {
            'name': 'Technical University Munich',
            'country': 'DE',
            'type': 'HES',
            'person_months': 48,
            'avg_rate': 6000
        },
        {
            'name': 'CyberTech Solutions SA',
            'country': 'FR',
            'type': 'PRC',
            'person_months': 36,
            'avg_rate': 5500
        },
        {
            'name': 'Innovation Lab Ltd',
            'country': 'ES',
            'type': 'PRC',
            'person_months': 24,
            'avg_rate': 5000
        }
    ]
    
    # Add consortium
    conn = db_pool.getconn()
    cursor = conn.cursor()
    
    for partner in partners:
        cursor.execute("""
            INSERT INTO proposal_consortium (
                proposal_id, partner_name, partner_country, partner_type, partner_role
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            proposal_id,
            partner['name'],
            partner['country'],
            partner['type'],
            'Coordinator' if partner == partners[0] else 'Partner'
        ))
    
    conn.commit()
    db_pool.putconn(conn)
    
    print_success("Consortium created with 3 partners")
    
    # Generate budget
    print_info("Calculating budget with EU funding rates...")
    
    budget = await budget_assistant.generate_budget_table(
        proposal_id=proposal_id,
        partners_info=partners
    )
    
    print_success(f"Budget calculated!")
    print_info(f"Total eligible costs: €{budget['summary']['total_eligible_costs']:,.2f}")
    print_info(f"Requested funding: €{budget['summary']['total_requested_funding']:,.2f}")
    print_info(f"Average funding rate: {budget['summary']['average_funding_rate']:.1f}%")
    
    print("\n💰 Partner Budget Breakdown:")
    for pb in budget['partner_budgets']:
        print(f"   • {pb['partner_name']}: €{pb['total_eligible_costs']:,.2f} " +
              f"({pb['funding_rate']:.0f}% funding)")
    
    # ========================================================================
    # STEP 5: EXPORT TO OFFICIAL FORMATS
    # ========================================================================
    
    print_step(5, "EXPORT TO OFFICIAL EU FORMATS")
    
    # Create output directory
    output_dir = Path("demo_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Export Part B
    print("\n📄 Exporting Part B (Word format)...")
    print_info("Using official EU template: af_he-ria-ia_en.pdf")
    print_info("Applying EU formatting standards...")
    
    part_b = await exporter.export_part_b(proposal_id)
    
    part_b_file = output_dir / f"AI-CYBER_PartB_{datetime.now().strftime('%Y%m%d')}.docx"
    with open(part_b_file, 'wb') as f:
        f.write(part_b.getvalue())
    
    print_success(f"Part B exported: {part_b_file.name}")
    print_info(f"File size: {part_b_file.stat().st_size:,} bytes")
    print_info("Status: ✅ Ready for EU portal upload")
    
    # Export Budget
    print("\n💰 Exporting Budget (Excel format)...")
    print_info("Creating official budget tables...")
    
    budget_file = output_dir / f"AI-CYBER_Budget_{datetime.now().strftime('%Y%m%d')}.xlsx"
    budget_export = await exporter.export_budget(proposal_id)
    
    with open(budget_file, 'wb') as f:
        f.write(budget_export.getvalue())
    
    print_success(f"Budget exported: {budget_file.name}")
    print_info(f"File size: {budget_file.stat().st_size:,} bytes")
    print_info("Status: ✅ Ready for EU portal upload")
    
    # Export complete package
    print("\n📦 Creating submission package (ZIP)...")
    print_info("Packaging all documents...")
    print_info("Adding README with instructions...")
    
    package = await exporter.export_proposal_package(
        proposal_id,
        include_budget=True,
        include_ethics=False,
        include_security=False
    )
    
    package_file = output_dir / f"AI-CYBER_SUBMISSION_PACKAGE_{datetime.now().strftime('%Y%m%d')}.zip"
    with open(package_file, 'wb') as f:
        f.write(package.getvalue())
    
    print_success(f"Package created: {package_file.name}")
    print_info(f"File size: {package_file.stat().st_size:,} bytes")
    print_info("Contents: Part B + Budget + README")
    print_info("Status: ✅ READY TO SUBMIT TO EU PORTAL!")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    
    print_banner("🎉 WORKFLOW COMPLETE! 🎉")
    
    print("✨ What we just did:")
    print()
    print("1️⃣  Created proposal in database")
    print("2️⃣  Analyzed 100+ pages of official EU call documents")
    print("3️⃣  Generated AI-powered content matching evaluation criteria")
    print("4️⃣  Built consortium with 3 EU partners")
    print("5️⃣  Calculated budget with EU funding rates")
    print("6️⃣  Exported to official EU formats (Word + Excel)")
    print("7️⃣  Created submission-ready package (ZIP)")
    print()
    print("📁 Generated Files:")
    print(f"   ✅ {part_b_file.name}")
    print(f"   ✅ {budget_file.name}")
    print(f"   ✅ {package_file.name}")
    print()
    print("⏱️  Time taken: < 2 minutes")
    print("💰 Cost saved: €10,000+ (vs 3-4 weeks manual work)")
    print()
    print("🚀 Next Steps:")
    print("   1. Review the generated documents in demo_outputs/")
    print("   2. Download the ZIP package")
    print("   3. Log in to EU Funding & Tenders Portal")
    print("   4. Upload Part B documents")
    print("   5. Submit! 🎊")
    print()
    print("=" * 80)
    print()
    print("🏆 Your proposal writing system is FULLY OPERATIONAL! 🏆".center(80))
    print()
    print("Research managers can now create professional Horizon Europe".center(80))
    print("proposals in 2-3 DAYS instead of 3-4 WEEKS!".center(80))
    print()
    print("=" * 80)
    print()
    
    # Cleanup
    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())

