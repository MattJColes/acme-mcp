"""The server publishes its companion skill as reports-scoped MCP resources."""

import pytest
from fastmcp import Client

from tests.conftest import as_caller

SKILL_URI = "skill://handle-downloads/SKILL.md"
MANIFEST_URI = "skill://handle-downloads/_manifest"


@pytest.mark.parametrize("groups", [["support"], ["finance"], ["admin"]])
async def test_reports_callers_can_discover_and_read_skill(server, groups):
    with as_caller(groups=groups):
        async with Client(server) as client:
            uris = {str(resource.uri) for resource in await client.list_resources()}
            result = await client.read_resource(SKILL_URI)

    assert {SKILL_URI, MANIFEST_URI} <= uris
    assert "# Handling file downloads from acme-mcp" in result[0].text


async def test_unknown_group_cannot_discover_or_read_skill(server):
    with as_caller(groups=["engineering"]):
        async with Client(server) as client:
            uris = {str(resource.uri) for resource in await client.list_resources()}
            assert SKILL_URI not in uris
            with pytest.raises(Exception):
                await client.read_resource(SKILL_URI)
