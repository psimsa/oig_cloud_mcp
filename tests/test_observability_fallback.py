import builtins
import importlib
import types

import pytest

from oig_cloud_mcp import observability


def test_setup_observability_handles_missing_opentelemetry(monkeypatch, tmp_path):
    """Simulate that opentelemetry packages are not importable and ensure setup_observability doesn't raise."""

    # Point a dummy endpoint so the function attempts to initialize OTel
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://example.invalid:4318")

    # Save the real import
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Simulate ImportError for any opentelemetry import
        if name.startswith("opentelemetry"):
            raise ImportError("simulated missing package")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Create a dummy FastAPI app object; instrumentation should be skipped gracefully
    class DummyApp:
        pass

    try:
        # Call setup_observability; should not raise despite missing OTEL packages
        observability.setup_observability(DummyApp())
    finally:
        # Restore import
        monkeypatch.setattr(builtins, "__import__", real_import)
