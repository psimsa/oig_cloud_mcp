"""
Configures and initializes OpenTelemetry for the OIG Cloud MCP server.

This module sets up tracing and logging, exporting data via OTLP (gRPC or HTTP).
It also configures a dedicated logger for fail2ban.
"""
import os
import logging
from typing import Optional

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

    # Lazy import of OpenTelemetry components so the module can be imported
    # even when OTel packages are not installed or missing specific submodules.
    try:
        from opentelemetry import trace as ot_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
    except Exception as e:
        print(f"OpenTelemetry tracing components not available: {e}")
        setup_fail2ban_logging()
        return

    # Attempt to import span exporters (optional)
    OTLPSpanExporterGRPC = None
    OTLPSpanExporterHTTP = None
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPSpanExporterGRPC
    except Exception:
        OTLPSpanExporterGRPC = None
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP
    except Exception:
        OTLPSpanExporterHTTP = None

    # Attempt to import logs SDK and log-related exporters and handlers (optional)
    logs_available = False
    LoggerProvider = None
    LoggingHandler = None
    BatchLogRecordProcessor = None
    OTLPLogExporterGRPC = None
    OTLPLogExporterHTTP = None
    logs_api = None
    try:
        from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
        import importlib
        try:
            logs_api = importlib.import_module("opentelemetry.logs")
        except Exception:
            logs_api = None
        logs_available = True
    except Exception:
        # Best-effort: logs are optional; proceed without them.
        logs_available = False

    if logs_available:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter as OTLPLogExporterGRPC
        except Exception:
            OTLPLogExporterGRPC = None
        try:
            from opentelemetry.exporter.otlp.proto.http.log_exporter import OTLPLogExporter as OTLPLogExporterHTTP
        except Exception:
            OTLPLogExporterHTTP = None

    print(f"Initializing OpenTelemetry for service '{service_name}' with {protocol} exporter to '{endpoint}'...")
    resource = Resource.create(attributes={"service.name": service_name})
    
    # --- Tracing Setup ---
    tracer_provider = TracerProvider(resource=resource)
    ot_trace.set_tracer_provider(tracer_provider)
    
    if protocol == "grpc":
        span_exporter = OTLPSpanExporterGRPC(endpoint=endpoint) if OTLPSpanExporterGRPC else None
    else:
        span_exporter = OTLPSpanExporterHTTP(endpoint=endpoint) if OTLPSpanExporterHTTP else None
    
    if span_exporter:
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    else:
        print("Span exporter not available; tracing will be partially disabled.")

    # --- Logging Setup (optional) ---
    if logs_available and (OTLPLogExporterGRPC or OTLPLogExporterHTTP):
        logger_provider = LoggerProvider(resource=resource)
        if logs_api and hasattr(logs_api, "set_logger_provider"):
            logs_api.set_logger_provider(logger_provider)

        log_exporter = None
        if protocol == "grpc":
            log_exporter = OTLPLogExporterGRPC(endpoint=endpoint) if OTLPLogExporterGRPC else None
        else:
            log_exporter = OTLPLogExporterHTTP(endpoint=endpoint) if OTLPLogExporterHTTP else None

        if log_exporter:
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

            # Instrument the root logger to send standard logs to OTel
            try:
                handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
                logging.getLogger().addHandler(handler)
                logging.getLogger().setLevel(logging.INFO)
            except Exception as e:
                print(f"Failed to attach OpenTelemetry logging handler: {e}")
    else:
        print("OpenTelemetry logging not configured (logs SDK or exporters missing).")
    
    # --- Fail2ban Logging ---
    setup_fail2ban_logging()
    
    # --- Auto-Instrumentation ---
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        print("FastAPI instrumentation not available; skipping auto-instrumentation.")
    
    print("OpenTelemetry initialization complete.")