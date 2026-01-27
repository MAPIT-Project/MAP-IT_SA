#!/usr/bin/env python3
"""
Simple script to add procedural documents to the processed_documents.json file
"""

import json
from datetime import datetime
from pathlib import Path


def add_procedural_documents():
    """Add procedural documents to the processed documents list."""

    processed_docs_file = Path("processed_docs/horizon_europe/processed_documents.json")

    if not processed_docs_file.exists():
        print(f"❌ Processed documents file not found: {processed_docs_file}")
        return False

    # Load existing processed documents
    with open(processed_docs_file, encoding="utf-8") as f:
        processed_docs = json.load(f)

    # Procedural documents to add
    procedural_docs = [
        {
            "filename": "lump_sum_grants_guide.pdf",
            "filepath": "processed_docs/horizon_europe/procedural_guides/lump_sum_grants_guide.pdf",
            "file_size": 300446,
            "file_type": ".pdf",
            "document_type": "procedural_guide",
            "cluster": "general",
            "cluster_name": "Funding Procedures",
            "programme_year": "2021-2027",
            "processing_date": datetime.now().isoformat(),
            "total_chunks": 0,
            "total_words": 0,
            "total_characters": 0,
            "description": "Guide to managing lump-sum grants in Horizon Europe - explains lump-sum funding rules, eligibility, reporting, and differences from actual cost funding",
        },
        {
            "filename": "operations_manual.pdf",
            "filepath": "processed_docs/horizon_europe/procedural_guides/operations_manual.pdf",
            "file_size": 1982084,
            "file_type": ".pdf",
            "document_type": "procedural_guide",
            "cluster": "general",
            "cluster_name": "Portal Operations",
            "programme_year": "2021-2027",
            "processing_date": datetime.now().isoformat(),
            "total_chunks": 0,
            "total_words": 0,
            "total_characters": 0,
            "description": "Horizon Europe Operations Manual - comprehensive guide to portal navigation, filtering, call vs topic differentiation, and administrative procedures",
        },
    ]

    # Add procedural documents
    added_count = 0
    for doc in procedural_docs:
        filename = doc["filename"]
        if filename not in processed_docs:
            processed_docs[filename] = {"metadata": doc, "chunks": [], "full_text": ""}
            added_count += 1
            print(f"✅ Added: {filename}")
        else:
            print(f"⚠️ Already exists: {filename}")

    # Save updated processed documents
    with open(processed_docs_file, "w", encoding="utf-8") as f:
        json.dump(processed_docs, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n🎉 Added {added_count} procedural documents to processing queue")
    print("💡 Next: Run the document processing script to extract text and create chunks")

    return True


if __name__ == "__main__":
    print("🚀 Adding procedural documents to processing queue...")
    success = add_procedural_documents()

    if success:
        print("\n✅ Procedural documents added successfully!")
    else:
        print("\n❌ Failed to add procedural documents")
