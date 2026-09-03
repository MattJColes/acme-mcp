"""The assembled acme MCP server.

This is where the pieces fit together, in the order the blog post builds them:

1. Authenticate every caller (:func:`acme_mcp.auth.build_auth`).
2. Mount each business domain as its own sub-server, so the codebase stays
   split by domain rather than one giant file.
3. Publish companion skills as MCP resources.
4. Wrap every tool call in audit logging (:class:`acme_mcp.audit.AuditLog`).
5. Filter the components each caller sees and can use by their group
   (:func:`acme_mcp.access.build_access_middleware`).
6. Drop the tools a category facade already fronts from ``tools/list``, so the
   model reads one line per category instead of every tool in it
   (:class:`acme_mcp.grouping.HideFacadeMembers`). They stay callable.

A local stdio server is a convenience; a remote HTTP server is production
infrastructure and gets treated like it. ``main`` runs stdio by default and
HTTP when ``ACME_MCP_REMOTE`` is set.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from acme_mcp.access import build_access_middleware
from acme_mcp.audit import AuditLog
from acme_mcp.auth import build_auth
from acme_mcp.domains.admin import admin_server
from acme_mcp.domains.billing import billing_server
from acme_mcp.domains.english import english_server
from acme_mcp.domains.maths import maths_server
from acme_mcp.domains.orders import orders_server
from acme_mcp.domains.reports import reports_server
from acme_mcp.domains.support import support_server
from acme_mcp.grouping import HideFacadeMembers, listing_for_facade
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.providers.skills import SkillsDirectoryProvider

# The separately-owned analytics domain runs as its own service. We proxy it
# rather than holding it in-process; this is the closest thing to lazy loading,
# and it keeps that domain independently deployable. It is wired here for
# illustration and only mounted when ACME_MCP_ANALYTICS_URL is set, so the
# server still starts offline.
ANALYTICS_URL = os.environ.get(
    "ACME_MCP_ANALYTICS_URL", "https://analytics.acme.internal/mcp"
)
SKILLS_DIR = Path(__file__).parent / "skills"


def _facade(mcp: FastMCP, *, name: str, tag: str, description: str) -> str:
    """Register the single tool that fronts one tagged domain.

    The facade is the only tool from its domain that reaches the model, so it
    has to do both jobs. Called with no arguments it returns the domain's index
    (every member's name, description and input schema, plus companion skills).
    Called with an ``operation`` it runs that member and returns its result.

    Dispatch is not a convenience. A host hands the model exactly the tools that
    came back from ``tools/list``, so a member hidden from that listing is not
    in the model's vocabulary and it can never emit a call for one. Publishing
    the schema in a result does not change that: the schema is result data, not
    a tool definition. Routing through the facade is what makes a hidden member
    reachable at all.

    Returns the facade's name, so ``build_server`` can tell
    :class:`~acme_mcp.grouping.HideFacadeMembers` which door fronts which tag.
    """

    async def facade(
        operation: str | None = None, arguments: dict | None = None
    ) -> dict:
        # The members, as this caller sees them. Listing through the normal
        # pipeline is what applies the access check; hiding stands down so the
        # facade can see what it exists to front.
        with listing_for_facade():
            listed = await mcp.list_tools()
        members = {
            tool.name: tool
            for tool in listed
            if tag in tool.tags and tool.name != name
        }

        if operation is not None:
            if operation not in members:
                # Names an operation this caller cannot reach, whether it is
                # unknown, another domain's, or one they are not cleared for.
                raise ToolError(f"Unknown {tag} operation: {operation}")
            result = await mcp.call_tool(operation, arguments or {})
            # FastMCP wraps a non-dict return under "result"; unwrap it so the
            # facade's own "result" key holds the value, not a nested envelope.
            structured = result.structured_content or {}
            return {
                "category": tag,
                "operation": operation,
                "result": structured.get("result", structured),
            }

        skills = []
        for resource in await mcp.list_resources():
            info = getattr(resource, "skill_info", None)
            uri = str(resource.uri)
            if (
                info is not None
                and tag in info.frontmatter.get("tags", [])
                and uri.endswith("/SKILL.md")
            ):
                skills.append(
                    {
                        "name": info.name,
                        "description": info.description,
                        "uri": uri,
                    }
                )
        return {
            "category": tag,
            "description": description,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in members.values()
            ],
            "skills": skills,
        }

    mcp.tool(facade, name=name, description=description, tags={tag})
    return name


def build_server(env: str | None = None) -> FastMCP:
    """Assemble the full acme server: auth, domains, audit, and group filtering."""
    mcp = FastMCP("acme", auth=build_auth(env))

    @mcp.tool(tags={"public"})
    def whoami() -> dict:
        """Return the caller's verified identity and groups."""
        token = get_access_token()
        claims = token.claims if token else {}
        return {
            "user": claims.get("sub"),
            "groups": claims.get("groups", []),
        }

    # Mount each domain in-process. No namespace: these are domains of one
    # product, so tool names stay clean (order_status, not orders_order_status).
    for sub in (
        orders_server,
        billing_server,
        admin_server,
        support_server,
        reports_server,
        maths_server,
        english_server,
    ):
        mcp.mount(sub)

    mcp.add_provider(SkillsDirectoryProvider(roots=SKILLS_DIR))
    facades = {
        "maths": _facade(
            mcp,
            name="perform_maths",
            tag="maths",
            description="List the available maths operations and companion skills.",
        ),
        "english": _facade(
            mcp,
            name="perform_english",
            tag="english",
            description="List the available English analysis tools and companion skills.",
        ),
    }

    # Audit first so it wraps the outermost call. Then the two filters, in the
    # order their results depend on each other: the access middleware runs
    # innermost and decides who may reach each tool, and HideFacadeMembers sees
    # what survived that, so it only ever hides behind a door the caller can see.
    mcp.add_middleware(AuditLog())
    mcp.add_middleware(HideFacadeMembers(facades))
    mcp.add_middleware(build_access_middleware())
    return mcp


def mount_analytics(mcp: FastMCP, url: str | None = None) -> None:
    """Proxy a separately-owned analytics MCP service into the main server.

    Demonstrates composing a remote domain via a proxy. Called from ``main``
    only when an analytics URL is configured.
    """
    from fastmcp.server import create_proxy

    analytics = create_proxy(url or ANALYTICS_URL)
    mcp.mount(analytics)


def wire_dev_s3():
    """Back ``export_report`` with an in-process moto S3 for dev runs.

    In dev there is no real AWS, so without this the reports domain is the one
    part of the example that can't run end-to-end. moto ships in the ``dev``
    extra; when it's importable we start a process-lifetime mock, create the
    export bucket, and hand the client to the reports seam. Returns the started
    mock (so a test can stop it) or ``None`` when moto isn't installed.
    """
    try:
        from moto import mock_aws
    except ImportError:
        import logging

        logging.getLogger("acme_mcp.server").warning(
            "moto not installed; export_report needs real AWS credentials "
            "and the export bucket (pip install -e '.[dev]' for a local fake)"
        )
        return None
    import boto3

    from acme_mcp.domains import reports

    mock = mock_aws()
    mock.start()
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=reports.EXPORT_BUCKET)
    reports.set_s3_client(s3)
    return mock


def main() -> None:
    """Console entry point. stdio locally; HTTP when ACME_MCP_REMOTE is set."""
    mcp = build_server()

    if os.environ.get("ACME_MCP_ENV", "dev") == "dev":
        wire_dev_s3()

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
