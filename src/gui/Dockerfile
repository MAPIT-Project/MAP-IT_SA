FROM python:3.12.7-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker's caching
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app (including static and templates folders)
COPY . /app/

# Expose port 5000 to access Flask app
EXPOSE 5000

# Start Flask app
CMD ["python", "app.py"]
