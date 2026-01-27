#!/usr/bin/env python3
"""
Script to update the Supabase schema to add 'additional_resource' to document_type constraint.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.supabase_client import SupabaseVectorStore


def update_schema():
    """Update the database schema to add 'additional_resource' to document_type constraint."""
    try:
        # Initialize Supabase client
        supabase = SupabaseVectorStore()

        # Test connection first
        if not supabase.test_connection():
            print("❌ Failed to connect to Supabase")
            return False

        print("✅ Connected to Supabase successfully")

        # Update the document_type constraint to include 'additional_resource'
        # We need to drop the existing constraint and add a new one
        update_query = """
        ALTER TABLE horizon_documents DROP CONSTRAINT IF EXISTS horizon_documents_document_type_check;
        ALTER TABLE horizon_documents ADD CONSTRAINT horizon_documents_document_type_check
        CHECK (document_type IN ('work_programme', 'programme_guide', 'call_text', 'grant_agreement', 'faq', 'manual', 'policy', 'template', 'additional_resource'));
        """

        # Execute the query
        # Note: Supabase doesn't allow direct DDL through the REST API, so we'll need to do this differently
        print("⚠️  Schema update needs to be done through Supabase SQL editor")
        print("Please run the following SQL in your Supabase SQL editor:")
        print()
        print(update_query)
        print()
        print("After running the SQL, you can proceed with the ingestion.")

        return True

    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        return False


if __name__ == "__main__":
    success = update_schema()
    if not success:
        sys.exit(1)
    else:
        print("✅ Schema update instructions provided")
