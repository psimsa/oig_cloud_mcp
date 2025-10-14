Implementation Plan: Add Full Observability with OpenTelemetry
==============================================================

**Objective:** To integrate comprehensive observability into the OIG Cloud MCP server using OpenTelemetry (OTel), including structured logging for both performance monitoring and security (fail2ban).

### **Part 1: Foundational Setup and Configuration**

**1.1. Update Dependencies**

Open `requirements.txt` and add the following lines to include the necessary OpenTelemetry packages:

    # Observability
    opentelemetry-api
    opentelemetry-sdk
    opentelemetry-exporter-otlp-proto-grpc
    opentelemetry-exporter-otlp-proto-http
    opentelemetry-instrumentation-fastapi
    

**1.2. Create Observability Module**

Create a new file named `src/oig_cloud_mcp/observability.py`. This module will contain all the setup logic.

**1.3. Implement Core OTel Configuration**

Populate `src/oig_cloud_mcp/observability.py` with the following code. This sets up tracing and logging, making them configurable via environment variables.

    """
    Configures and initializes OpenTelemetry for the OIG Cloud MCP server.
    
    This module sets up tracing and logging, exporting data via OTLP (gRPC or HTTP).
    It also configures a dedicated logger for fail2ban.
    """
    import os
    import logging
    from typing import Optional
    
    # OpenTelemetry API
    from opentelemetry import trace, logs
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.resources import Resource
    
    # OTLP Exporters
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPSpanExporterGRPC
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP
    from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter as OTLPLogExporterGRPC
    from opentelemetry.exporter.otlp.proto.http.log_exporter import OTLPLogExporter as OTLPLogExporterHTTP
    
    # Instrumentation
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    
    # --- Fail2ban Logger Setup ---
    FAIL2BAN_LOGGER_NAME = "oig_mcp_auth_failures"
    
    def setup_fail2ban_logging():
        """Configures a dedicated file logger for authentication failures."""
        log_path = os.getenv("FAIL2BAN_LOG_PATH", "/var/log/oig_mcp_auth.log")
        
        # Ensure the directory exists
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            try:
                # Create directory with permissions that allow the running user to write
                os.makedirs(log_dir, exist_ok=True)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}")
                return
    
        # Create the logger
        fail2ban_logger = logging.getLogger(FAIL2BAN_LOGGER_NAME)
        fail2ban_logger.setLevel(logging.INFO)
        fail2ban_logger.propagate = False  # Prevent logs from going to the root logger/OTel
    
        # Use a file handler
        try:
            handler = logging.FileHandler(log_path)
            # Format: timestamp: oig-mcp-auth: FAILED for user [email] from IP [client_ip]
            formatter = logging.Formatter('%(asctime)s: oig-mcp-auth: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            fail2ban_logger.addHandler(handler)
            print(f"Fail2ban logging configured at: {log_path}")
        except PermissionError:
            print(f"PermissionError: Could not write to fail2ban log at {log_path}. Check file permissions.")
        except Exception as e:
            print(f"Failed to set up fail2ban logger: {e}")
    
    
    def setup_observability(app):
        """Initializes OpenTelemetry tracing, logging, and FastAPI instrumentation."""
        service_name = os.getenv("OTEL_SERVICE_NAME", "oig-cloud-mcp")
        protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
        if not endpoint:
            print("OTel endpoint not configured. Skipping OpenTelemetry setup.")
            # Setup fail2ban logging even if OTel is disabled
            setup_fail2ban_logging()
            return
    
        print(f"Initializing OpenTelemetry for service '{service_name}' with {protocol} exporter to '{endpoint}'...")
        resource = Resource.create(attributes={"service.name": service_name})
        
        # --- Tracing Setup ---
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        if protocol == "grpc":
            span_exporter = OTLPSpanExporterGRPC(endpoint=endpoint)
        else:
            span_exporter = OTLPSpanExporterHTTP(endpoint=endpoint)
        
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    
        # --- Logging Setup ---
        logger_provider = LoggerProvider(resource=resource)
        logs.set_logger_provider(logger_provider)
    
        if protocol == "grpc":
            log_exporter = OTLPLogExporterGRPC(endpoint=endpoint)
        else:
            log_exporter = OTLPLogExporterHTTP(endpoint=endpoint)
            
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    
        # Instrument the root logger to send standard logs to OTel
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # --- Fail2ban Logging ---
        setup_fail2ban_logging()
    
        # --- Auto-Instrumentation ---
        FastAPIInstrumentor.instrument_app(app)
        print("OpenTelemetry initialization complete.")
    
    

**1.4. Initialize Observability in `main.py`**

Open `bin/main.py`. Import the new `setup_observability` function and call it before running the app.

    from oig_cloud_mcp.tools import oig_tools
    from oig_cloud_mcp.observability import setup_observability
    
    if __name__ == "__main__":
        # Configure host and port for the tools-driven FastMCP instance
        oig_tools.settings.host = "0.0.0.0"
        oig_tools.settings.port = 8000
    
        # Initialize OpenTelemetry
        setup_observability(oig_tools.app)
    
        print("Starting OIG Cloud MCP Server on [http://0.0.0.0:8000](http://0.0.0.0:8000)")
        oig_tools.run(transport="streamable-http")
    

### **Part 2: Integrate Application Tracing**

**2.1. Manually Instrument Key Functions**

Now, add custom spans to get more detailed traces.

*   **In `src/oig_cloud_mcp/tools.py`:**
    
    *   Add `from opentelemetry import trace` at the top.
        
    *   Modify `_get_credentials` to wrap its logic in a span and record the auth method.
        
    
        # ... existing imports ...
        from opentelemetry import trace
        
        tracer = trace.get_tracer(__name__)
        
        def _get_credentials(ctx: Context) -> Tuple[str, str]:
            """Extracts email and password..."""
            with tracer.start_as_current_span("get_credentials") as span:
                # ... existing function code ...
                auth_header = headers.get("authorization")
                if auth_header:
                    # ... existing logic ...
                    span.set_attribute("auth.method", "basic")
                    return email, password
        
                # ... existing function code ...
                email = headers.get("x-oig-email")
                password = headers.get("x-oig-password")
                if email and password:
                    span.set_attribute("auth.method", "header")
                    return email, password
        
                # ... existing function code ...
                raise ValueError(...)
        
    
*   **In `src/oig_cloud_mcp/session_manager.py`:**
    
    *   Add `from opentelemetry import trace` at the top.
        
    *   Modify `get_session_id` to add a span that records cache hits/misses.
        
    
        # ... existing imports ...
        from opentelemetry import trace
        
        tracer = trace.get_tracer(__name__)
        
        class SessionCache:
            # ... existing class code ...
            async def get_session_id(self, email: str, password: str, client_ip: str = "unknown") -> Tuple[Any, str]:
                """ ... existing docstring ... """
                with tracer.start_as_current_span("get_oig_session") as span:
                    span.set_attribute("user.email", email)
                    # ... existing mock mode logic ...
        
                    key = self._get_key(email, password)
                    async with self._lock:
                        # ... existing cleanup logic ...
                        if key in self._cache:
                            span.add_event("session_cache_hit")
                            # ... existing cache hit logic ...
                            return client, "session_from_cache"
        
                        span.add_event("session_cache_miss")
                        # ... existing cache miss logic ...
                        # Find the line: except Exception as e:
                        # And modify the surrounding block to log the failure
                        try:
                            if await client.authenticate():
                                # ... success logic ...
                                return client, "new_session_created"
                            else:
                                # Log failure for fail2ban
                                logging.getLogger(FAIL2BAN_LOGGER_NAME).warning(f"FAILED for user [{email}] from IP [{client_ip}]")
                                await rate_limiter.record_failure(email)
                                raise ConnectionError("Failed to authenticate with OIG Cloud.")
                        except RateLimitException:
                            # Propagate rate limit exceptions
                            raise
                        except Exception as e:
                            # Log failure for fail2ban
                            logging.getLogger(FAIL2BAN_LOGGER_NAME).warning(f"FAILED for user [{email}] from IP [{client_ip}]")
                            # Any unexpected errors during authentication are treated as connection errors
                            await rate_limiter.record_failure(email)
                            logging.error(f"Authentication error for '{email}': {e}")
                            raise ConnectionError("Failed to authenticate with OIG Cloud.")
        
        
    
    _Note: You also added `client_ip` to the function signature. This will be passed in the next step._
    

### **Part 3: Integrate Logging and `fail2ban`**

**3.1. Pass Client IP to Session Manager**

In `src/oig_cloud_mcp/tools.py`, update all five tool functions (`get_basic_data`, `get_extended_data`, etc.) to extract the client's IP address and pass it to `session_cache.get_session_id`.

*   Find this line in each tool: `client, status = await session_cache.get_session_id(email, password)`
    
*   Get the client IP from the context. The `request` object might be None, so handle that case.
    
*   Change the line to:
    
        request = ctx.request_context.request
        client_ip = request.client.host if request and request.client else "unknown"
        client, status = await session_cache.get_session_id(email, password, client_ip=client_ip)
        
    

**3.2. Import Fail2ban Logger Name**

In `src/oig_cloud_mcp/session_manager.py`, you need to import the logger name constant. Add this line to the top of the file:

    from oig_cloud_mcp.observability import FAIL2BAN_LOGGER_NAME
    import logging
    

### **Part 4: Update Deployment and Documentation**

**4.1. Update `Dockerfile`**

Open `Dockerfile` and add two lines before the `USER appuser` instruction to create the log directory and set permissions.

    # ... after COPY commands ...
    
    # Create and set permissions for the log directory
    RUN mkdir -p /var/log && \
        touch /var/log/oig_mcp_auth.log && \
        chown -R appuser:appuser /var/log
    
    # Switch to the non-privileged user
    USER appuser
    
    # ... rest of file ...
    

**4.2. Update `README.md`**

Open `README.md` and add a new "Observability" section after the "Configuration" section.

    ## Observability
    
    This server supports comprehensive observability through OpenTelemetry (OTel) and provides a dedicated log for security monitoring with tools like `fail2ban`.
    
    ### OpenTelemetry (Traces & Logs)
    
    To enable OTel, configure the following environment variables:
    
    * `OTEL_EXPORTER_OTLP_ENDPOINT`: The full URL to your OTel collector's gRPC or HTTP endpoint (e.g., `http://localhost:4317` for gRPC or `http://localhost:4318/v1/logs` for HTTP).
    * `OTEL_EXPORTER_OTLP_PROTOCOL`: Set to `grpc` (default) or `http/protobuf` to choose the export protocol.
    * `OTEL_SERVICE_NAME`: A name for this service (defaults to `oig-cloud-mcp`).
    
    If `OTEL_EXPORTER_OTLP_ENDPOINT` is not set, OTel will be disabled.
    
    ### Security Logging for Fail2ban
    
    The server writes all failed authentication attempts to a dedicated log file, suitable for monitoring with `fail2ban`.
    
    * **Log Path:** The default location is `/var/log/oig_mcp_auth.log`. This can be changed by setting the `FAIL2BAN_LOG_PATH` environment variable.
    * **Log Format:**
        ```
        YYYY-MM-DD HH:MM:SS: oig-mcp-auth: FAILED for user [user@email.com] from IP [123.45.67.89]
        ```
    
    When running in Docker, you should mount a volume to this path to persist the log on the host machine.
    

### **Part 5: Verification**

After applying the changes, the agent must verify them.

5.1. Run Tests

Run the test suite to ensure no existing functionality was broken.

pytest

5.2. Run Server with OTel

Start the server with OTel environment variables configured.

export OTEL\_EXPORTER\_OTLP\_ENDPOINT="http://localhost:4317"

export OTEL\_SERVICE\_NAME="my-test-mcp"

python bin/main.py

Observe the console output to confirm that OpenTelemetry initializes successfully.

5.3. Test fail2ban Logging

Make a request with incorrect credentials and check that a log entry is written to /var/log/oig\_mcp\_auth.log.

python bin/cli\_tester.py get\_basic\_data --email "bad@user.com" --password "wrong"

sudo cat /var/log/oig\_mcp\_auth.log

Confirm that a "FAILED" log entry appears in the file.