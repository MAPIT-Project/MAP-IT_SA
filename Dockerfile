FROM python:3.11-slim

WORKDIR /app

# Install dependencies - modified to handle dependency conflicts
COPY requirements.txt .

# First install protobuf with compatible version
RUN pip install --no-cache-dir "protobuf>=3.19.5,<5.0.0"

# Then install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create a .env file if it doesn't exist (this will be overwritten by mounted volume)
RUN touch .env

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
