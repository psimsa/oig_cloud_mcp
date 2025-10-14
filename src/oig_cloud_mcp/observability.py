"""
Configures and initializes OpenTelemetry for the OIG Cloud MCP server.

This module sets up tracing and logging, exporting data via OTLP (gRPC or HTTP).
It also configures a dedicated logger for fail2ban.
"""

import os
import logging
from typing import Optional, Any, Callable, Dict, Type, Protocol, cast

# Module logger
logger: logging.Logger = logging.getLogger(__name__)

# --- Fail2ban Logger Setup ---
FAIL2BAN_LOGGER_NAME: str = "oig_mcp_auth_failures"


# Protocols used to safely type optional OpenTelemetry SDK components when they are
# imported at runtime. These describe the small subset of the SDK surface that this
# module actually relies on so type-checkers can validate usage without requiring
# the full OpenTelemetry types to be installed.
class LoggerProviderProtocol(Protocol):
    def __init__(self, resource: Any) -> None: ...
    def add_log_record_processor(self, processor: Any) -> None: ...


class BatchLogRecordProcessorProtocol(Protocol):
    def __init__(self, exporter: Any) -> None: ...


class LoggingHandlerProtocol(Protocol):
    def __init__(self, level: int = ..., logger_provider: Any = ...) -> None: ...


def setup_fail2ban_logging() -> None:
    """Configures a dedicated file logger for authentication failures."""
    log_path: str = os.getenv("FAIL2BAN_LOG_PATH", "/var/log/oig_mcp_auth.log")

    # Ensure the directory exists
    log_dir: str = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        try:
            # Create directory with permissions that allow the running user to write
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating log directory {log_dir}: {e}")
            return

    # Create the logger
    fail2ban_logger: logging.Logger = logging.getLogger(FAIL2BAN_LOGGER_NAME)
    fail2ban_logger.setLevel(logging.INFO)
    fail2ban_logger.propagate = False  # Prevent logs from going to the root logger/OTel

    # Use a file handler
    try:
        handler: logging.Handler = logging.FileHandler(log_path)
        # Format: timestamp: oig-mcp-auth: FAILED for user [email] from IP [client_ip]
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s: oig-mcp-auth: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        fail2ban_logger.addHandler(handler)
        print(f"Fail2ban logging configured at: {log_path}")
    except PermissionError:
        print(
            f"PermissionError: Could not write to fail2ban log at {log_path}. Check file permissions."
        )
    except Exception as e:
        print(f"Failed to set up fail2ban logger: {e}")


def setup_observability(app: Any) -> None:
    """Initializes OpenTelemetry tracing, logging, and FastAPI instrumentation."""
    service_name: str = os.getenv("OTEL_SERVICE_NAME", "oig-cloud-mcp")
    protocol: str = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    endpoint: Optional[str] = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not endpoint:
        logger.info("OTel endpoint not configured. Skipping OpenTelemetry setup.")
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
        logger.debug("OpenTelemetry tracing components not available: %s", e)
        setup_fail2ban_logging()
        return

    # Attempt to import span exporters (optional)
    OTLPSpanExporterGRPC: Optional[Type[Any]] = None
    OTLPSpanExporterHTTP: Optional[Type[Any]] = None
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter as OTLPSpanExporterGRPC,
        )
    except Exception:
        OTLPSpanExporterGRPC = None
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as OTLPSpanExporterHTTP,
        )
    except Exception:
        OTLPSpanExporterHTTP = None

    # Attempt to import logs SDK and log-related exporters and handlers (optional)
    logs_available = False
    LoggerProvider: Optional[Type[LoggerProviderProtocol]] = None
    LoggingHandler: Optional[Type[LoggingHandlerProtocol]] = None
    BatchLogRecordProcessor: Optional[Type[BatchLogRecordProcessorProtocol]] = None
    OTLPLogExporterGRPC: Optional[Type[Any]] = None
    OTLPLogExporterHTTP: Optional[Type[Any]] = None
    logs_api: Optional[Any] = None
    try:
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
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
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter as OTLPLogExporterGRPC,
            )
        except Exception:
            OTLPLogExporterGRPC = None
        try:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter as OTLPLogExporterHTTP,
            )
        except Exception:
            OTLPLogExporterHTTP = None

    logger.info(
        "Initializing OpenTelemetry for service '%s' with %s exporter to '%s'...",
        service_name,
        protocol,
        endpoint,
    )
    resource = Resource.create(attributes={"service.name": service_name})

    # --- Tracing Setup ---
    tracer_provider = TracerProvider(resource=resource)
    ot_trace.set_tracer_provider(tracer_provider)

    # Create span exporter safely: ensure the symbol is present and callable before instantiating
    span_exporter: Optional[Any] = None
    try:
        if protocol == "grpc":
            if OTLPSpanExporterGRPC is not None and callable(OTLPSpanExporterGRPC):
                span_exporter = OTLPSpanExporterGRPC(endpoint=endpoint)
        else:
            if OTLPSpanExporterHTTP is not None and callable(OTLPSpanExporterHTTP):
                span_exporter = OTLPSpanExporterHTTP(endpoint=endpoint)
    except Exception as e:
        logger.warning("Failed to create span exporter: %s", e)

    if span_exporter is not None:
        try:
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        except Exception as e:
            logger.warning("Failed to add span processor: %s", e)
    else:
        logger.info("Span exporter not available; tracing will be partially disabled.")

    # --- Logging Setup (optional) ---
    if logs_available and (OTLPLogExporterGRPC or OTLPLogExporterHTTP):
        # Ensure LoggerProvider was actually imported and is callable before using it
        if LoggerProvider is None or not callable(LoggerProvider):
            print("LoggerProvider not available; skipping OpenTelemetry logging setup.")
        else:
            logger_provider = LoggerProvider(resource=resource)
            if logs_api and hasattr(logs_api, "set_logger_provider"):
                logs_api.set_logger_provider(logger_provider)

            # Safely create log exporter and attach processors/handlers
            log_exporter: Optional[Any] = None
            try:
                if protocol == "grpc":
                    if OTLPLogExporterGRPC is not None and callable(
                        OTLPLogExporterGRPC
                    ):
                        log_exporter = OTLPLogExporterGRPC(endpoint=endpoint)
                else:
                    if OTLPLogExporterHTTP is not None and callable(
                        OTLPLogExporterHTTP
                    ):
                        log_exporter = OTLPLogExporterHTTP(endpoint=endpoint)
            except Exception as e:
                logger.warning("Failed to create log exporter: %s", e)

            # Add log record processor only if exporter and processor class are available
            if (
                log_exporter is not None
                and BatchLogRecordProcessor is not None
                and callable(BatchLogRecordProcessor)
            ):
                try:
                    processor = BatchLogRecordProcessor(log_exporter)
                    # Cast to the protocol so type-checkers understand the instance
                    cast(
                        LoggerProviderProtocol, logger_provider
                    ).add_log_record_processor(processor)
                except Exception as e:
                    logger.warning("Failed to add log record processor: %s", e)
            else:
                print(
                    "Log record processor not available; logs will not be exported to OTel."
                )

            # Instrument the root logger to send standard logs to OTel if handler is available
            if (
                log_exporter is not None
                and LoggingHandler is not None
                and callable(LoggingHandler)
            ):
                try:
                    handler: logging.Handler = cast(
                        logging.Handler,
                        LoggingHandler(
                            level=logging.INFO, logger_provider=logger_provider
                        ),
                    )
                    logging.getLogger().addHandler(handler)
                    logging.getLogger().setLevel(logging.INFO)
                except Exception as e:
                    logger.warning(
                        "Failed to attach OpenTelemetry logging handler: %s", e
                    )
                else:
                    print(
                        "OpenTelemetry LoggingHandler not available; standard logs won't be sent to OTel."
                    )
    else:
        logger.info(
            "OpenTelemetry logging not configured (logs SDK or exporters missing)."
        )

    # --- Fail2ban Logging ---
    setup_fail2ban_logging()

    # --- Auto-Instrumentation ---
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        logger.info(
            "FastAPI instrumentation not available; skipping auto-instrumentation."
        )

    logger.info("OpenTelemetry initialization complete.")
