#!/usr/bin/env python3
"""
Script to process procedural documents for enhanced FAQ handling.
Adds procedural guides for portal navigation, filtering, and funding types.
"""

import os
import sys
import json
from pathlib import Path
import shutil

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

def process_procedural_documents():
    """Process procedural documents and add them to the ingestion pipeline."""
    
    # Source directory for procedural documents
    source_dir = Path("downloads/horizon_europe_comprehensive/procedural_guides")
    
    # Destination directory for processed documents
    dest_dir = Path("processed_docs/horizon_europe")
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Processing procedural documents from: {source_dir}")
    print(f"📁 Destination: {dest_dir}")
    
    # Check if source directory exists and has files
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return False
    
    procedural_files = list(source_dir.glob("*.pdf"))
    if not procedural_files:
        print("❌ No procedural PDF files found")
        return False
    
    print(f"📄 Found {len(procedural_files)} procedural documents:")
    for file in procedural_files:
        print(f"   - {file.name}")
    
    # Load existing processed documents list
    processed_docs_file = dest_dir / "processed_documents.json"
    processed_docs = []
    
    if processed_docs_file.exists():
        try:
            with open(processed_docs_file, 'r', encoding='utf-8') as f:
                processed_docs = json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading processed documents: {e}")
            processed_docs = []
    
    # Process each procedural document
    processed_count = 0
    for pdf_file in procedural_files:
        try:
            # Create document metadata
            doc_metadata = {
                "filename": pdf_file.name,
                "filepath": str(pdf_file),
                "document_type": "procedural_guide",
                "source": "EU Funding & Tenders Portal",
                "year": "2021-2027",
                "cluster": "general",
                "description": _get_document_description(pdf_file.name),
                "processed": False,
                "processing_date": None
            }
            
            # Check if document already exists in processed list
            existing_doc = next((doc for doc in processed_docs if doc.get("filename") == pdf_file.name), None)
            
            if existing_doc:
                print(f"⚠️ Document already processed: {pdf_file.name}")
                continue
            
            # Add to processed documents list
            processed_docs.append(doc_metadata)
            processed_count += 1
            
            print(f"✅ Added to processing queue: {pdf_file.name}")
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file.name}: {e}")
    
    # Save updated processed documents list
    try:
        with open(processed_docs_file, 'w', encoding='utf-8') as f:
            json.dump(processed_docs, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Updated processed documents list: {processed_docs_file}")
        
    except Exception as e:
        print(f"❌ Error saving processed documents: {e}")
        return False
    
    print(f"\n🎉 Successfully queued {processed_count} procedural documents for processing")
    print("\n💡 Next steps:")
    print("1. Run the document processing: python scripts/process_comprehensive_docs.py")
    print("2. Ingest processed documents: python scripts/ingest_comprehensive_docs.py")
    print("3. Test enhanced FAQ responses with procedural questions")
    
    return True

def _get_document_description(filename):
    """Get descriptive text for different procedural documents."""
    descriptions = {
        "lump_sum_grants_guide.pdf": "Guide to managing lump-sum grants in Horizon Europe - explains lump-sum funding rules, eligibility, reporting, and differences from actual cost funding",
        "operations_manual.pdf": "Horizon Europe Operations Manual - comprehensive guide to portal navigation, filtering, call vs topic differentiation, and administrative procedures",
        "eu_portal_faq.pdf": "EU Funding & Tenders Portal FAQ - answers common questions about portal usage, filtering, and call/topic navigation",
        "portal_user_guide.pdf": "Portal User Guide - detailed instructions for using the EU Funding & Tenders Portal interface"
    }
    
    return descriptions.get(filename, f"Procedural guide: {filename}")

if __name__ == "__main__":
    print("🚀 Starting procedural document processing...")
    success = process_procedural_documents()
    
    if success:
        print("\n🎉 Procedural document processing completed!")
    else:
        print("\n💥 Procedural document processing failed!")
        sys.exit(1)