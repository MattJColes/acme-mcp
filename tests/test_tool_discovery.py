"""Native tool discovery after domain-tag access filtering."""

from __future__ import annotations

import pytest
from fastmcp import Client

from tests.conftest import as_caller, tool_tags

MATHS_TOOLS = {"addition", "subtraction", "multiplication", "division"}
ENGLISH_TOOLS = {"vowel_count", "noun_count", "verb_count", "word_count"}


@pytest.mark.parametrize("groups", [["support"], ["finance"], ["admin"]])
async def test_group_grants_expose_native_tools(server, groups):
    with as_caller(groups=groups):
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}

    assert MATHS_TOOLS | ENGLISH_TOOLS <= names
    assert {"perform_maths", "perform_english"}.isdisjoint(names)


async def test_native_tools_keep_tags_and_typed_schemas(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}

    assert tool_tags(tools["addition"]) == {"maths"}
    assert set(tools["addition"].inputSchema["properties"]) == {"a", "b"}
    assert tool_tags(tools["vowel_count"]) == {"english"}
    assert set(tools["vowel_count"].inputSchema["properties"]) == {"text"}


async def test_native_tool_is_called_directly(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = await client.call_tool("multiplication", {"a": 3, "b": 4})

    assert result.data == 12


async def test_ungranted_domain_is_hidden_and_blocked(server):
    with as_caller(groups=["engineering"]):
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert MATHS_TOOLS.isdisjoint(names)
            with pytest.raises(Exception) as excinfo:
                await client.call_tool("addition", {"a": 1, "b": 2})

    message = str(excinfo.value).lower()
    assert "permission" in message or "authorization" in message


async def test_one_domain_tag_scopes_tools_and_skills(server, monkeypatch):
    from acme_mcp import auth

    monkeypatch.setitem(auth.GROUP_TAGS, "mathsonly", {"maths"})
    with as_caller(groups=["mathsonly"]):
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
            resources = {
                str(resource.uri) for resource in await client.list_resources()
            }

    assert MATHS_TOOLS <= names
    assert ENGLISH_TOOLS.isdisjoint(names)
    assert "skill://calculator-usage/SKILL.md" in resources
    assert "skill://english-analysis-caveats/SKILL.md" not in resources
