"""The audit middleware logs the caller, tool, and timing on every call."""

import logging

from fastmcp import Client, FastMCP

from acme_mcp.audit import AuditLog
from tests.conftest import as_caller


def _server() -> FastMCP:
    mcp = FastMCP("test")

    @mcp.tool
    def ping() -> str:
        return "pong"

    @mcp.tool
    def boom() -> str:
        raise ValueError("kaboom")

    mcp.add_middleware(AuditLog())
    return mcp


async def test_audit_logs_user_tool_and_timing(caplog):
    caplog.set_level(logging.INFO, logger="acme_mcp.audit")
    with as_caller(groups=["support"], sub="alice@acme.test"):
        async with Client(_server()) as client:
            await client.call_tool("ping", {})

    records = [r for r in caplog.records if r.name == "acme_mcp.audit"]
    assert len(records) == 1
    rec = records[0]
    assert rec.user == "alice@acme.test"
    assert rec.tool == "ping"
    assert isinstance(rec.ms, int)
    assert rec.error is None


async def test_audit_records_anon_when_unauthenticated(caplog):
    caplog.set_level(logging.INFO, logger="acme_mcp.audit")
    async with Client(_server()) as client:
        await client.call_tool("ping", {})
    rec = next(r for r in caplog.records if r.name == "acme_mcp.audit")
    assert rec.user == "anon"


async def test_audit_records_errors(caplog):
    caplog.set_level(logging.INFO, logger="acme_mcp.audit")
    async with Client(_server()) as client:
        try:
            await client.call_tool("boom", {})
        except Exception:
            pass
    rec = next(r for r in caplog.records if r.name == "acme_mcp.audit" and r.tool == "boom")
    # The tool's ValueError surfaces to middleware wrapped as a ToolError; what
    # matters for the audit trail is that the failure is recorded, not swallowed.
    assert rec.error == "ToolError"
