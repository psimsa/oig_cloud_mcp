from mcp.server.fastmcp import FastMCP
from session_manager import session_cache
from security import whitelist, RateLimitException
from transformer import transform_get_stats

# Create a tools instance
oig_tools = FastMCP("OIG Cloud Tools")


@oig_tools.tool()
async def get_basic_data(email: str, password: str) -> dict:
    """Fetches a real-time snapshot of the PV system from the user's OIG Cloud account.

    Uses an authenticated OigCloudApi client supplied by `session_manager.SessionCache`.
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        client, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    # Use the authenticated client to fetch live stats
    try:
        live_data = await client.get_stats()
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch data from OIG Cloud: {e}"}

    session_id = getattr(client, "_phpsessid", "") or ""
    preview = f"{session_id[:4]}...{session_id[-4:]}" if session_id else "(unknown)"

    # Transform the raw API response into the AI-friendly schema
    try:
        transformed_data = transform_get_stats(live_data)
    except Exception:
        # Fall back to raw payload if transformation fails for any reason
        transformed_data = live_data

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": preview,
        "data": transformed_data,
    }


@oig_tools.tool()
async def get_extended_data(email: str, password: str, start_date: str, end_date: str) -> dict:
    """Retrieves historical time-series data for a specified period from OIG Cloud.

    The `name` parameter for the underlying API is hardcoded to "history".
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        client, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    # Call the extended stats endpoint with the name "history"
    try:
        live_data = await client.get_extended_stats("history", start_date, end_date)
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch historical data from OIG Cloud: {e}"}

    session_id = getattr(client, "_phpsessid", "") or ""
    preview = f"{session_id[:4]}...{session_id[-4:]}" if session_id else "(unknown)"

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": preview,
        "data": live_data,
    }


@oig_tools.tool()
async def get_notifications(email: str, password: str) -> dict:
    """Fetches system alerts, warnings, and informational messages from OIG Cloud.
    """
    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {"status": "error", "message": "Authorization denied: User not on whitelist."}

    try:
        client, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    try:
        live_data = await client.get_notifications()
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch notifications from OIG Cloud: {e}"}

    session_id = getattr(client, "_phpsessid", "") or ""
    preview = f"{session_id[:4]}...{session_id[-4:]}" if session_id else "(unknown)"

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": preview,
        "data": live_data,
    }
