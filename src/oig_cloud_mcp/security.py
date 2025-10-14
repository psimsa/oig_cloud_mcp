import os
import time
import asyncio
from typing import Dict, Optional, Set, Any, List, TypedDict, cast


class RateLimitException(Exception):
    """Raised when a user is temporarily locked out due to repeated failures."""


class Whitelist:
    """Loads a simple newline-separated whitelist of allowed email addresses.

    The whitelist file is expected to be named `whitelist.txt` and can be in:
    1. The current working directory (for Docker/production)
    2. The project root (for local development - 3 levels up from this file)

    Lines beginning with `#` or empty lines are ignored.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            # First try current working directory (Docker/production)
            cwd_path = os.path.join(os.getcwd(), "whitelist.txt")
            if os.path.exists(cwd_path):
                path = cwd_path
            else:
                # Fall back to project root (local development)
                path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "whitelist.txt"
                )
        assert path is not None
        self.path: str = os.path.abspath(path)
        self._emails: Set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r") as f:
                for raw in f:
                    line = raw.split("#", 1)[0].strip()
                    if not line:
                        continue
                    self._emails.add(line.lower())
        except FileNotFoundError:
            # If the whitelist file is missing, treat as empty (no users allowed)
            print(
                f"Warning: whitelist file not found at '{self.path}'. No users are permitted until this file is created."
            )
        except Exception as e:
            print(f"Error loading whitelist from '{self.path}': {e}")

    def is_allowed(self, email: str) -> bool:
        if not email:
            return False
        return email.lower() in self._emails


class _UserState(TypedDict):
    failed_attempts: int
    lockout_until: float


class RateLimiter:
    """Simple in-memory exponential backoff rate limiter for authentication attempts.

    Tracks failed attempts and enforces a temporary lockout window when too many
    failures occur. This is intentionally lightweight and intended for use in
    single-process testing or small deployments. For distributed deployments a
    central store (Redis, DB) should be used instead.
    """

    MAX_FAILURES = 3
    INITIAL_LOCKOUT = 10  # seconds
    MAX_LOCKOUT = 30  # seconds

    def __init__(self) -> None:
        # _user_state[email] = {"failed_attempts": int, "lockout_until": float}
        self._user_state: Dict[str, _UserState] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def check_and_proceed(self, email: str) -> None:
        """Check whether the given email is currently locked out.

        Raises RateLimitException when the user is still in a lockout window.
        """
        now: float = time.time()
        async with self._lock:
            state: Optional[_UserState] = self._user_state.get(email)
            if not state:
                # Initialize state for the user
                # Explicitly create a properly-typed _UserState mapping.
                self._user_state[email] = cast(
                    _UserState, {"failed_attempts": 0, "lockout_until": 0.0}
                )
                return

            lockout_until = state.get("lockout_until", 0)
            if lockout_until > now:
                remaining = int(lockout_until - now)
                raise RateLimitException(
                    f"Too many failed authentication attempts. Try again in {remaining} seconds."
                )

    async def record_success(self, email: str) -> None:
        """Reset the failure counter for a successful authentication."""
        async with self._lock:
            self._user_state[email] = {"failed_attempts": 0, "lockout_until": 0.0}

    async def record_failure(self, email: str) -> None:
        """Register a failed authentication attempt and apply lockout if needed."""
        async with self._lock:
            state: _UserState = self._user_state.setdefault(
                email, {"failed_attempts": 0, "lockout_until": 0.0}
            )
            state["failed_attempts"] = int(state.get("failed_attempts", 0)) + 1
            failures: int = state["failed_attempts"]
            if failures >= self.MAX_FAILURES:
                exponent: int = failures - self.MAX_FAILURES
                lockout: float = min(
                    self.INITIAL_LOCKOUT * (2**exponent), self.MAX_LOCKOUT
                )
                state["lockout_until"] = time.time() + lockout
                print(
                    f"User '{email}' locked out for {int(lockout)} seconds after {failures} failures."
                )


# Module-level shared instances
whitelist: Whitelist = Whitelist()
rate_limiter: RateLimiter = RateLimiter()
