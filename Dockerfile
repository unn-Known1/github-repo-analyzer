# Dockerfile for GitHub Repo Analyzer
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (if needed for building some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command - can be overridden in docker-compose or docker run
ENTRYPOINT ["python", "-m", "github_repo_analyzer"]
