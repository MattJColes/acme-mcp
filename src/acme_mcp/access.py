"""Per-group tool access control via FastMCP's callable-based authorization.

The whole point of a company MCP is that each team sees only the domains it is
cleared for -- the finance team doesn't see order tools, and no one but admin
can reach the refund tool. (Support is cleared for billing here, so it *can* see
the read-only invoice lookup; what it can't reach is the privileged ``admin``
domain -- see ``GROUP_TAGS`` in :mod:`acme_mcp.auth` for the exact grants.)

FastMCP 3 ships callable-based authorization for exactly this. An auth check is
a function that takes an :class:`AuthContext` (the caller's token plus the
component being accessed) and returns ``True`` to allow or ``False`` to deny.
Wiring that check through :class:`AuthMiddleware` enforces it across every
component in two places at once:

* it filters denied tools out of ``tools/list``, so they never clutter the
  model's context; and
* it blocks a direct call to a denied tool even if the model guesses the name.

One tradeoff to know about: the built-in does not pretend a denied tool doesn't
exist. A blocked call surfaces an "insufficient permissions" error that names
the tool, and that differs from the "not found" error a genuinely-unknown tool
returns, so a prober can confirm a hidden tool's name. Hiding that too takes a
thin extra middleware that normalises both errors to "Unknown tool"; we don't
add it here, but it's the one reason you'd reach past the built-in.
"""

from __future__ import annotations

from fastmcp.server.auth import AuthContext
from fastmcp.server.middleware import AuthMiddleware

from acme_mcp.auth import ALL_TAGS, tags_for_groups


def group_access(ctx: AuthContext) -> bool:
    """Allow a caller whose groups clear them for the component's tags.

    ``True`` when the caller holds the wildcard (``ALL_TAGS``, e.g. admin) or
    when any of the component's tags is in the set the caller's groups map to.
    ``public``-tagged tools pass for any authenticated caller; an unauthenticated
    caller (``ctx.token is None``) is denied everything, which is what hides
    every business tool from ``tools/list`` before any auth provider rejects the
    request outright.
    """
    if ctx.token is None:
        return False
    allowed = tags_for_groups(ctx.token.claims.get("groups"))
    if ALL_TAGS in allowed:
        return True
    return bool(set(ctx.component.tags) & allowed)


def build_access_middleware() -> AuthMiddleware:
    """Server-wide authorization: hide denied tools and block calls to them."""
    return AuthMiddleware(auth=group_access)
