import asyncio
import time
import hashlib
from typing import Dict, Tuple, Any
 
# The real OigCloudApi is imported only when needed so that local mock
# mode (OIG_CLOUD_MOCK=1) can run without the external dependency.
import os
import secrets
from security import rate_limiter, RateLimitException
 
class SessionCache:
    def __init__(self, eviction_time_seconds: int = 43200): # 12 hours
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._eviction_time = eviction_time_seconds
        self._lock = asyncio.Lock()
        print("SessionCache initialized.")
 
    def _get_key(self, email: str, password: str) -> str:
        """Creates a secure hash key from credentials."""
        return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()
 
    async def get_session_id(self, email: str, password: str) -> Tuple[Any, str]:
        """
        Get a valid, authenticated OigCloudApi client, authenticating if necessary.
        Returns a tuple of (client, status), where status is
        'session_from_cache' or 'new_session_created'.
        """
        # Support a local mock mode for offline testing. When the environment
        # variable OIG_CLOUD_MOCK is set to '1' we return a minimal mock client
        # that serves the project's sample-response.json. This avoids making
        # network calls during local verification and CI.
        if os.environ.get("OIG_CLOUD_MOCK") == "1":
            # Minimal mock client used only for testing. It provides the
            # attributes and coroutines the tools expect.
            class _MockClient:
                def __init__(self, sample_path):
                    self._phpsessid = "mock-session"
                    self._sample_path = sample_path

                async def authenticate(self):
                    return True

                async def get_stats(self):
                    import json
                    from pathlib import Path

                    p = Path(self._sample_path)
                    if p.exists():
                        return json.loads(p.read_text())
                    return {}

                async def get_extended_stats(self, name, start_date, end_date):
                    return {}

                async def get_notifications(self):
                    return []

            sample_path = os.path.join(os.path.dirname(__file__), "sample-response.json")
            return _MockClient(sample_path), "mock_session"

        key = self._get_key(email, password)
        async with self._lock:
            # Clean up expired sessions first
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in self._cache.items() if current_time - ts > self._eviction_time]
            for k in expired_keys:
                del self._cache[k]

            if key in self._cache:
                # Cache stores only the raw session id (string). When we hit the cache
                # we construct a fresh client instance and set the session id on it so
                # callers receive a ready-to-use authenticated client object.
                session_id, last_used = self._cache[key]
                self._cache[key] = (session_id, time.time())
                # Import the real client lazily to avoid hard dependency in mock mode
                from oig_cloud_client.api.oig_cloud_api import OigCloudApi
                client = OigCloudApi(username=email, password=password, no_telemetry=True)
                # The underlying client library uses _phpsessid as the session token.
                client._phpsessid = session_id
                return client, "session_from_cache"

            # If not in cache, authenticate to get a new one
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
                    new_session_id = client._phpsessid
                    # Cache the session id string only; client objects are created on demand
                    # so we avoid storing complex objects in the in-memory cache.
                    self._cache[key] = (new_session_id, time.time())
                    await rate_limiter.record_success(email)
                    print(f"Authentication successful for '{email}'.")
                    # Return the authenticated client instance for immediate use by callers.
                    return client, "new_session_created"
                else:
                    await rate_limiter.record_failure(email)
                    raise ConnectionError("Failed to authenticate with OIG Cloud.")
            except RateLimitException:
                # Propagate rate limit exceptions
                raise
            except Exception as e:
                # Any unexpected errors during authentication are treated as connection errors
                await rate_limiter.record_failure(email)
                print(f"Authentication error for '{email}': {e}")
                raise ConnectionError("Failed to authenticate with OIG Cloud.")

# Create a single instance to be used by the server
session_cache = SessionCache()
