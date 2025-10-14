# Stage 1: Builder - Install dependencies into a virtual environment
FROM python:3.13-slim-bookworm as builder

# Install git for git-based dependencies and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
ENV VENV_PATH=/opt/venv
RUN python3 -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

# Copy requirements and source code
WORKDIR /app
COPY requirements.txt setup.py ./
COPY src/ ./src/

# Install dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# ---

# Stage 2: Final Image - Setup the application
FROM python:3.13-slim-bookworm

# Create a non-privileged user
RUN useradd --create-home appuser

# Copy the virtual environment from the builder stage
ENV VENV_PATH=/opt/venv
COPY --from=builder $VENV_PATH $VENV_PATH

# Set the PATH to use the virtual environment
ENV PATH="$VENV_PATH/bin:$PATH"

# Set up the application directory
WORKDIR /home/appuser/app
COPY bin/ ./bin/
COPY whitelist.txt .

# Create log file and set permissions for all necessary directories
RUN mkdir -p /var/log && \
    touch /var/log/oig_mcp_auth.log && \
    chown -R appuser:appuser /var/log /home/appuser

# Switch to the non-privileged user
USER appuser

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["python", "bin/main.py"]
