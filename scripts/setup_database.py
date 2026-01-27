#!/usr/bin/env python3
"""
Script to set up the Horizon Europe RAG database tables in Supabase.
"""

import os
import sys
from pathlib import Path

import psycopg2

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_database():
    """Set up the database tables and functions."""

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return False

    print(f"🔗 Connecting to database: {db_url}")

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("✅ Connected to database")

        # Read and execute the setup SQL
        sql_file = Path(__file__).parent / "setup_supabase.sql"

        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return False

        with open(sql_file) as f:
            sql_content = f.read()

        print("📄 Executing database setup script...")

        # Try to execute the entire SQL script as one block first
        try:
            cursor.execute(sql_content)
            print("✅ SQL script executed successfully as one block")
        except Exception as e:
            print(f"⚠️ Full script execution failed, falling back to individual statements: {e}")

            # Split SQL into individual statements and execute
            statements = sql_content.split(";")

            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        cursor.execute(statement)
                        print(f"✅ Executed statement {i + 1}/{len(statements)}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"⚠️ Statement {i + 1} - already exists: {str(e)[:100]}...")
                        else:
                            print(f"❌ Error in statement {i + 1}: {e}")
                            print(f"Statement: {statement[:200]}...")

        # Verify tables were created
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'horizon_%' OR table_name LIKE '%chunk%' OR table_name LIKE '%embedding%'
        """
        )

        tables = cursor.fetchall()
        print(f"✅ Database setup completed. Tables created: {[t[0] for t in tables]}")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Setting up Horizon Europe RAG database...")
    success = setup_database()

    if success:
        print("🎉 Database setup completed successfully!")
    else:
        print("💥 Database setup failed!")
        sys.exit(1)
