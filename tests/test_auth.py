"""Auth and identity through the fully-assembled server.

These run against ``build_server`` (auth + all domains + middleware), exercising
the end-to-end path: an authenticated caller's groups decide what they see, and
``whoami`` reflects their verified claims.
"""

import pytest
from fastmcp import Client

from acme_mcp.auth import DEV_TOKENS, build_auth
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from tests.conftest import as_caller


async def test_whoami_returns_verified_identity(server):
    with as_caller(groups=["support"], sub="alice@acme.test"):
        async with Client(server) as client:
            result = await client.call_tool("whoami", {})
    assert result.data == {"user": "alice@acme.test", "groups": ["support"]}


async def test_whoami_visible_to_every_authenticated_caller(server):
    # whoami is tagged "public", so even a caller in an unknown group sees it.
    with as_caller(groups=["nobody"]):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
    assert "whoami" in names


async def test_support_sees_support_domains_not_admin(server):
    with as_caller(groups=["support"]):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
    assert {"order_status", "get_invoice"} <= names
    assert "issue_refund" not in names


async def test_finance_sees_billing_not_orders(server):
    with as_caller(groups=["finance"]):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
    assert "get_invoice" in names
    assert "order_status" not in names


async def test_admin_can_call_refund(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = await client.call_tool(
                "issue_refund", {"order_id": "A1", "amount": 9.99}
            )
    assert result.data["refunded"] == 9.99


async def test_support_cannot_call_refund_even_by_name(server):
    with as_caller(groups=["support"]):
        async with Client(server) as client:
            with pytest.raises(Exception):
                await client.call_tool("issue_refund", {"order_id": "A1", "amount": 9.99})


async def test_unknown_group_sees_only_public_and_cannot_call_business_tools(server):
    """An authenticated caller in a group no one mapped gets identity tools only.

    Default-deny: an unrecognised group resolves to just PUBLIC_TAGS, so business
    tools are both hidden and uncallable even when named directly.
    """
    with as_caller(groups=["nobody"]):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            assert names == {"whoami"}
            with pytest.raises(Exception):
                await client.call_tool("order_status", {"order_id": "A1"})
            with pytest.raises(Exception):
                await client.call_tool("issue_refund", {"order_id": "A1", "amount": 5.0})


async def test_null_groups_claim_does_not_crash(server):
    """A token with ``groups: null`` must fail closed, not raise a 500.

    ``dict.get("groups", [])`` returns ``None`` (not the default) when the key is
    present-but-null, and iterating ``None`` would raise ``TypeError`` that
    surfaces to the caller. The caller should instead be treated as group-less.
    """
    from mcp.server.auth.middleware.auth_context import (
        AccessToken,
        AuthenticatedUser,
        auth_context_var,
    )

    token = AccessToken(
        token="t", client_id="u", scopes=[], claims={"sub": "u", "groups": None}
    )
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            assert names == {"whoami"}  # public only, no crash
            result = await client.call_tool("whoami", {})
    finally:
        auth_context_var.reset(reset)
    assert result.data == {"user": "u", "groups": None}


async def test_scalar_string_groups_claim_is_treated_as_one_group(server):
    """A bare-string ``groups`` claim ("admin") must not be iterated per-character.

    Some IdPs emit a single group as a string rather than a one-element list.
    Iterating the string would loop over characters, match no group, and lock the
    caller out. It should be treated as the single group it names.
    """
    from mcp.server.auth.middleware.auth_context import (
        AccessToken,
        AuthenticatedUser,
        auth_context_var,
    )

    token = AccessToken(
        token="t", client_id="u", scopes=[], claims={"sub": "u", "groups": "admin"}
    )
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            # "admin" resolves to the admin group -> sees the refund tool.
            assert "issue_refund" in names
    finally:
        auth_context_var.reset(reset)


def test_normalize_groups_fails_closed_on_odd_types():
    from acme_mcp.auth import _normalize_groups

    assert _normalize_groups(None) == []
    assert _normalize_groups("admin") == ["admin"]
    assert _normalize_groups(["a", "b"]) == ["a", "b"]
    assert _normalize_groups(("a",)) == ["a"]
    # Non-string members are dropped; wholly unexpected types yield no groups.
    assert _normalize_groups([1, "a", None]) == ["a"]
    assert _normalize_groups(123) == []
    assert _normalize_groups({"a": 1}) == []


def test_build_auth_dev_is_static_verifier():
    assert isinstance(build_auth("dev"), StaticTokenVerifier)


def test_build_auth_prod_is_jwt_verifier():
    assert isinstance(build_auth("prod"), JWTVerifier)


def test_dev_tokens_carry_groups():
    assert DEV_TOKENS["dev-support"]["groups"] == ["support"]
