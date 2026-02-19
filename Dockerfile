# Dockerfile for OPA Test Framework
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install OPA CLI.
# Override at build time:  docker build --build-arg OPA_VERSION=0.71.0 .
# Or via docker-compose:   OPA_VERSION=0.71.0 docker-compose build
ARG OPA_VERSION=0.70.0
RUN wget -q "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_amd64_static" -O /tmp/opa_linux_amd64_static && \
    wget -q "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_amd64_static.sha256" -O /tmp/opa_linux_amd64_static.sha256 && \
    cd /tmp && sha256sum -c opa_linux_amd64_static.sha256 && \
    mv /tmp/opa_linux_amd64_static /usr/local/bin/opa && \
    chmod +x /usr/local/bin/opa && \
    rm -f /tmp/opa_linux_amd64_static.sha256 && \
    opa version

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .

# Install the package
RUN pip install --no-cache-dir -e .

# Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/test-results && \
    chown -R appuser:appuser /app

USER appuser

# Set entrypoint
ENTRYPOINT ["opa-test"]
CMD ["--help"]
