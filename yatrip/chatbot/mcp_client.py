"""
MCP client for the Yatrip chatbot.

The chatbot no longer scrapes anything in-process. It loads its tools from the
Yatrip MCP server (see ``yatrip/mcp_server.py``) over the Model Context
Protocol, so the tool surface is discovered at runtime instead of being
hardcoded in the agent.

Transport is chosen by ``MCP_SERVER_TRANSPORT``:
  stdio             spawns ``python -m yatrip.mcp_server`` (default, no server
                    process to babysit)
  streamable_http   connects to a long-running server started with
                    ``manage.py mcp_server --transport streamable-http``

``langchain-mcp-adapters`` opens a fresh MCP session per tool call, so the
loaded tool list is cached and reused across chat messages.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

SERVER_NAME = "yatrip"
TOOL_CACHE_TTL_SECONDS = float(os.getenv("MCP_TOOL_CACHE_TTL", "900"))
TOOL_CACHE_MAX_AGE_ON_ERROR = 30.0

_cache_lock = threading.Lock()
_cached_tools: list[Any] | None = None
_cached_at: float = 0.0


class McpUnavailable(RuntimeError):
    """Raised when the MCP server cannot be reached or exposes no tools."""


def _repo_root() -> Path:
    """Directory that must be on sys.path for ``import yatrip`` to work."""
    return Path(settings.BASE_DIR).parent


def _build_connections() -> dict[str, dict[str, Any]]:
    transport = (settings.MCP_SERVER_TRANSPORT or "stdio").strip().lower()

    if transport == "stdio":
        python_path = str(_repo_root())
        existing = os.environ.get("PYTHONPATH", "")
        env = dict(os.environ)
        env["PYTHONPATH"] = (
            f"{python_path}{os.pathsep}{existing}" if existing else python_path
        )
        return {
            SERVER_NAME: {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", settings.MCP_SERVER_MODULE, "--transport", "stdio"],
                "cwd": str(settings.BASE_DIR),
                "env": env,
            }
        }

    if transport == "sse":
        return {
            SERVER_NAME: {
                "transport": "sse",
                "url": settings.MCP_SERVER_URL,
                "timeout": settings.MCP_SERVER_TIMEOUT,
            }
        }

    return {
        SERVER_NAME: {
            "transport": "streamable_http",
            "url": settings.MCP_SERVER_URL,
            "timeout": settings.MCP_SERVER_TIMEOUT,
        }
    }


async def get_tools(*, force_refresh: bool = False) -> list[Any]:
    """
    Return the MCP tool list as LangChain tools, cached across requests.

    Raises :class:`McpUnavailable` when the server cannot be reached, so the
    caller can fall back to a plain LLM reply instead of failing the request.
    """
    global _cached_tools, _cached_at

    if not settings.MCP_SERVER_ENABLED:
        raise McpUnavailable("MCP_SERVER_ENABLED is False")

    now = time.monotonic()
    with _cache_lock:
        fresh = (
            _cached_tools is not None
            and (now - _cached_at) < TOOL_CACHE_TTL_SECONDS
        )
        if fresh and not force_refresh:
            return list(_cached_tools)

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(_build_connections())
        tools = await client.get_tools(server_name=SERVER_NAME)
    except Exception as exc:  # noqa: BLE001
        # Serve a recently cached list rather than losing tools entirely.
        with _cache_lock:
            if _cached_tools and (now - _cached_at) < TOOL_CACHE_MAX_AGE_ON_ERROR:
                logger.warning("MCP refresh failed (%s); reusing cached tools", exc)
                return list(_cached_tools)
        raise McpUnavailable(f"could not load tools from the MCP server: {exc}") from exc

    if not tools:
        with _cache_lock:
            if _cached_tools:
                return list(_cached_tools)
        raise McpUnavailable("the MCP server exposed no tools")

    with _cache_lock:
        _cached_tools = list(tools)
        _cached_at = time.monotonic()

    logger.info(
        "Loaded %d MCP tool(s) from %s: %s",
        len(tools),
        SERVER_NAME,
        ", ".join(getattr(tool, "name", "?") for tool in tools),
    )
    return list(tools)


def clear_cache() -> None:
    """Drop the cached tool list. Useful in tests and after redeploys."""
    global _cached_tools, _cached_at
    with _cache_lock:
        _cached_tools = None
        _cached_at = 0.0


def tool_names(tools: list[Any]) -> set[str]:
    return {getattr(tool, "name", "") for tool in tools}
