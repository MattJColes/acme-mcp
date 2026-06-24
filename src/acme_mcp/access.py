"""Per-group tool access control, enforced as middleware.

The whole point of a company MCP is that the support team doesn't see finance
tools and a read-only user can't reach a refund tool. We enforce that in *two*
places, because hiding a tool from the list is presentation, not protection:

* ``on_list_tools`` hides tools the caller isn't cleared for, so they never
  clutter the model's context.
* ``on_call_tool`` is the one that actually protects you: it blocks a call to a
  disallowed tool even if the model guesses the name, so a hidden tool is
  genuinely uncallable rather than merely invisible.

Filter only the list and a guessed tool name still runs; filtering the call is
what closes the door.

This uses FastMCP middleware rather than any bespoke transform API: middleware
runs per request, so it sees the authenticated caller and can decide based on
their groups via :func:`acme_mcp.auth.allowed_tags`.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from acme_mcp.auth import ALL_TAGS, allowed_tags


def cleared_for(tool_tags, allowed) -> bool:
    """Whether a caller cleared for ``allowed`` may use a tool tagged ``tool_tags``.

    The caller is cleared if they hold the wildcard (``ALL_TAGS``, e.g. admin) or
    if any of the tool's tags is in their allowed set. Using a helper keeps the
    list and call paths enforcing exactly the same rule.
    """
    if ALL_TAGS in allowed:
        return True
    return bool(set(tool_tags) & allowed)


class GroupTagFilter(Middleware):
    """Show and run only the tools a caller's groups allow."""

    async def on_list_tools(self, context: MiddlewareContext, call_next) -> Sequence:
        tools = await call_next(context)
        tags = allowed_tags()
        return [t for t in tools if cleared_for(t.tags, tags)]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        name = context.message.name
        tags = allowed_tags()
        tool = await context.fastmcp_context.fastmcp.get_tool(name)
        if not (tool and cleared_for(tool.tags, tags)):
            # Same answer whether the tool is unknown or just off-limits: don't
            # leak the existence of tools the caller isn't cleared for.
            raise ToolError(f"Unknown tool: {name}")
        return await call_next(context)
