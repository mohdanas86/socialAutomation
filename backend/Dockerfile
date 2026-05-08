# Dockerfile for Social Media Automation Backend
#
# HOW TO USE:
#   docker build -t social-automation-backend .
#   docker run -p 8000:8000 --env-file .env social-automation-backend
#
# MULTI-STAGE BUILD:
# Stage 1: Builder - installs dependencies
# Stage 2: Runtime - only includes what we need to run the app
#
# Benefits:
# - Smaller final image (no pip cache)
# - Faster deployments (smaller = faster transfer)
# - More secure (fewer tools to exploit)

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ===== RUNTIME STAGE =====
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Add local pip packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
