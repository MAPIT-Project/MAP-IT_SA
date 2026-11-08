FROM python:3.13-slim

WORKDIR /app

# Install system dependencies required for building lxml and other packages
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies - modified to handle dependency conflicts
# First install protobuf with compatible version
RUN pip install --no-cache-dir "protobuf>=3.19.5,<5.0.0"

# Then install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .
COPY scripts/sync_funding_calls.py ./scripts/sync_funding_calls.py
COPY scripts/reembed_funding_calls.py ./scripts/reembed_funding_calls.py
COPY scripts/audit_document_sources.py ./scripts/audit_document_sources.py
COPY scripts/apply_document_refresh.py ./scripts/apply_document_refresh.py
COPY scripts/sync_verified_document_revisions.py ./scripts/sync_verified_document_revisions.py
COPY scripts/record_document_source_reviews.py ./scripts/record_document_source_reviews.py
COPY scripts/check_pending_document_sources.py ./scripts/check_pending_document_sources.py
COPY scripts/cordis_extract.py ./scripts/cordis_extract.py
COPY scripts/import_cordis_projects.py ./scripts/import_cordis_projects.py
COPY scripts/sql/ ./scripts/sql/

# Create a .env file if it doesn't exist (this will be overwritten by mounted volume)
RUN touch .env

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
