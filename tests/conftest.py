"""Shared test fixtures and helpers.

Tests drive the server with the in-memory ``Client`` (no network), and simulate
an authenticated caller by setting the auth context var directly to an
``AccessToken`` carrying the claims a real IdP would have signed. This is the
documented way to unit-test FastMCP auth without minting real JWTs.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

import pytest
from mcp.server.auth.middleware.auth_context import (
    AccessToken,
    AuthenticatedUser,
    auth_context_var,
)


def make_token(
    *,
    sub: str = "user@acme.test",
    groups: list[str] | None = None,
    scopes: list[str] | None = None,
) -> AccessToken:
    """Build an access token with the claims a verified caller would carry."""
    return AccessToken(
        token="test-token",
        client_id=sub,
        scopes=scopes or [],
        claims={"sub": sub, "groups": groups or []},
    )


@contextlib.contextmanager
def as_caller(groups: list[str] | None = None, *, sub: str = "user@acme.test") -> Iterator[AccessToken]:
    """Run the enclosed block as an authenticated caller in the given groups."""
    token = make_token(sub=sub, groups=groups)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        yield token
    finally:
        auth_context_var.reset(reset)


@pytest.fixture
def server():
    """A fully-assembled acme server with auth, audit, and group filtering."""
    from acme_mcp.server import build_server

    return build_server(env="dev")
