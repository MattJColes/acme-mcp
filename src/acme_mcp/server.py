"""The assembled acme MCP server.

This is where the pieces fit together, in the order the blog post builds them:

1. Authenticate every caller (:func:`acme_mcp.auth.build_auth`).
2. Mount each business domain as its own sub-server, so the codebase stays
   split by domain rather than one giant file.
3. Wrap every tool call in audit logging (:class:`acme_mcp.audit.AuditLog`).
4. Filter the tools each caller sees and can run by their group
   (:class:`acme_mcp.access.GroupTagFilter`).

A local stdio server is a convenience; a remote HTTP server is production
infrastructure and gets treated like it. ``main`` runs stdio by default and
HTTP when ``ACME_MCP_REMOTE`` is set.
"""

from __future__ import annotations

import os

from fastmcp import Context, FastMCP

from acme_mcp.access import GroupTagFilter
from acme_mcp.audit import AuditLog
from acme_mcp.auth import build_auth
from acme_mcp.domains.admin import admin_server
from acme_mcp.domains.billing import billing_server
from acme_mcp.domains.orders import orders_server
from acme_mcp.domains.reports import reports_server
from acme_mcp.domains.support import support_server
from fastmcp.server.dependencies import get_access_token

# The separately-owned analytics domain runs as its own service. We proxy it
# rather than holding it in-process; this is the closest thing to lazy loading,
# and it keeps that domain independently deployable. It is wired here for
# illustration and only mounted when ACME_MCP_ANALYTICS_URL is set, so the
# server still starts offline.
ANALYTICS_URL = os.environ.get(
    "ACME_MCP_ANALYTICS_URL", "https://analytics.acme.internal/mcp"
)


def build_server(env: str | None = None) -> FastMCP:
    """Assemble the full acme server: auth, domains, audit, and group filtering."""
    mcp = FastMCP("acme", auth=build_auth(env))

    @mcp.tool(tags={"public"})
    def whoami(ctx: Context) -> dict:
        """Return the caller's verified identity and groups."""
        token = get_access_token()
        claims = token.claims if token else {}
        return {
            "user": claims.get("sub"),
            "groups": claims.get("groups", []),
        }

    # Mount each domain in-process. No namespace: these are domains of one
    # product, so tool names stay clean (order_status, not orders_order_status).
    for sub in (orders_server, billing_server, admin_server, support_server, reports_server):
        mcp.mount(sub)

    # Audit first so it wraps the outermost call; the group filter sits inside
    # it and decides who may reach each tool.
    mcp.add_middleware(AuditLog())
    mcp.add_middleware(GroupTagFilter())
    return mcp


def mount_analytics(mcp: FastMCP, url: str | None = None) -> None:
    """Proxy a separately-owned analytics MCP service into the main server.

    Demonstrates composing a remote domain via a proxy. Called from ``main``
    only when an analytics URL is configured.
    """
    from fastmcp.server import create_proxy

    analytics = create_proxy(url or ANALYTICS_URL)
    mcp.mount(analytics)


def main() -> None:
    """Console entry point. stdio locally; HTTP when ACME_MCP_REMOTE is set."""
    mcp = build_server()

    if os.environ.get("ACME_MCP_ANALYTICS_URL"):
        mount_analytics(mcp)

    if os.environ.get("ACME_MCP_REMOTE"):
        # A web service in front of company data: reachable, multi-user, authed.
        mcp.run(
            transport="http",
            host=os.environ.get("ACME_MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("ACME_MCP_PORT", "8000")),
        )
    else:
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
