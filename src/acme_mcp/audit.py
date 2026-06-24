"""The audit trail: who called what, and how long it took.

Once an MCP brokers authenticated access to company data, "who pulled that
customer's record?" stops being nice-to-have. Middleware is the right home for
it because it wraps every tool call in one place without touching each tool, and
it's also where rate limiting or anomaly checks would later hang.

In production you'd ship these lines to CloudWatch as structured JSON; here we
just emit them on the ``acme_mcp.audit`` logger so tests can assert on them.
"""

from __future__ import annotations

import logging
import time

from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext

log = logging.getLogger("acme_mcp.audit")


class AuditLog(Middleware):
    """Log the caller, tool, and timing for every tool invocation."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token = get_access_token()
        user = token.claims.get("sub") if token else "anon"
        # Record the caller's groups too: "who did it" is the subject, but "what
        # were they cleared as" is what answers whether an access decision was
        # right after the fact.
        groups = token.claims.get("groups", []) if token else []
        tool = context.message.name
        start = time.perf_counter()
        error: str | None = None
        try:
            return await call_next(context)
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            error = type(exc).__name__
            raise
        finally:
            ms = round((time.perf_counter() - start) * 1000)
            log.info(
                "tool_call",
                extra={"user": user, "groups": groups, "tool": tool, "ms": ms, "error": error},
            )
