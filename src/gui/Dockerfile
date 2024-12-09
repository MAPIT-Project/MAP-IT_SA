FROM python:3.12.7-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source files
COPY . /app/

# Set the PYTHONPATH to include the src directory
ENV PYTHONPATH="/app/src"

# Expose the application port
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]