#!/bin/bash
# Setup script for the CORDIS RAG API

set -e

echo "Setting up CORDIS Research Projects RAG API..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp config/env.example .env
    echo "Please edit .env file with your API keys and configuration."
fi

echo "Setup complete! Please:"
echo "1. Edit .env file with your API keys"
echo "2. Run 'source venv/bin/activate' to activate the virtual environment"
echo "3. Run 'python main.py' or 'uvicorn main:app --reload' to start the server"
