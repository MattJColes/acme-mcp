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
    """A name the facade returns can be run, through the facade that named it."""
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            facade = (await client.call_tool("perform_maths", {})).data
            assert "addition" in {tool["name"] for tool in facade["tools"]}
            result = await client.call_tool(
                "perform_maths",
                {"operation": "addition", "arguments": {"a": 1, "b": 2}},
            )
    assert result.data["result"] == 3
    assert result.data["operation"] == "addition"


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


async def test_facade_contents_are_scoped_to_the_caller(server, monkeypatch):
    """Every real group holds both maths and english, so tag filtering alone
    would pass the tests above. A caller cleared for maths only proves the
    facade derives its answer under the caller's own auth context."""
    from acme_mcp import auth

    monkeypatch.setitem(auth.GROUP_TAGS, "mathsonly", {"maths"})
    with as_caller(groups=["mathsonly"]):
        async with Client(server) as client:
            data = (await client.call_tool("perform_maths", {})).data
            names = {tool.name for tool in await client.list_tools()}

    assert {tool["name"] for tool in data["tools"]} == MATHS_TOOLS
    assert {skill["name"] for skill in data["skills"]} == {"calculator-usage"}
    assert not ENGLISH_TOOLS & names
    assert "perform_english" not in names


async def test_a_model_reaches_hidden_members_only_through_the_facade(server):
    """Exercise the path a real host takes, not the one ``Client`` allows.

    A host hands the model exactly the tools that came back from ``tools/list``
    and will only dispatch a name from that set. So a hidden member is not in
    the model's vocabulary at all, and calling it by name -- which ``Client``
    happily permits -- proves nothing about whether the model can reach it.
    Routing through the facade is the only path that exists, so it is the path
    the tests have to walk.
    """
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            offered = {tool.name for tool in await client.list_tools()}
            assert "perform_maths" in offered
            assert not (MATHS_TOOLS | ENGLISH_TOOLS) & offered

            index = (await client.call_tool("perform_maths", {})).data
            operation = index["tools"][0]["name"]
            assert operation not in offered  # named, but never listed

            result = (
                await client.call_tool(
                    "perform_maths",
                    {"operation": "multiplication", "arguments": {"a": 3, "b": 4}},
                )
            ).data

    assert result["result"] == 12


@pytest.mark.parametrize(
    "operation", ["sqrt", "vowel_count", "issue_refund", "perform_maths"]
)
async def test_facade_refuses_anything_outside_its_own_domain(server, operation):
    """Unknown, another domain's, and the facade itself are all one answer.

    The facade dispatches only to the members it just listed for this caller,
    so it cannot be used as a way around the access check or the domain split.
    """
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            with pytest.raises(Exception) as excinfo:
                await client.call_tool(
                    "perform_maths", {"operation": operation, "arguments": {}}
                )

    assert "unknown maths operation" in str(excinfo.value).lower()


async def test_hiding_does_not_grant_access(server):
    """Hiding loosens visibility, never permission. An uncleared caller who
    guesses a hidden name is still refused by the access check."""
    with as_caller(groups=["engineering"]):
        async with Client(server) as client:
            with pytest.raises(Exception) as excinfo:
                await client.call_tool("addition", {"a": 1, "b": 2})

    message = str(excinfo.value).lower()
    assert "permission" in message or "authorization" in message


async def test_members_stay_listed_when_their_facade_is_not(server):
    """Never strand a tool. If the door is missing from the listing, the
    members it would have fronted are left in place rather than hidden."""
    from acme_mcp.grouping import HideFacadeMembers

    class FakeTool:
        def __init__(self, name, tags):
            self.name, self.tags = name, tags

    tools = [FakeTool("addition", {"maths"}), FakeTool("whoami", {"public"})]
    middleware = HideFacadeMembers({"maths": "perform_maths"})

    async def call_next(_context):
        return tools

    kept = await middleware.on_list_tools(None, call_next)
    assert {tool.name for tool in kept} == {"addition", "whoami"}
