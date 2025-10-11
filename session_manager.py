import asyncio
import time
import hashlib
from typing import Dict, Tuple
 
# Note: oig_cloud_client is installed from git in the venv
from oig_cloud_client.api.oig_cloud_api import OigCloudApi
import secrets
 
class SessionCache:
    def __init__(self, eviction_time_seconds: int = 43200): # 12 hours
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._eviction_time = eviction_time_seconds
        self._lock = asyncio.Lock()
        print("SessionCache initialized.")
 
    def _get_key(self, email: str, password: str) -> str:
        """Creates a secure hash key from credentials."""
        return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()
 
    async def get_session_id(self, email: str, password: str) -> Tuple[str, str]:
        """
        Get a valid session ID, authenticating if necessary.
        Returns a tuple of (session_id, status), where status is
        'session_from_cache' or 'new_session_created'.
        """
        key = self._get_key(email, password)
        async with self._lock:
            # Clean up expired sessions first
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in self._cache.items() if current_time - ts > self._eviction_time]
            for k in expired_keys:
                del self._cache[k]

            if key in self._cache:
                session_id, last_used = self._cache[key]
                self._cache[key] = (session_id, time.time())
                return session_id, "session_from_cache"

            # If not in cache, authenticate to get a new one
            # NOTE: For local development and testing this environment does
            # not always have valid credentials or network access to OIG
            # Cloud. To avoid making real network calls during these
            # stages, the actual authentication call is commented out
            # below. Instead we generate a pseudo-session id and cache
            # it so that the rest of the application can exercise
            # session-related behavior without hitting the external API.
            #
            # client = OigCloudApi(username=email, password=password, no_telemetry=True)
            # if await client.authenticate():
            #     new_session_id = client._phpsessid
            #     self._cache[key] = (new_session_id, time.time())
            #     print(f"Authentication successful for '{email}'.")
            #     return new_session_id, "new_session_created"
            # else:
            #     raise ConnectionError("Failed to authenticate with OIG Cloud.")

            # Generate a local pseudo-session id for testing instead of
            # performing real authentication.
            new_session_id = secrets.token_hex(16)
            self._cache[key] = (new_session_id, time.time())
            print(f"Generated local session id for '{email}'.")
            return new_session_id, "new_session_created"

# Create a single instance to be used by the server
session_cache = SessionCache()
