FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by PyMuPDF
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmupdf-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure pip for network resilience (large wheels & slow connection)
ENV PIP_DEFAULT_TIMEOUT=1000 \
    PIP_RETRIES=10

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout 1000 --retries 10 -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
