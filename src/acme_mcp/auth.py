"""Authentication and the group-to-tag mapping that access control is built on.

A remote MCP server sits in front of company data, so every caller is
authenticated and we learn *who* they are from their verified token. In
production that token is a JWT minted by the company identity provider and
verified against its public keys; for a local spike we accept a small dict of
static tokens instead.

Once a caller is authenticated, their token claims carry a ``groups`` list.
``GROUP_TAGS`` maps each org group to the set of tool *tags* it is allowed to
see, and :func:`tags_for_groups` resolves a token's groups claim into the set
of tags it permits. The access-control check in :mod:`acme_mcp.access`
consumes that set.
"""

from __future__ import annotations

import os

from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier

# Sentinel tag meaning "every tag, including ones from domains added later".
# A group cleared for it sees and can call every tool regardless of the tool's
# own tags -- that is what "admin sees everything" actually requires. Listing the
# domains explicitly (as admin used to) silently drops any domain composed in
# later, e.g. the proxied analytics service, which carries the ``analytics`` tag
# that no explicit list mentioned.
ALL_TAGS = "*"

# Which tool tags each org group is allowed to see and call. Tags name a domain
# (orders, billing, ...); a group is cleared for the union of its tags' domains.
# ``admin`` is cleared for the wildcard so it stays a true superset as new
# domains are mounted, rather than needing this list edited for each one.
GROUP_TAGS: dict[str, set[str]] = {
    "support": {"orders", "billing", "support", "reports"},
    "finance": {"billing", "reports"},
    "admin": {ALL_TAGS},
}


# Tags any authenticated caller may use regardless of group — identity and
# health tools that aren't tied to a business domain.
PUBLIC_TAGS: set[str] = {"public"}


def tags_for_groups(groups) -> set[str]:
    """Resolve a ``groups`` claim into the set of tool tags it permits.

    Takes the ``groups`` value straight from the token rather than reading
    global request state, so the access-control check in :mod:`acme_mcp.access`
    can pass the claim through. An empty or malformed claim yields only
    ``PUBLIC_TAGS`` (identity and health tools), so an unknown group still sees
    those but no business domains. A group cleared for ``ALL_TAGS`` (e.g.
    ``admin``) yields a set containing the wildcard, which
    :func:`acme_mcp.access.group_access` treats as "every tag".
    """
    names = _normalize_groups(groups)
    tags = set().union(*(GROUP_TAGS.get(g, set()) for g in names))
    return tags | PUBLIC_TAGS


def _normalize_groups(groups) -> list[str]:
    """Coerce the ``groups`` claim into a clean list of group names.

    IdP tokens are not as tidy as the happy path assumes, and this value drives
    an access decision, so it must never crash or misbehave on odd input:

    * ``None`` (an explicit ``"groups": null`` in the token) or a missing claim
      -> no groups. ``dict.get(..., [])`` does *not* cover the explicit-null
      case, so iterating it directly would raise ``TypeError`` and surface a raw
      500-style error to the caller.
    * a bare string (an IdP that emits a single group as ``"admin"`` rather than
      ``["admin"]``) -> a one-element list. Iterating the string directly would
      loop over its *characters*, match nothing, and silently lock the user out.
    * any other unexpected type -> no groups (fail closed).

    Every path fails closed: a caller can never gain tags from malformed input,
    only lose them, so this hardens availability without weakening access.
    """
    if groups is None:
        return []
    if isinstance(groups, str):
        return [groups]
    if isinstance(groups, (list, tuple, set)):
        return [g for g in groups if isinstance(g, str)]
    return []


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
