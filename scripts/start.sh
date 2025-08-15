#!/bin/bash
# Startup script for the CORDIS RAG API

set -e

echo "Starting CORDIS Research Projects RAG API..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please copy config/env.example to .env and configure it."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if requirements.txt has changed
if [ requirements.txt -nt venv/lib/python*/site-packages ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
