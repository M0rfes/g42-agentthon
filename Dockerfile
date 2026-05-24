FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and its system dependencies
RUN playwright install --with-deps chromium

# Copy application files
COPY . .

# Expose Flask port
EXPOSE 8000

# Start server using Gunicorn with a generous 10-minute timeout for long agentic flows
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "run:app"]

