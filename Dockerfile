# Stage 1: Builder - Install dependencies
FROM python:3.11-slim-bookworm as builder

# Install git, which is required for pip to install the git-based dependency
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Image - Setup the application
FROM python:3.11-slim-bookworm

# Create a non-privileged user to run the application
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY . .

# Change ownership of the app directory
RUN chown -R appuser:appuser /home/appuser

# Switch to the non-privileged user
USER appuser

# Expose the port the server runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
