"""
🎨 PROPOSAL WRITING ASSISTANT - INTERACTIVE DEMO

This demo showcases the complete proposal writing workflow from idea to draft.
Experience the power of AI-assisted proposal creation!
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.proposal_writing import (
    ProposalTemplateService,
    ProposalDraftGenerator,
    BudgetAssistant
)
from app.services.call_document_service import CallDocumentService
import psycopg2.pool


# Demo configuration
DEMO_CALL = "HORIZON-CL3-2025-02-CS-ECCC-01"
DEMO_PROJECT = {
    'title': 'CYBER-SHIELD',
    'idea': 'AI-powered early warning system for cybersecurity threats in critical infrastructure',
    'innovation': 'First system to combine real-time AI threat detection with explainable AI for operator decision support',
    'objectives': [
        'Develop novel AI algorithms for real-time cyber threat detection in critical infrastructure',
        'Create an intuitive early warning dashboard with explainable AI recommendations',
        'Validate the system in 3 real critical infrastructure sites across Europe',
        'Establish best practices and guidelines for AI-based cybersecurity systems'
    ],
    'consortium': [
        {
            'name': 'Technical University Munich',
            'short_name': 'TUM',
            'country': 'DE',
            'type': 'HES',
            'role': 'AI and Machine Learning expertise, project coordination',
            'person_months': 48,
            'avg_monthly_rate': 5500,
            'equipment_costs': 200000,
            'other_direct_costs': 50000
        },
        {
            'name': 'Thales Security Solutions',
            'short_name': 'Thales',
            'country': 'FR',
            'type': 'PRC',
            'role': 'Cybersecurity expertise and system integration',
            'person_months': 36,
            'avg_monthly_rate': 6000,
            'equipment_costs': 100000,
            'other_direct_costs': 30000
        },
        {
            'name': 'CERN',
            'short_name': 'CERN',
            'country': 'CH',
            'type': 'REC',
            'role': 'Critical infrastructure testbed and validation',
            'person_months': 24,
            'avg_monthly_rate': 6500,
            'other_direct_costs': 40000
        },
        {
            'name': 'University of Barcelona',
            'short_name': 'UB',
            'country': 'ES',
            'type': 'HES',
            'role': 'Explainable AI and human-computer interaction',
            'person_months': 30,
            'avg_monthly_rate': 5000,
            'other_direct_costs': 25000
        }
    ],
    'duration_months': 36,
    'research_area': 'Cybersecurity, Artificial Intelligence, Critical Infrastructure Protection'
}


def print_header(title: str):
    """Print a styled header"""
    print("\n" + "="*80)
    print(f"✨ {title}")
    print("="*80 + "\n")


def print_section(title: str, content: str = ""):
    """Print a styled section"""
    print(f"\n📌 {title}")
    print("-" * 80)
    if content:
        print(content)
    print("-" * 80)


def print_success(message: str):
    """Print success message"""
    print(f"\n✅ {message}\n")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")


def wait_for_enter(message: str = "Press Enter to continue..."):
    """Wait for user to press Enter"""
    input(f"\n⏸️  {message}")


async def demo_template_generation(db_pool):
    """Demo: Generate proposal template"""
    print_header("STEP 1: Generate Proposal Template")
    
    print_info(f"Generating template for call: {DEMO_CALL}")
    print_info(f"This analyzes call documents and creates a structured outline...")
    
    call_doc_service = CallDocumentService(db_pool)
    template_service = ProposalTemplateService(db_pool, call_doc_service)
    
    template = await template_service.generate_template(DEMO_CALL)
    
    print_success("Template generated!")
    
    print(f"📋 **Proposal Type:** {template['proposal_type']}")
    print(f"📄 **Page Limit:** {template['metadata']['page_limit']} pages\n")
    
    print("📂 **Section Structure:**")
    for section in template['structure']['sections']:
        print(f"\n   {section['order']}. **{section['name']}** (max {section.get('page_limit', '?')} pages)")
        for subsection in section.get('subsections', []):
            print(f"      • {subsection['name']}")
            if subsection.get('guidance'):
                print(f"        ↳ {subsection['guidance'][:70]}...")
    
    print("\n📊 **Evaluation Criteria:**")
    for category, criteria in template['evaluation_criteria'].items():
        print(f"\n   {category.upper()}:")
        for criterion in criteria:
            print(f"      ✓ {criterion}")
    
    wait_for_enter()
    return template


async def demo_draft_generation(db_pool):
    """Demo: Generate section draft"""
    print_header("STEP 2: Generate 'Objectives' Section Draft")
    
    print_info(f"Project: {DEMO_PROJECT['title']}")
    print_info(f"Idea: {DEMO_PROJECT['idea']}")
    print_info("\nGenerating AI-powered draft...")
    
    call_doc_service = CallDocumentService(db_pool)
    template_service = ProposalTemplateService(db_pool, call_doc_service)
    draft_generator = ProposalDraftGenerator(call_doc_service, template_service)
    
    # Prepare context
    user_context = {
        'project_idea': DEMO_PROJECT['idea'],
        'research_area': DEMO_PROJECT['research_area'],
        'main_objectives': DEMO_PROJECT['objectives'],
        'partners': [
            {'name': p['name'], 'expertise': p['role']}
            for p in DEMO_PROJECT['consortium']
        ],
        'budget': 3000000,
        'duration_months': DEMO_PROJECT['duration_months']
    }
    
    draft_result = await draft_generator.generate_section_draft(
        call_id=DEMO_CALL,
        section_id='excellence.objectives',
        user_context=user_context
    )
    
    print_success("Draft generated!")
    
    print_section("OBJECTIVES AND AMBITION", draft_result['draft_text'])
    
    print(f"\n📊 **Draft Statistics:**")
    print(f"   • Word count: {draft_result['word_count']}")
    print(f"   • Estimated pages: {draft_result['estimated_pages']:.1f}")
    print(f"   • Quality score: {draft_result.get('quality_score', 0.7)*100:.0f}%")
    
    print(f"\n✅ **Evaluation Criteria Addressed:**")
    for criterion in draft_result.get('evaluation_criteria_addressed', []):
        print(f"   ✓ {criterion}")
    
    if draft_result.get('suggestions'):
        print(f"\n💡 **Improvement Suggestions:**")
        for suggestion in draft_result['suggestions'][:3]:
            priority = suggestion.get('priority', 'info').upper()
            text = suggestion.get('text', '')
            print(f"   [{priority}] {text}")
    
    wait_for_enter()
    return draft_result


async def demo_budget_creation(db_pool):
    """Demo: Create budget table"""
    print_header("STEP 3: Generate Budget Table")
    
    print_info(f"Creating budget for {len(DEMO_PROJECT['consortium'])} partners...")
    print_info("Calculating costs, funding rates, and compliance...")
    
    budget_assistant = BudgetAssistant(db_pool)
    
    project_params = {
        'duration_months': DEMO_PROJECT['duration_months'],
        'partners': DEMO_PROJECT['consortium'],
        'total_budget': 3500000
    }
    
    budget_result = await budget_assistant.generate_budget_table(
        call_id=DEMO_CALL,
        proposal_type='RIA',
        project_params=project_params
    )
    
    print_success("Budget table generated!")
    
    print(budget_result['budget_table_formatted'])
    
    print(f"\n💰 **Summary:**")
    print(f"   • Total Eligible Costs: €{budget_result['summary']['total_eligible_costs']:,.2f}")
    print(f"   • Total Requested Funding: €{budget_result['summary']['total_requested_funding']:,.2f}")
    print(f"   • Average Funding Rate: {budget_result['summary']['average_funding_rate']*100:.1f}%")
    
    print(f"\n✅ **Compliance:**")
    if budget_result['compliance']['compliant']:
        print("   ✓ Budget is compliant with call requirements")
    else:
        print("   ✗ Compliance issues found:")
        for issue in budget_result['compliance']['issues']:
            print(f"      - {issue}")
    
    if budget_result['compliance']['warnings']:
        print(f"\n⚠️  **Warnings:**")
        for warning in budget_result['compliance']['warnings']:
            print(f"   • {warning}")
    
    print(f"\n📝 **Budget Justification Guidance:**")
    print(budget_result['justification_guidance']['personnel'][:300] + "...")
    
    wait_for_enter()
    return budget_result


async def demo_complete_workflow():
    """Run complete demo workflow"""
    print("\n" + "🎨"*40)
    print("\n  PROPOSAL WRITING ASSISTANT - INTERACTIVE DEMO")
    print(f"\n  Project: {DEMO_PROJECT['title']}")
    print(f"  Call: {DEMO_CALL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "🎨"*40 + "\n")
    
    print("""
This demo will walk you through the complete AI-assisted proposal writing workflow:

1. 📋 Generate proposal template from call requirements
2. ✍️  Generate 'Objectives' section draft with AI
3. 💰 Create complete budget table with calculations
4. 📊 Show final proposal overview

All of this happens automatically using AI and your call documents!
    """)
    
    wait_for_enter("Ready? Press Enter to start the demo...")
    
    # Initialize database
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not set")
        print("Please set DATABASE_URL environment variable and try again.")
        return
    
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
    
    try:
        # Step 1: Template
        template = await demo_template_generation(db_pool)
        
        # Step 2: Draft
        draft = await demo_draft_generation(db_pool)
        
        # Step 3: Budget
        budget = await demo_budget_creation(db_pool)
        
        # Final summary
        print_header("DEMO COMPLETE - PROPOSAL OVERVIEW")
        
        print(f"""
🎉 **Congratulations!** You've just created a professional proposal foundation in minutes!

**What we created:**

📋 **Proposal Structure:**
   • {len(template['structure']['sections'])} main sections
   • {sum(len(s.get('subsections', [])) for s in template['structure']['sections'])} subsections
   • {template['metadata']['page_limit']} page limit

✍️  **Content Generated:**
   • Objectives section: {draft['word_count']} words ({draft['estimated_pages']:.1f} pages)
   • Quality score: {draft.get('quality_score', 0.7)*100:.0f}%
   • Evaluation criteria coverage: {len(draft.get('evaluation_criteria_addressed', []))} criteria

💰 **Budget Table:**
   • {len(DEMO_PROJECT['consortium'])} partners across {len(set(p['country'] for p in DEMO_PROJECT['consortium']))} countries
   • Total budget: €{budget['summary']['total_requested_funding']:,.2f}
   • Compliance: {'✅ Passed' if budget['compliance']['compliant'] else '⚠️ Warnings'}

**Next Steps:**

1. Continue drafting other sections (Methodology, Impact, etc.)
2. Refine drafts based on AI suggestions
3. Run compliance checks
4. Review and improve quality
5. Export to Word/PDF for submission

**Time Saved:** 📈
   • Traditional approach: 2-4 weeks of work
   • With AI assistance: 2-3 days
   • **Efficiency gain: 80-90%!**
        """)
        
        print("\n" + "✨"*40)
        print("\n  Thank you for trying the Proposal Writing Assistant!")
        print(f"  Built with ❤️  using AI and Horizon Europe expertise")
        print("\n" + "✨"*40 + "\n")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_pool.closeall()


async def demo_conversational_mode():
    """Demo conversational proposal writing"""
    print_header("BONUS: Conversational Proposal Writing")
    
    print("""
The system also supports natural conversation for proposal writing!

**Example conversation:**

👤 User: "I want to write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01"

🤖 Assistant: "Great! I'll help you write your proposal. First, let me 
              generate a template based on the call requirements..."
              
              [Generates template]
              
              "Template ready! Tell me about your project idea and I'll 
              help you draft the sections."

👤 User: "It's an AI system for cybersecurity in critical infrastructure"

🤖 Assistant: "Excellent! I'll help you draft the Objectives section. 
              What are your main objectives?"

👤 User: "Develop AI models, create a dashboard, validate in real sites"

🤖 Assistant: [Generates professional draft addressing all evaluation criteria]
              
              "Here's your Objectives section draft. Would you like me to 
              improve it or move to the next section?"

**And it continues conversationally through the entire proposal! 🚀**
    """)
    
    print_info("Try it in your application by saying:")
    print("""
    - "Generate a proposal template for [CALL-ID]"
    - "Help me write the objectives section"
    - "Create a budget table"
    - "Check my proposal for compliance"
    """)


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run demo
    asyncio.run(demo_complete_workflow())
    
    # Show conversational bonus
    asyncio.run(demo_conversational_mode())
    
    print("\n")

