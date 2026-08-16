FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg for audio synthesis, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Expose port
EXPOSE 8000

# Run Uvicorn server with dynamic Render $PORT support
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
