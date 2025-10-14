import asyncio
import time
import hashlib
from typing import Any, Dict, Tuple, Optional, List, Protocol, Awaitable, Literal, cast

SessionStatus = Literal["session_from_cache", "new_session_created", "mock_session"]

# The real OigCloudApi is imported only when needed so that local mock
# mode (OIG_CLOUD_MOCK=1) can run without the external dependency.
import os
from oig_cloud_mcp.security import rate_limiter, RateLimitException
from oig_cloud_mcp.observability import FAIL2BAN_LOGGER_NAME
import logging
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class OigCloudClientProtocol(Protocol):
    """Structural protocol describing the minimal client surface used by SessionCache.

    Declared as a Protocol so we can avoid importing the real client at module import
    time while still giving mypy a useful shape to check against.
    """

    _phpsessid: str
    _sample_path: Optional[str]
    box_id: Optional[str]

    def authenticate(self) -> Awaitable[bool]: ...
    def get_stats(self) -> Awaitable[Dict[str, Any]]: ...
    def get_extended_stats(
        self, name: str, start_date: str, end_date: str
    ) -> Awaitable[Dict[str, Any]]: ...
    def get_notifications(self) -> Awaitable[List[Any]]: ...
    def set_box_mode(self, mode: Any) -> Awaitable[bool]: ...
    def set_grid_delivery(self, mode: Any) -> Awaitable[bool]: ...


class SessionCache:
    def __init__(self, eviction_time_seconds: int = 43200):  # 12 hours
        # Cache maps credential-hash -> (authenticated client instance, last_used_timestamp)
        self._cache: Dict[str, Tuple[OigCloudClientProtocol, float]] = {}
        self._eviction_time = eviction_time_seconds
        self._lock = asyncio.Lock()
        print("SessionCache initialized.")

    def _get_key(self, email: str, password: str) -> str:
        """Creates a secure hash key from credentials."""
        return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()

    async def get_session_id(
        self, email: str, password: str, client_ip: str = "unknown"
    ) -> Tuple[OigCloudClientProtocol, SessionStatus]:
        """
        Get a valid, authenticated OigCloudApi client, authenticating if necessary.
        Returns a tuple of (client, status), where status is
        'session_from_cache' or 'new_session_created'.
        """
        with tracer.start_as_current_span("get_oig_session") as span:
            span.set_attribute("user.email", email)
            # Support a local mock mode for offline testing. When the environment
            # variable OIG_CLOUD_MOCK is set to '1' we return a minimal mock client
            # that serves the project's sample-response.json. This avoids making
            # network calls during local verification and CI.
        if os.environ.get("OIG_CLOUD_MOCK") == "1":
            # Minimal mock client used only for testing. It provides the
            # attributes and coroutines the tools expect.
            class _MockClient:
                def __init__(self, sample_path: str) -> None:
                    self._phpsessid: str = "mock-session"
                    self._sample_path: str = sample_path
                    # Mock clients may be asked to report a box_id by the tools.
                    # Initialize to None and populate when get_stats() is called.
                    self.box_id: Optional[str] = None

                async def authenticate(self) -> bool:
                    return True

                async def get_stats(self) -> Dict[str, Any]:
                    import json
                    from pathlib import Path

                    p = Path(self._sample_path)
                    if p.exists():
                        return json.loads(p.read_text())
                    return {}

                async def get_extended_stats(
                    self, name: str, start_date: str, end_date: str
                ) -> Dict[str, Any]:
                    return {}

                async def get_notifications(self) -> List[Any]:
                    return []

                # Provide minimal implementations for write actions so that
                # tools that call these methods in mock mode behave predictably.
                async def set_box_mode(self, mode: Any) -> bool:
                    # In the mock we simply accept the value and pretend it succeeded.
                    return True

                async def set_grid_delivery(self, mode: Any) -> bool:
                    # Accept numeric flags (1/0) and pretend success.
                    return True

            sample_path: str = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "tests",
                "fixtures",
                "sample-response.json",
            )
            return (
                cast(OigCloudClientProtocol, _MockClient(sample_path)),
                "mock_session",
            )

        key = self._get_key(email, password)
        async with self._lock:
            # Clean up expired sessions first
            current_time = time.time()
            expired_keys = [
                k
                for k, (_, ts) in self._cache.items()
                if current_time - ts > self._eviction_time
            ]
            for k in expired_keys:
                del self._cache[k]

            if key in self._cache:
                # A client instance is already in the cache, reuse it.
                client, last_used = self._cache[key]
                # Update the last-used timestamp to prevent premature eviction.
                self._cache[key] = (client, time.time())
                span.add_event("session_cache_hit")
                return client, "session_from_cache"

            # If not in cache, authenticate to get a new one
            span.add_event("session_cache_miss")
            # Enforce rate-limiter before attempting to authenticate.
            try:
                await rate_limiter.check_and_proceed(email)
            except RateLimitException:
                # Re-raise so callers (tools) can turn this into a user-visible error
                raise

            # Perform real authentication against OIG Cloud API. Import lazily
            # to keep local mock testing simple.
            from oig_cloud_client.api.oig_cloud_api import OigCloudApi

            client = OigCloudApi(username=email, password=password, no_telemetry=True)
            try:
                if await client.authenticate():
                    # Cache the entire authenticated client instance, not just the session ID.
                    self._cache[key] = (client, time.time())
                    await rate_limiter.record_success(email)
                    print(f"Authentication successful for '{email}'.")
                    # Return the authenticated client instance for immediate use by callers.
                    return client, "new_session_created"
                else:
                    # Log failure for fail2ban
                    logging.getLogger(FAIL2BAN_LOGGER_NAME).warning(
                        f"FAILED for user [{email}] from IP [{client_ip}]"
                    )
                    await rate_limiter.record_failure(email)
                    raise ConnectionError("Failed to authenticate with OIG Cloud.")
            except RateLimitException:
                # Propagate rate limit exceptions
                raise
            except Exception as e:
                # Log failure for fail2ban
                logging.getLogger(FAIL2BAN_LOGGER_NAME).warning(
                    f"FAILED for user [{email}] from IP [{client_ip}]"
                )
                # Any unexpected errors during authentication are treated as connection errors
                await rate_limiter.record_failure(email)
                logging.error(f"Authentication error for '{email}': {e}")
                raise ConnectionError("Failed to authenticate with OIG Cloud.")


# Create a single instance to be used by the server
session_cache: SessionCache = SessionCache()
