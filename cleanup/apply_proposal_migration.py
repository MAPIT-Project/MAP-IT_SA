"""
Apply Proposal Writing System Migration to Supabase

This script applies the proposal writing database migration using
credentials from environment variables.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def apply_migration():
    """Apply the proposal writing system migration"""

    print("\n" + "=" * 80)
    print("🚀 APPLYING PROPOSAL WRITING SYSTEM MIGRATION")
    print("=" * 80 + "\n")

    # Get database URL
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("\nPlease ensure DATABASE_URL is set in your .env file or environment")
        print("Example: DATABASE_URL=postgresql://user:pass@host:port/database")
        return False

    # Mask password in URL for display
    display_url = db_url
    if "@" in db_url and ":" in db_url:
        parts = db_url.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split(":")
            display_url = f"{user_pass[0]}:****@{parts[1]}"

    print(f"📡 Connecting to database: {display_url}\n")

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        print("✅ Connected successfully!\n")

        # Read migration file
        migration_file = "migration/005_proposal_writing_system.sql"

        print(f"📄 Reading migration file: {migration_file}\n")

        with open(migration_file) as f:
            migration_sql = f.read()

        print(f"📊 Migration file size: {len(migration_sql)} characters\n")

        # Execute migration
        print("🔧 Applying migration...\n")

        try:
            cursor.execute(migration_sql)
            conn.commit()

            print("✅ Migration applied successfully!\n")

            # Verify tables were created
            print("🔍 Verifying created tables...\n")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'proposal%'
                ORDER BY table_name
            """
            )

            tables = cursor.fetchall()

            print("📋 Proposal-related tables created:")
            for table in tables:
                print(f"   ✓ {table[0]}")

            print(f"\n✅ Total: {len(tables)} tables created\n")

            # Check views
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'public'
                AND table_name LIKE 'proposal%'
            """
            )

            views = cursor.fetchall()

            if views:
                print("📊 Views created:")
                for view in views:
                    print(f"   ✓ {view[0]}")
                print()

            # Check functions
            cursor.execute(
                """
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_name LIKE '%proposal%'
                OR routine_name LIKE 'calculate%'
                OR routine_name LIKE 'update_%'
            """
            )

            functions = cursor.fetchall()

            if functions:
                print("⚙️  Functions created:")
                for func in functions:
                    print(f"   ✓ {func[0]}")
                print()

            print("=" * 80)
            print("🎉 MIGRATION COMPLETE!")
            print("=" * 80)
            print("\n✨ Your proposal writing system is ready to use!")
            print("\n📚 Next steps:")
            print("   1. Run the demo: python demo_proposal_writing.py")
            print("   2. Run tests: python test_proposal_writing_system.py")
            print("   3. Start using: 'Generate template for HORIZON-CL3-2025-02-CS-ECCC-01'")
            print()

            return True

        except psycopg2.Error as e:
            print(f"❌ Error applying migration: {e}")
            conn.rollback()
            return False

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection error: {e}")
        print("\nPlease check:")
        print("   - DATABASE_URL is correct")
        print("   - Database is accessible")
        print("   - Network connection is working")
        return False

    except FileNotFoundError:
        print(f"❌ Migration file not found: {migration_file}")
        print("\nPlease ensure the migration file exists at:")
        print(f"   {os.path.abspath(migration_file)}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if "conn" in locals():
            cursor.close()
            conn.close()
            print("📡 Database connection closed\n")


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
