"""Category facade tests: top-level doors over maths and English tools."""

from __future__ import annotations

import pytest
from fastmcp import Client

from tests.conftest import as_caller

MATHS_TOOLS = {"addition", "subtraction", "multiplication", "division"}
ENGLISH_TOOLS = {"vowel_count", "noun_count", "verb_count", "word_count"}


@pytest.mark.parametrize("groups", [["support"], ["finance"], ["admin"]])
async def test_cleared_callers_see_both_facades(server, groups):
    with as_caller(groups=groups):
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
    assert {"perform_maths", "perform_english"} <= names


async def test_perform_maths_lists_only_maths_tools(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            data = (await client.call_tool("perform_maths", {})).data

    assert data["category"] == "maths"
    assert {tool["name"] for tool in data["tools"]} == MATHS_TOOLS
    assert all(tool["description"] for tool in data["tools"])
    assert all(tool["input_schema"] for tool in data["tools"])
    assert all(
        {"a", "b"} <= set(tool["input_schema"]["properties"])
        for tool in data["tools"]
    )


async def test_perform_english_lists_only_english_tools(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            data = (await client.call_tool("perform_english", {})).data

    assert data["category"] == "english"
    assert {tool["name"] for tool in data["tools"]} == ENGLISH_TOOLS
    assert all(tool["description"] for tool in data["tools"])
    assert all(tool["input_schema"] for tool in data["tools"])


async def test_uncleared_caller_cannot_see_or_call_facades(server):
    with as_caller(groups=["engineering"]):
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert "perform_maths" not in names
            assert "perform_english" not in names
            with pytest.raises(Exception) as excinfo:
                await client.call_tool("perform_maths", {})

    message = str(excinfo.value).lower()
    assert "permission" in message or "authorization" in message


async def test_facade_named_tool_is_callable(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            facade = (await client.call_tool("perform_maths", {})).data
            assert "addition" in {tool["name"] for tool in facade["tools"]}
            result = await client.call_tool("addition", {"a": 1, "b": 2})
    assert result.data == 3


@pytest.mark.parametrize(
    ("facade", "skill", "heading"),
    [
        (
            "perform_maths",
            "calculator-usage",
            "# Using the acme-mcp maths tools",
        ),
        (
            "perform_english",
            "english-analysis-caveats",
            "# Interpreting acme-mcp English analysis",
        ),
    ],
)
async def test_facade_companion_skill_uri_is_readable(
    server, facade, skill, heading
):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            data = (await client.call_tool(facade, {})).data
            skills = {item["name"]: item for item in data["skills"]}
            assert skill in skills
            assert skills[skill]["description"]
            assert skills[skill]["uri"] == f"skill://{skill}/SKILL.md"
            result = await client.read_resource(skills[skill]["uri"])
    assert heading in result[0].text
