"""The server publishes its tagged companion skills as MCP resources."""

import pytest
from fastmcp import Client

from tests.conftest import as_caller

SKILLS = {
    "handle-downloads": "# Handling file downloads from acme-mcp",
    "calculator-usage": "# Using the acme-mcp maths tools",
    "english-analysis-caveats": "# Interpreting acme-mcp English analysis",
}


def skill_uris() -> set[str]:
    return {
        uri
        for skill in SKILLS
        for uri in (
            f"skill://{skill}/SKILL.md",
            f"skill://{skill}/_manifest",
        )
    }


@pytest.mark.parametrize("groups", [["support"], ["finance"], ["admin"]])
async def test_cleared_callers_can_discover_and_read_skills(server, groups):
    with as_caller(groups=groups):
        async with Client(server) as client:
            uris = {str(resource.uri) for resource in await client.list_resources()}
            assert skill_uris() <= uris
            for skill, heading in SKILLS.items():
                result = await client.read_resource(f"skill://{skill}/SKILL.md")
                assert heading in result[0].text


async def test_unknown_group_cannot_discover_or_read_skills(server):
    with as_caller(groups=["engineering"]):
        async with Client(server) as client:
            uris = {str(resource.uri) for resource in await client.list_resources()}
            assert skill_uris().isdisjoint(uris)
            for skill in SKILLS:
                with pytest.raises(Exception):
                    await client.read_resource(f"skill://{skill}/SKILL.md")
