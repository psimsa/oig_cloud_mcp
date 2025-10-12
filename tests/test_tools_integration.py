"""Integration tests for tools.py module with mocked API calls."""

import pytest
from unittest.mock import Mock, AsyncMock
from tools import (
    get_basic_data,
    get_extended_data,
    get_notifications,
    set_box_mode,
    set_grid_delivery,
)
import tempfile


@pytest.fixture
def mock_whitelist(mocker):
    """Mock the whitelist to allow test users."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test@example.com\n")
        f.write("admin@example.com\n")
        f.flush()

        mock_wl = mocker.patch("tools.whitelist")
        mock_wl.is_allowed.side_effect = lambda email: email.lower() in [
            "test@example.com",
            "admin@example.com",
        ]
        return mock_wl


@pytest.fixture
def mock_rate_limiter(mocker):
    """Mock the rate limiter to allow all requests."""
    mock_rl = mocker.patch("tools.RateLimitException", Exception)
    return mock_rl


@pytest.fixture
def mock_session_cache(mocker):
    """Mock the session cache to return a fake API client."""
    mock_client = AsyncMock()
    mock_client.get_stats = AsyncMock(
        return_value={
            "2205232120": {
                "actual": {
                    "fv_p1": 0,
                    "fv_p2": 0,
                    "bat_c": 89,
                    "bat_p": -467,
                    "aco_p": 253,
                }
            }
        }
    )
    mock_client.get_extended_stats = AsyncMock(return_value={"history": "data"})
    mock_client.get_notifications = AsyncMock(return_value={"notifications": []})
    mock_client.set_box_mode = AsyncMock(return_value=True)
    mock_client.set_grid_delivery = AsyncMock(return_value=True)
    mock_client._phpsessid = "test_session_id_12345"
    mock_client.box_id = "test_box_id"

    mock_cache = mocker.patch("tools.session_cache")
    mock_cache.get_session_id = AsyncMock(return_value=(mock_client, "cached"))

    return mock_cache, mock_client


@pytest.fixture
def mock_context():
    """Create a mock FastMCP Context object with request headers."""
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.request = Mock()
    ctx.request_context.request.headers = {
        "x-oig-email": "test@example.com",
        "x-oig-password": "test_password",
    }
    return ctx


@pytest.fixture
def mock_context_readonly():
    """Create a mock context with readonly access (default)."""
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.request = Mock()
    ctx.request_context.request.headers = {
        "x-oig-email": "test@example.com",
        "x-oig-password": "test_password",
        "x-oig-readonly-access": "true",
    }
    return ctx


@pytest.fixture
def mock_context_write():
    """Create a mock context with write access enabled."""
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.request = Mock()
    ctx.request_context.request.headers = {
        "x-oig-email": "test@example.com",
        "x-oig-password": "test_password",
        "x-oig-readonly-access": "false",
    }
    return ctx


@pytest.fixture
def mock_context_basic_auth():
    """Create a mock context with a valid Basic Auth header."""
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.request = Mock()
    
    # Base64 encode 'test@example.com:test_password'
    token = "dGVzdEBleGFtcGxlLmNvbTp0ZXN0X3Bhc3N3b3Jk"
    ctx.request_context.request.headers = {
        "authorization": f"Basic {token}"
    }
    return ctx


class TestGetBasicData:
    """Tests for get_basic_data tool."""

    @pytest.mark.asyncio
    async def test_success_with_valid_auth(
        self, mock_context, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await get_basic_data(mock_context)

        assert result["status"] == "success"
        assert "data" in result
        assert result["cache_status"] == "cached"
        mock_client.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_email_header(self, mock_whitelist):
        ctx = Mock()
        ctx.request_context = Mock()
        ctx.request_context.request = Mock()
        ctx.request_context.request.headers = {"x-oig-password": "test_password"}

        result = await get_basic_data(ctx)

        assert result["status"] == "error"
        assert "Missing authentication" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_password_header(self, mock_whitelist):
        ctx = Mock()
        ctx.request_context = Mock()
        ctx.request_context.request = Mock()
        ctx.request_context.request.headers = {"x-oig-email": "test@example.com"}

        result = await get_basic_data(ctx)

        assert result["status"] == "error"
        assert "Missing authentication" in result["message"]

    @pytest.mark.asyncio
    async def test_user_not_on_whitelist(self, mock_session_cache):
        mock_cache, mock_client = mock_session_cache

        ctx = Mock()
        ctx.request_context = Mock()
        ctx.request_context.request = Mock()
        ctx.request_context.request.headers = {
            "x-oig-email": "unauthorized@example.com",
            "x-oig-password": "test_password",
        }

        import tools

        original_whitelist = tools.whitelist
        mock_wl = Mock()
        mock_wl.is_allowed = Mock(return_value=False)
        tools.whitelist = mock_wl

        result = await get_basic_data(ctx)

        tools.whitelist = original_whitelist

        assert result["status"] == "error"
        assert "not on whitelist" in result["message"]

    @pytest.mark.asyncio
    async def test_success_with_basic_auth(
        self, mock_context_basic_auth, mock_whitelist, mock_session_cache
    ):
        """Verify that authentication succeeds using the Authorization: Basic header."""
        mock_cache, mock_client = mock_session_cache

        result = await get_basic_data(mock_context_basic_auth)

        assert result["status"] == "success"
        mock_client.get_stats.assert_called_once()
        # Verify the correct email was passed to the session cache
        mock_cache.get_session_id.assert_called_with("test@example.com", "test_password")

    @pytest.mark.asyncio
    async def test_basic_auth_has_priority(
        self, mock_context_basic_auth, mock_whitelist, mock_session_cache
    ):
        """Verify that Basic Auth is used even if custom headers are also present."""
        mock_cache, mock_client = mock_session_cache

        # Add conflicting custom headers to the Basic Auth context
        mock_context_basic_auth.request_context.request.headers.update({
            "x-oig-email": "wrong@example.com",
            "x-oig-password": "wrong_password",
        })

        result = await get_basic_data(mock_context_basic_auth)

        assert result["status"] == "success"
        # Assert that the session cache was called with the credentials from Basic Auth, not the custom headers
        mock_cache.get_session_id.assert_called_with("test@example.com", "test_password")


class TestGetExtendedData:
    """Tests for get_extended_data tool."""

    @pytest.mark.asyncio
    async def test_success_with_valid_params(
        self, mock_context, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await get_extended_data(mock_context, "2024-01-01", "2024-01-31")

        assert result["status"] == "success"
        assert "data" in result
        mock_client.get_extended_stats.assert_called_once_with(
            "history", "2024-01-01", "2024-01-31"
        )


class TestGetNotifications:
    """Tests for get_notifications tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_context, mock_whitelist, mock_session_cache):
        mock_cache, mock_client = mock_session_cache

        result = await get_notifications(mock_context)

        assert result["status"] == "success"
        assert "data" in result
        mock_client.get_notifications.assert_called_once()


class TestSetBoxMode:
    """Tests for set_box_mode tool (write action)."""

    @pytest.mark.asyncio
    async def test_success_with_write_access(
        self, mock_context_write, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await set_box_mode(mock_context_write, "Home 1")

        assert result["status"] == "success"
        assert "Home 1" in result["message"]
        mock_client.set_box_mode.assert_called_once_with("Home 1")

    @pytest.mark.asyncio
    async def test_denied_in_readonly_mode(
        self, mock_context_readonly, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await set_box_mode(mock_context_readonly, "Home 1")

        assert result["status"] == "error"
        assert "readonly mode" in result["message"]
        mock_client.set_box_mode.assert_not_called()

    @pytest.mark.asyncio
    async def test_denied_without_readonly_header(
        self, mock_context, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await set_box_mode(mock_context, "Home 1")

        assert result["status"] == "error"
        assert "readonly mode" in result["message"]
        mock_client.set_box_mode.assert_not_called()


class TestSetGridDelivery:
    """Tests for set_grid_delivery tool (write action)."""

    @pytest.mark.asyncio
    async def test_success_with_write_access(
        self, mock_context_write, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await set_grid_delivery(mock_context_write, 1)

        assert result["status"] == "success"
        mock_client.set_grid_delivery.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_denied_in_readonly_mode(
        self, mock_context_readonly, mock_whitelist, mock_session_cache
    ):
        mock_cache, mock_client = mock_session_cache

        result = await set_grid_delivery(mock_context_readonly, 1)

        assert result["status"] == "error"
        assert "readonly mode" in result["message"]
        mock_client.set_grid_delivery.assert_not_called()
