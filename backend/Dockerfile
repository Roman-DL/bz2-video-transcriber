FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck and ffmpeg for video duration detection
RUN apt-get update && apt-get install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Create non-root user with uid/gid matching host (roman:family = 3000:3000)
RUN groupadd -g 3000 appgroup && \
    useradd -m -u 3000 -g 3000 appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
