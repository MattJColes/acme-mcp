"""acme-mcp: a worked example of a secure FastMCP 3 server.

See the companion blog post "Building and securing MCP servers with FastMCP".
The public entry point is :func:`acme_mcp.server.build_server`.
"""

__all__ = ["build_server"]


def build_server(*args, **kwargs):
    """Lazy re-export so importing the package doesn't pull in every domain."""
    from acme_mcp.server import build_server as _build_server

    return _build_server(*args, **kwargs)
