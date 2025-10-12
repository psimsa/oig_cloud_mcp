from mcp.server.fastmcp import FastMCP, Context
from session_manager import session_cache
from security import whitelist, RateLimitException
from transformer import transform_get_stats
from typing import Tuple

# Create a tools instance
oig_tools = FastMCP("OIG Cloud Tools")


def _get_creds_from_headers(ctx: Context) -> Tuple[str, str]:
    """Extract email and password from request headers.

    Returns:
        Tuple of (email, password)

    Raises:
        ValueError: If headers are missing or credentials not found
    """
    request = ctx.request_context.request
    if not request:
        raise ValueError("Request context not available")

    # Access headers from Starlette Request object
    headers = request.headers

    email = headers.get("x-oig-email")
    password = headers.get("x-oig-password")

    if not email or not password:
        raise ValueError(
            "Missing required authentication headers: X-OIG-Email and X-OIG-Password"
        )

    return email, password


def _is_readonly(ctx: Context) -> bool:
    """Checks if the client is in readonly mode. Defaults to True (safe)."""
    request = ctx.request_context.request
    if not request:
        return True  # Default to readonly if context is missing

    # Header value is a string 'true' or 'false'
    readonly_header = request.headers.get("x-oig-readonly-access", "true")
    return readonly_header.lower() != "false"


@oig_tools.tool()
async def get_basic_data(ctx: Context) -> dict:
    """Fetches a real-time snapshot of the PV system from the user's OIG Cloud account.

    Uses an authenticated OigCloudApi client supplied by `session_manager.SessionCache`.
    Credentials are extracted from X-OIG-Email and X-OIG-Password headers.
    """
    try:
        email, password = _get_creds_from_headers(ctx)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {
            "status": "error",
            "message": "Authorization denied: User not on whitelist.",
        }

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
        return {
            "status": "error",
            "message": f"Failed to fetch data from OIG Cloud: {e}",
        }

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
async def get_extended_data(ctx: Context, start_date: str, end_date: str) -> dict:
    """Retrieves historical time-series data for a specified period from OIG Cloud.

    The `name` parameter for the underlying API is hardcoded to "history".
    Credentials are extracted from X-OIG-Email and X-OIG-Password headers.
    """
    try:
        email, password = _get_creds_from_headers(ctx)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {
            "status": "error",
            "message": "Authorization denied: User not on whitelist.",
        }

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
        return {
            "status": "error",
            "message": f"Failed to fetch historical data from OIG Cloud: {e}",
        }

    session_id = getattr(client, "_phpsessid", "") or ""
    preview = f"{session_id[:4]}...{session_id[-4:]}" if session_id else "(unknown)"

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": preview,
        "data": live_data,
    }


@oig_tools.tool()
async def get_notifications(ctx: Context) -> dict:
    """Fetches system alerts, warnings, and informational messages from OIG Cloud.

    Credentials are extracted from X-OIG-Email and X-OIG-Password headers.
    """
    try:
        email, password = _get_creds_from_headers(ctx)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {
            "status": "error",
            "message": "Authorization denied: User not on whitelist.",
        }

    try:
        client, status = await session_cache.get_session_id(email, password)
    except RateLimitException as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError:
        return {"status": "error", "message": "Authentication failed with OIG Cloud."}

    try:
        live_data = await client.get_notifications()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch notifications from OIG Cloud: {e}",
        }

    session_id = getattr(client, "_phpsessid", "") or ""
    preview = f"{session_id[:4]}...{session_id[-4:]}" if session_id else "(unknown)"

    return {
        "status": "success",
        "cache_status": status,
        "session_id_preview": preview,
        "data": live_data,
    }


@oig_tools.tool()
async def set_box_mode(ctx: Context, mode: str) -> dict:
    """
    Sets the operating mode of the main control box (e.g., 'Home 1', 'Home 2').
    This is a write operation and requires readonly access to be disabled by setting
    the 'X-OIG-Readonly-Access' header to 'false'.
    """
    try:
        email, password = _get_creds_from_headers(ctx)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # Readonly safety check
    if _is_readonly(ctx):
        return {
            "status": "error",
            "message": (
                "Action denied. Server is in readonly mode. "
                "Set 'X-OIG-Readonly-Access: false' header to allow actions."
            ),
        }

    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {
            "status": "error",
            "message": "Authorization denied: User not on whitelist.",
        }

    try:
        client, status = await session_cache.get_session_id(email, password)
        # The underlying API client needs the box_id, which is fetched during get_stats
        if not getattr(client, "box_id", None):
            await client.get_stats()

        success = await client.set_box_mode(mode)
        if success:
            return {
                "status": "success",
                "message": f"Box mode successfully set to '{mode}'.",
            }
        else:
            return {
                "status": "error",
                "message": "API call succeeded but failed to set box mode.",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred while setting box mode: {e}",
        }


@oig_tools.tool()
async def set_grid_delivery(ctx: Context, mode: int) -> dict:
    """
    Sets the grid delivery mode (e.g., 1 for enabled, 0 for disabled).
    This is a write operation and requires readonly access to be disabled by setting
    the 'X-OIG-Readonly-Access' header to 'false'.
    """
    try:
        email, password = _get_creds_from_headers(ctx)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # Readonly safety check
    if _is_readonly(ctx):
        return {
            "status": "error",
            "message": (
                "Action denied. Server is in readonly mode. "
                "Set 'X-OIG-Readonly-Access: false' header to allow actions."
            ),
        }

    # Whitelist enforcement
    if not whitelist.is_allowed(email):
        return {
            "status": "error",
            "message": "Authorization denied: User not on whitelist.",
        }

    try:
        client, status = await session_cache.get_session_id(email, password)
        # The underlying API client needs the box_id, which is fetched during get_stats
        if not getattr(client, "box_id", None):
            await client.get_stats()

        success = await client.set_grid_delivery(mode)
        if success:
            return {
                "status": "success",
                "message": f"Grid delivery mode successfully set to '{mode}'.",
            }
        else:
            return {
                "status": "error",
                "message": "API call succeeded but failed to set grid delivery mode.",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred while setting grid delivery mode: {e}",
        }
