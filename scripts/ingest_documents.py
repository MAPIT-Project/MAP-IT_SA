#!/usr/bin/env python3
"""
Script to ingest downloaded Horizon Europe documents into the RAG system.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def ingest_documents():
    """Ingest all downloaded Horizon Europe documents."""

    try:
        # Import services
        from app.services.ingestion_service import DocumentIngestionService

        print("🚀 Initializing ingestion service...")
        ingestion_service = DocumentIngestionService()

        # Check service status
        stats = ingestion_service.get_service_stats()
        print("📊 Service Status:")
        print(f"   Supabase Connected: {stats.get('supabase_connected', False)}")
        print(
            f"   Embedding Service Ready: {stats.get('embedding_stats', {}).get('cache_enabled', False)}"
        )

        if not stats.get("supabase_connected", False):
            print("❌ Supabase connection failed. Check your configuration.")
            return False

        # Find downloaded documents
        download_dir = Path("downloads/horizon_europe")

        if not download_dir.exists():
            print(f"❌ Download directory not found: {download_dir}")
            print("💡 Run 'python scripts/download_horizon_documents.py' first")
            return False

        # Get all PDF files
        pdf_files = list(download_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"❌ No PDF files found in {download_dir}")
            return False

        print(f"📄 Found {len(pdf_files)} PDF files to ingest")

        # Document type mapping based on filename
        type_mapping = {
            "general": "work_programme",
            "climate_energy": "work_programme",
            "programme_guide": "programme_guide",
            "aga_annotated": "grant_agreement",
            "digital_industry": "work_programme",
            "health": "work_programme",
            "culture": "work_programme",
            "food_bioeconomy": "work_programme",
            "civil_security": "work_programme",
            "eic": "work_programme",
        }

        # Ingest each document
        successful_ingestions = 0
        failed_ingestions = []

        for pdf_file in pdf_files:
            print(f"\n📄 Processing: {pdf_file.name}")

            # Determine document type
            document_type = "work_programme"  # default
            for key, doc_type in type_mapping.items():
                if key in pdf_file.name.lower():
                    document_type = doc_type
                    break

            # Determine programme year
            programme_year = "2023-2024"  # Most documents are from this period

            try:
                # Ingest the document
                result = ingestion_service.ingest_file(
                    file_path=str(pdf_file),
                    document_type=document_type,
                    programme_year=programme_year,
                    metadata={
                        "source": "official_eu_portal",
                        "language": "en",
                        "ingested_by": "automated_script",
                    },
                )

                if result.get("success"):
                    print(f"✅ Ingested: {pdf_file.name}")
                    print(f"   Document ID: {result.get('document_id')}")
                    print(f"   Chunks Created: {result.get('chunks_created')}")
                    print(f"   Document Type: {result.get('document_type')}")
                    successful_ingestions += 1
                else:
                    print(f"❌ Failed to ingest: {pdf_file.name}")
                    print(f"   Error: {result.get('error')}")
                    failed_ingestions.append(pdf_file.name)

            except Exception as e:
                print(f"❌ Exception during ingestion of {pdf_file.name}: {e}")
                failed_ingestions.append(pdf_file.name)

            # Small delay between ingestions
            await asyncio.sleep(1)

        # Summary
        print("\n📊 Ingestion Summary:")
        print(f"✅ Successful: {successful_ingestions}/{len(pdf_files)}")
        print(f"❌ Failed: {len(failed_ingestions)}")

        if failed_ingestions:
            print("Failed ingestions:")
            for name in failed_ingestions:
                print(f"  - {name}")

        # Get final database stats
        try:
            final_stats = ingestion_service.supabase.get_document_stats()
            print("\n📈 Database Stats:")
            print(f"   Total Documents: {final_stats.get('total_documents', 0)}")
            print(f"   Total Chunks: {final_stats.get('total_chunks', 0)}")
            print(f"   Documents by Type: {final_stats.get('documents_by_type', {})}")
        except Exception as e:
            print(f"⚠️ Could not get final stats: {e}")

        return successful_ingestions > 0

    except Exception as e:
        print(f"❌ Ingestion process failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Horizon Europe document ingestion...")

    # Run the async function
    success = asyncio.run(ingest_documents())

    if success:
        print("🎉 Document ingestion completed!")
        print("\n💡 Next steps:")
        print("1. Test the system: python -m app.main")
        print(
            "2. Try a query: curl -X POST http://localhost:8000/api/rag/query -H 'Content-Type: application/json' -d '{\"question\": \"What are the eligibility criteria for Horizon Europe?\"}'"
        )
    else:
        print("💥 Document ingestion failed!")
        sys.exit(1)
