FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt')"

# Copy source code
COPY src/ ./src/

# Create input/output directories
RUN mkdir -p /app/input /app/output

# Set environment
ENV PYTHONPATH=/app

# Default command
CMD ["python", "src/main.py", "--input", "/app/input/input.json", "--output", "/app/output/output.json"]
