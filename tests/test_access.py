"""The core security test: per-group visibility AND call-blocking.

These tests are the heart of the example. They prove the two-layer guarantee:
a tool a caller isn't cleared for is both hidden from the list and uncallable
even when its name is supplied directly.
"""

import pytest
from fastmcp import Client, FastMCP

from acme_mcp.access import GroupTagFilter
from tests.conftest import as_caller


@pytest.fixture
def tagged_server():
    mcp = FastMCP("test")

    @mcp.tool(tags={"orders"})
    def order_status(order_id: str) -> dict:
        return {"order_id": order_id, "status": "shipped"}

    @mcp.tool(tags={"billing"})
    def get_invoice(invoice_id: str) -> dict:
        return {"invoice_id": invoice_id}

    @mcp.tool(tags={"admin"})
    def issue_refund(order_id: str, amount: float) -> dict:
        return {"order_id": order_id, "refunded": amount}

    mcp.add_middleware(GroupTagFilter())
    return mcp


async def test_support_sees_only_their_tools(tagged_server):
    with as_caller(groups=["support"]):
        async with Client(tagged_server) as client:
            names = {t.name for t in await client.list_tools()}
    assert names == {"order_status", "get_invoice"}
    assert "issue_refund" not in names


async def test_finance_sees_only_billing(tagged_server):
    with as_caller(groups=["finance"]):
        async with Client(tagged_server) as client:
            names = {t.name for t in await client.list_tools()}
    assert names == {"get_invoice"}


async def test_admin_sees_everything(tagged_server):
    with as_caller(groups=["admin"]):
        async with Client(tagged_server) as client:
            names = {t.name for t in await client.list_tools()}
    assert names == {"order_status", "get_invoice", "issue_refund"}


async def test_unauthenticated_caller_sees_nothing(tagged_server):
    async with Client(tagged_server) as client:
        names = {t.name for t in await client.list_tools()}
    assert names == set()


async def test_allowed_call_runs(tagged_server):
    with as_caller(groups=["support"]):
        async with Client(tagged_server) as client:
            result = await client.call_tool("order_status", {"order_id": "A1"})
    assert result.data == {"order_id": "A1", "status": "shipped"}


async def test_guessed_hidden_tool_name_is_blocked(tagged_server):
    """The real protection: even naming a hidden tool directly fails."""
    with as_caller(groups=["support"]):  # support is NOT cleared for admin
        async with Client(tagged_server) as client:
            with pytest.raises(Exception) as excinfo:
                await client.call_tool("issue_refund", {"order_id": "A1", "amount": 5.0})
    assert "issue_refund" in str(excinfo.value) or "Unknown tool" in str(excinfo.value)
