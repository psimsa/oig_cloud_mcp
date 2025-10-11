from mcp.server.fastmcp import FastMCP
from session_manager import session_cache
from security import whitelist, RateLimitException
import json
from typing import Any, Dict

# Create a tools instance
oig_tools = FastMCP("OIG Cloud Tools")

# Mock data will be loaded from sample-response.json
MOCK_DATA: Dict[str, Any] = {}
try:
    with open("sample-response.json", "r") as f:
        MOCK_DATA = json.load(f)
except FileNotFoundError:
    print("Warning: sample-response.json not found. Tools will return empty data.")
    MOCK_DATA = {}


@oig_tools.tool()
async def get_basic_data(email: str, password: str) -> dict:
    """Fetches a real-time snapshot of the PV system.

    Returns mock data loaded from `sample-response.json` in the `data` field.
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        session_id, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": f"{session_id[:4]}...{session_id[-4:]}",
        "data": MOCK_DATA,
    }


@oig_tools.tool()
async def get_extended_data(email: str, password: str, start_date: str, end_date: str) -> dict:
    """Retrieves historical time-series data for a specified period.

    Date range parameters are accepted for compatibility but ignored for the
    current mock implementation.
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        session_id, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": f"{session_id[:4]}...{session_id[-4:]}",
        "data": MOCK_DATA,
    }


@oig_tools.tool()
async def get_notifications(email: str, password: str) -> dict:
    """Fetches system alerts, warnings, and informational messages.

    The sample data does not contain notifications; return an empty list.
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        session_id, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": f"{session_id[:4]}...{session_id[-4:]}",
        "data": {"notifications": []},
    }
