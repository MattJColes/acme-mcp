"""Authentication and the group-to-tag mapping that access control is built on.

A remote MCP server sits in front of company data, so every caller is
authenticated and we learn *who* they are from their verified token. In
production that token is a JWT minted by the company identity provider and
verified against its public keys; for a local spike we accept a small dict of
static tokens instead.

Once a caller is authenticated, their token claims carry a ``groups`` list.
``GROUP_TAGS`` maps each org group to the set of tool *tags* it is allowed to
see, and :func:`allowed_tags` resolves the current caller's groups into the set
of tags they may use. The access-control middleware in :mod:`acme_mcp.access`
consumes that set.
"""

from __future__ import annotations

import os

from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token

# Which tool tags each org group is allowed to see and call. Tags name a domain
# (orders, billing, ...); a group is cleared for the union of its tags' domains.
GROUP_TAGS: dict[str, set[str]] = {
    "support": {"orders", "billing", "support", "reports"},
    "finance": {"billing", "reports"},
    "admin": {"orders", "billing", "support", "admin", "reports"},
}


# Tags any authenticated caller may use regardless of group — identity and
# health tools that aren't tied to a business domain.
PUBLIC_TAGS: set[str] = {"public"}


def allowed_tags() -> set[str]:
    """Return the set of tool tags the current caller's groups permit.

    Reads ``groups`` from the verified access token. An unauthenticated caller
    gets nothing (the default is "see nothing"). An authenticated caller always
    gets ``PUBLIC_TAGS`` plus the union of the tags their groups map to, so an
    unknown group still sees identity/health tools but no business domains.
    """
    token = get_access_token()
    if token is None:
        return set()
    groups = token.claims.get("groups", [])
    tags = set().union(*(GROUP_TAGS.get(g, set()) for g in groups), set())
    return tags | PUBLIC_TAGS


# Tokens for local development only. Never ship these — they are the moral
# equivalent of a hardcoded password. The keys are bearer tokens; the values are
# the claims a real IdP would have signed.
DEV_TOKENS: dict[str, dict] = {
    "dev-support": {"client_id": "support@acme.dev", "sub": "support@acme.dev", "groups": ["support"]},
    "dev-finance": {"client_id": "finance@acme.dev", "sub": "finance@acme.dev", "groups": ["finance"]},
    "dev-admin": {"client_id": "admin@acme.dev", "sub": "admin@acme.dev", "groups": ["admin"]},
}


def build_auth(env: str | None = None):
    """Return an auth provider for the server.

    ``dev`` hands back a :class:`StaticTokenVerifier` seeded with ``DEV_TOKENS``
    so you can curl the server with a fixed bearer token. Anything else builds a
    :class:`JWTVerifier` pointed at the company identity provider's published
    keys — the only thing you should run in front of real data.
    """
    env = env or os.environ.get("ACME_MCP_ENV", "dev")
    if env == "dev":
        return StaticTokenVerifier(tokens=DEV_TOKENS)
    return JWTVerifier(
        jwks_uri=os.environ.get(
            "ACME_MCP_JWKS_URI", "https://auth.acme.internal/.well-known/jwks.json"
        ),
        issuer=os.environ.get("ACME_MCP_ISSUER", "https://auth.acme.internal"),
        audience=os.environ.get("ACME_MCP_AUDIENCE", "acme-mcp"),
    )
