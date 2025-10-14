# Stage 1: Builder - Install dependencies
FROM python:3.13-slim-bookworm as builder

# Install git, which is required for pip to install the git-based dependency
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and setup files
COPY requirements.txt setup.py ./
COPY src/ ./src/

# Install dependencies and the package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# Stage 2: Final Image - Setup the application
FROM python:3.13-slim-bookworm

# Create a non-privileged user to run the application
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application scripts and runtime files
COPY bin/ ./bin/
COPY whitelist.txt .

# Change ownership of the app directory
RUN chown -R appuser:appuser /home/appuser

# Create and set permissions for the log directory
RUN mkdir -p /var/log && \
    touch /var/log/oig_mcp_auth.log && \
    chown -R appuser:appuser /var/log

# Switch to the non-privileged user
USER appuser

# Expose the port the server runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "bin/main.py"]
