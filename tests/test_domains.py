"""Tests for the business-domain sub-servers (orders, billing, admin).

Each domain is exercised through the in-memory FastMCP ``Client`` (no network),
which is how the model would actually reach the tools. The backends stand in for
DynamoDB/an internal API and are plain in-memory dicts, so tests can seed and
inspect them directly without any AWS.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from acme_mcp.domains import admin, billing, orders


# --- tagging contract -------------------------------------------------------

def _tags(tool) -> set[str]:
    """Tags as carried on the client-side tool representation (under meta)."""
    return set((tool.meta or {}).get("fastmcp", {}).get("tags", []))


async def test_orders_tools_tagged_orders():
    async with Client(orders.orders_server) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert "order_status" in tools
    assert "orders" in _tags(tools["order_status"])


async def test_billing_tools_tagged_billing():
    async with Client(billing.billing_server) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert "get_invoice" in tools
    assert "billing" in _tags(tools["get_invoice"])


async def test_admin_tools_tagged_admin():
    async with Client(admin.admin_server) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert "issue_refund" in tools
    assert "admin" in _tags(tools["issue_refund"])


# --- orders.order_status ----------------------------------------------------

async def test_order_status_happy_path():
    async with Client(orders.orders_server) as client:
        result = await client.call_tool("order_status", {"order_id": "A1"})
    assert result.data["order_id"] == "A1"
    assert result.data["status"] == "shipped"


async def test_order_status_unknown_order():
    async with Client(orders.orders_server) as client:
        result = await client.call_tool("order_status", {"order_id": "nope"})
    assert result.data["order_id"] == "nope"
    assert result.data["status"] == "not_found"


# --- billing.get_invoice ----------------------------------------------------

async def test_get_invoice_happy_path():
    async with Client(billing.billing_server) as client:
        result = await client.call_tool("get_invoice", {"invoice_id": "INV-1"})
    assert result.data["invoice_id"] == "INV-1"
    assert result.data["status"] == "paid"
    assert result.data["amount"] == 42.0


async def test_get_invoice_unknown_invoice():
    async with Client(billing.billing_server) as client:
        result = await client.call_tool("get_invoice", {"invoice_id": "nope"})
    assert result.data["invoice_id"] == "nope"
    assert result.data["status"] == "not_found"


# --- admin.issue_refund -----------------------------------------------------

async def test_issue_refund_returns_confirmation():
    async with Client(admin.admin_server) as client:
        result = await client.call_tool(
            "issue_refund", {"order_id": "A1", "amount": 9.5}
        )
    assert result.data == {
        "order_id": "A1",
        "refunded": 9.5,
        "status": "refund_issued",
    }


async def test_issue_refund_records_refund():
    backend = admin.AdminBackend()
    admin._backend = backend
    try:
        async with Client(admin.admin_server) as client:
            await client.call_tool("issue_refund", {"order_id": "B2", "amount": 12.0})
        refunds = backend.list_refunds("B2")
        assert len(refunds) == 1
        assert refunds[0]["amount"] == 12.0
    finally:
        admin._backend = admin.AdminBackend()


@pytest.mark.parametrize("amount", [0, -1, -0.01])
async def test_issue_refund_rejects_non_positive_amount(amount):
    """The money tool must not record a zero or negative refund."""
    backend = admin.AdminBackend()
    admin._backend = backend
    try:
        async with Client(admin.admin_server) as client:
            with pytest.raises(Exception):
                await client.call_tool(
                    "issue_refund", {"order_id": "A1", "amount": amount}
                )
        # Nothing should have been written.
        assert backend.list_refunds() == []
    finally:
        admin._backend = admin.AdminBackend()


async def test_issue_refund_rejects_blank_order_id():
    backend = admin.AdminBackend()
    admin._backend = backend
    try:
        async with Client(admin.admin_server) as client:
            with pytest.raises(Exception):
                await client.call_tool("issue_refund", {"order_id": "  ", "amount": 5.0})
        assert backend.list_refunds() == []
    finally:
        admin._backend = admin.AdminBackend()
