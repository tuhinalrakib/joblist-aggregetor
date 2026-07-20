# Dockerfile for FastAPI + Playwright Job Scraper
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium

# Copy project files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI app with Uvicorn (using dynamic PORT for Render compatibility)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

