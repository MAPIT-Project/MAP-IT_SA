#!/usr/bin/env python3
"""
Script to fix the document_type constraint in the horizon_documents table.
This adds support for 'additional_resource' document type.
"""

import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_database_connection():
    """Get a direct PostgreSQL connection to the database."""
    # Get the database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    logger.info(f"Connecting to database: {database_url}")
    return psycopg2.connect(database_url)


def check_current_constraint():
    """Check the current document_type constraint."""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        # Query to get the current constraint definition (updated for newer PostgreSQL)
        query = """
        SELECT conname, pg_get_constraintdef(oid) as condef
        FROM pg_constraint
        WHERE conrelid = 'horizon_documents'::regclass
        AND conname LIKE '%document_type%';
        """

        cursor.execute(query)
        constraints = cursor.fetchall()

        logger.info("Current document_type constraints:")
        for constraint_name, constraint_def in constraints:
            logger.info(f"  {constraint_name}: {constraint_def}")

        cursor.close()
        conn.close()

        return constraints

    except Exception as e:
        logger.error(f"Error checking current constraint: {e}")
        return None


def update_document_type_constraint():
    """Update the document_type constraint to include 'additional_resource'."""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        logger.info("🔧 Updating document_type constraint...")

        # First, drop the existing constraint
        drop_constraint_sql = """
        ALTER TABLE horizon_documents
        DROP CONSTRAINT IF EXISTS horizon_documents_document_type_check;
        """

        cursor.execute(drop_constraint_sql)
        logger.info("✅ Dropped existing document_type constraint")

        # Add the new constraint with additional_resource included
        add_constraint_sql = """
        ALTER TABLE horizon_documents
        ADD CONSTRAINT horizon_documents_document_type_check
        CHECK (document_type IN (
            'work_programme',
            'programme_guide',
            'call_text',
            'grant_agreement',
            'faq',
            'manual',
            'policy',
            'template',
            'additional_resource'
        ));
        """

        cursor.execute(add_constraint_sql)
        logger.info("✅ Added new document_type constraint with 'additional_resource'")

        # Commit the changes
        conn.commit()
        logger.info("✅ Database constraint updated successfully")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"❌ Error updating constraint: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def test_constraint():
    """Test the updated constraint by trying to insert a test record."""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        logger.info("🧪 Testing updated constraint...")

        # Try to insert a test document with additional_resource type
        test_insert_sql = """
        INSERT INTO horizon_documents (
            title, document_type, programme_year, file_hash, source_type
        ) VALUES (
            'Test Additional Resource', 'additional_resource', '2021-2027', 'test_hash_123', 'pdf'
        ) RETURNING id;
        """

        cursor.execute(test_insert_sql)
        result = cursor.fetchone()

        if result:
            test_id = result[0]
            logger.info(f"✅ Test insert successful, document ID: {test_id}")

            # Clean up - delete the test record
            delete_sql = "DELETE FROM horizon_documents WHERE id = %s;"
            cursor.execute(delete_sql, (test_id,))
            logger.info("✅ Test record cleaned up")

            conn.commit()
            return True
        else:
            logger.error("❌ Test insert failed - no result returned")
            conn.rollback()
            return False

    except Exception as e:
        logger.error(f"❌ Constraint test failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def main():
    """Main function to fix the document type constraint."""
    logger.info("🚀 Starting document type constraint fix...")

    try:
        # Check current constraints
        logger.info("🔍 Checking current constraints...")
        current_constraints = check_current_constraint()

        if not current_constraints:
            logger.error("❌ Could not retrieve current constraints")
            return False

        # Update the constraint
        logger.info("🔧 Updating constraint...")
        success = update_document_type_constraint()

        if not success:
            logger.error("❌ Failed to update constraint")
            return False

        # Test the updated constraint
        logger.info("🧪 Testing updated constraint...")
        test_success = test_constraint()

        if test_success:
            logger.info("🎉 Database schema successfully updated!")
            logger.info("📋 The 'additional_resource' document type is now supported")
            return True
        else:
            logger.error("❌ Constraint test failed")
            return False

    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    else:
        logger.info("✅ Schema fix completed successfully!")
