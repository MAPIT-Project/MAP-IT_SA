#!/bin/bash
# Automated script to update Horizon Europe documents for the RAG system
# This script can be run manually or scheduled (e.g., via cron) to keep the system current

echo "🔄 Starting Horizon Europe document update process..."
echo "📅 Date: $(date)"

# Change to the project directory
cd /home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1

# Activate virtual environment if exists (optional)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Run the comprehensive download script
echo "📥 Downloading latest Horizon Europe documents..."
python scripts/download_all_horizon_calls.py

if [ $? -eq 0 ]; then
    echo "✅ Document download completed successfully"
    
    # Process the new documents
    echo "🔧 Processing new documents for the vector database..."
    python scripts/process_comprehensive_docs.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Document processing completed"
        
        # Ingest into vector database
        echo "📊 Ingesting documents into vector database..."
        python scripts/ingest_comprehensive_docs.py
        
        if [ $? -eq 0 ]; then
            echo "🎉 System update completed successfully!"
            echo "📁 New documents are now available in the RAG system"
            echo "⏰ Last update: $(date)" > .last_update_time
        else
            echo "❌ Document ingestion failed"
            exit 1
        fi
    else
        echo "❌ Document processing failed"
        exit 1
    fi
else
    echo "❌ Document download failed"
    exit 1
fi

# Deactivate virtual environment if activated
if [ -d "venv" ]; then
    deactivate
    echo "✅ Virtual environment deactivated"
fi

echo "📋 Update process finished at: $(date)"