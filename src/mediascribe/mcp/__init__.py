"""MCP server for mediascribe — expose pipeline tools to LLM agents."""

from __future__ import annotations


def run_server() -> None:
    """Start the MCP server (stdio transport)."""
    from mediascribe.mcp.server import mcp

    mcp.run()
