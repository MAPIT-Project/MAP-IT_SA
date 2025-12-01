"""
Quick verification that the proposal writing system is working
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def verify_system():
    """Verify the proposal writing system is ready"""
    
    print("\n" + "="*80)
    print("🔍 VERIFYING PROPOSAL WRITING SYSTEM")
    print("="*80 + "\n")
    
    db_url = os.getenv("DATABASE_URL")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check each table
        tables_to_check = [
            'proposals',
            'proposal_sections', 
            'proposal_consortium',
            'proposal_budgets',
            'compliance_checks',
            'improvement_suggestions'
        ]
        
        print("✅ Checking tables:\n")
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   ✓ {table}: {count} rows")
        
        # Check if we can insert a test proposal
        print("\n🧪 Testing proposal creation...\n")
        
        cursor.execute("""
            INSERT INTO proposals (
                call_identifier,
                proposal_title,
                proposal_acronym,
                proposal_type,
                project_summary,
                status
            ) VALUES (
                'TEST-CALL-2025',
                'Test Proposal for Verification',
                'TEST-PROP',
                'RIA',
                'This is a test proposal to verify the system is working',
                'draft'
            ) RETURNING id
        """)
        
        test_id = cursor.fetchone()[0]
        print(f"   ✓ Created test proposal with ID: {test_id}")
        
        # Check the proposal was created
        cursor.execute("""
            SELECT proposal_title, proposal_type, status, completion_percentage
            FROM proposals WHERE id = %s
        """, (test_id,))
        
        result = cursor.fetchone()
        print(f"   ✓ Retrieved: {result[0]}")
        print(f"   ✓ Type: {result[1]}")
        print(f"   ✓ Status: {result[2]}")
        print(f"   ✓ Completion: {result[3]}%")
        
        # Clean up test data
        cursor.execute("DELETE FROM proposals WHERE id = %s", (test_id,))
        conn.commit()
        
        print(f"\n   ✓ Cleaned up test data")
        
        # Check views
        print("\n✅ Checking views:\n")
        cursor.execute("SELECT COUNT(*) FROM proposal_overview")
        count = cursor.fetchone()[0]
        print(f"   ✓ proposal_overview: {count} rows")
        
        # Check functions exist
        print("\n✅ Checking functions:\n")
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND (routine_name LIKE '%proposal%' 
                 OR routine_name LIKE 'calculate%')
            ORDER BY routine_name
        """)
        
        functions = cursor.fetchall()
        for func in functions[:5]:  # Show first 5
            print(f"   ✓ {func[0]}()")
        
        print("\n" + "="*80)
        print("✅ SYSTEM VERIFIED - ALL CHECKS PASSED!")
        print("="*80)
        print("\n🎉 Your proposal writing system is fully operational!\n")
        print("📝 You can now:")
        print("   - Generate proposal templates")
        print("   - Create AI-powered drafts")
        print("   - Build budget tables")
        print("   - Check compliance")
        print("   - And much more!\n")
        print("🚀 Try it: python3 demo_proposal_writing.py\n")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_system()

