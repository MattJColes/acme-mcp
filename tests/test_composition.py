"""Multi-domain composition: mounting in-process domains and proxying a remote one.

Mounting keeps each domain independently deployable and stops a single server
becoming a monolith. The remote analytics domain is composed via a proxy; we
prove the proxy mechanism works in-memory (pointing it at a local sub-server)
without standing up a real remote service.
"""

from fastmcp import Client, FastMCP

from acme_mcp.server import build_server
from fastmcp.server import create_proxy
from tests.conftest import as_caller


async def test_mounted_domains_expose_their_tools(server):
    # Admin is cleared for every domain, so the full mounted surface is visible.
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
    for expected in {"order_status", "get_invoice", "issue_refund", "draft_refund_email", "export_report"}:
        assert expected in names


async def test_proxy_forwards_tools_from_another_server():
    # Stand up a tiny "remote" analytics domain and proxy it.
    analytics = FastMCP("analytics")

    @analytics.tool(tags={"analytics"})
    def top_products(limit: int = 3) -> list[str]:
        """Return the top selling products."""
        return ["widget", "gadget", "gizmo"][:limit]

    proxy = create_proxy(analytics)

    async with Client(proxy) as client:
        names = {t.name for t in await client.list_tools()}
        assert "top_products" in names
        result = await client.call_tool("top_products", {"limit": 2})
    assert result.data == ["widget", "gadget"]


async def test_proxy_can_be_mounted_into_main_server():
    analytics = FastMCP("analytics")

    @analytics.tool(tags={"analytics"})
    def health() -> str:
        return "ok"

    main = build_server(env="dev")
    main.mount(create_proxy(analytics))

    # analytics isn't in any group's tag set, so it stays hidden from the filter,
    # but the mount itself succeeds and the tool is registered on the server.
    tool = await main.get_tool("health")
    assert tool is not None
