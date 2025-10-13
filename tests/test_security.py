"""Unit tests for security.py module."""

import tempfile
import pytest
import asyncio
from oig_cloud_mcp.security import Whitelist, RateLimiter, RateLimitException


class TestWhitelist:
    """Tests for the Whitelist class."""

    def test_allows_listed_email(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("user@example.com\n")
            f.write("admin@example.com\n")
            f.flush()

            wl = Whitelist(path=f.name)
            assert wl.is_allowed("user@example.com")
            assert wl.is_allowed("admin@example.com")

    def test_rejects_unlisted_email(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("user@example.com\n")
            f.flush()

            wl = Whitelist(path=f.name)
            assert not wl.is_allowed("hacker@example.com")

    def test_case_insensitive(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("user@example.com\n")
            f.flush()

            wl = Whitelist(path=f.name)
            assert wl.is_allowed("USER@EXAMPLE.COM")
            assert wl.is_allowed("User@Example.Com")

    def test_ignores_comments(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("# This is a comment\n")
            f.write("user@example.com # inline comment\n")
            f.write("\n")
            f.write("  \n")
            f.flush()

            wl = Whitelist(path=f.name)
            assert wl.is_allowed("user@example.com")

    def test_empty_email(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("user@example.com\n")
            f.flush()

            wl = Whitelist(path=f.name)
            assert not wl.is_allowed("")
            assert not wl.is_allowed(None)

    def test_missing_file(self):
        wl = Whitelist(path="/nonexistent/path/to/whitelist.txt")
        assert not wl.is_allowed("user@example.com")


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_allows_user_with_no_failures(self):
        rl = RateLimiter()
        await rl.check_and_proceed("user@example.com")

    @pytest.mark.asyncio
    async def test_lockout_after_max_failures(self):
        rl = RateLimiter()
        email = "user@example.com"

        for _ in range(RateLimiter.MAX_FAILURES):
            await rl.record_failure(email)

        with pytest.raises(RateLimitException) as exc_info:
            await rl.check_and_proceed(email)

        assert "Too many failed authentication attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        rl = RateLimiter()
        email = "user@example.com"

        await rl.record_failure(email)
        await rl.record_failure(email)
        await rl.record_success(email)

        await rl.check_and_proceed(email)

    @pytest.mark.asyncio
    async def test_multiple_users_isolated(self):
        rl = RateLimiter()
        user1 = "user1@example.com"
        user2 = "user2@example.com"

        for _ in range(RateLimiter.MAX_FAILURES):
            await rl.record_failure(user1)

        await rl.check_and_proceed(user2)

    @pytest.mark.asyncio
    async def test_lockout_expires(self):
        rl = RateLimiter()
        rl.INITIAL_LOCKOUT = 0.1
        email = "user@example.com"

        for _ in range(RateLimiter.MAX_FAILURES):
            await rl.record_failure(email)

        with pytest.raises(RateLimitException):
            await rl.check_and_proceed(email)

        await asyncio.sleep(0.2)

        await rl.check_and_proceed(email)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        rl = RateLimiter()
        rl.INITIAL_LOCKOUT = 1
        rl.MAX_LOCKOUT = 100
        email = "user@example.com"

        for _ in range(RateLimiter.MAX_FAILURES + 2):
            await rl.record_failure(email)

        state = rl._user_state[email]
        assert state["failed_attempts"] == RateLimiter.MAX_FAILURES + 2
