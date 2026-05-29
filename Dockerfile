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

# Create a .env file if it doesn't exist (this will be overwritten by mounted volume)
RUN touch .env

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
