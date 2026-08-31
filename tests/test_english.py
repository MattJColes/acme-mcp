"""Tests for the English text-analysis domain via the assembled server."""

from __future__ import annotations

import pytest
from fastmcp import Client

from tests.conftest import as_caller, tool_tags

ENGLISH_TOOLS = ["vowel_count", "noun_count", "verb_count", "word_count"]


@pytest.mark.parametrize("tool", ENGLISH_TOOLS)
async def test_english_tools_tagged_english(server, tool):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            tools = {t.name: t for t in await client.list_tools()}
    assert tool in tools
    assert "english" in tool_tags(tools[tool])


async def test_vowel_count(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            assert (
                await client.call_tool("vowel_count", {"text": "Hello, World!"})
            ).data == 3
            assert (await client.call_tool("vowel_count", {"text": ""})).data == 0
            assert (
                await client.call_tool("vowel_count", {"text": "12345"})
            ).data == 0


async def test_noun_count(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = (
                await client.call_tool(
                    "noun_count", {"text": "The dogs chased the ball"}
                )
            ).data
            empty = (await client.call_tool("noun_count", {"text": ""})).data

    assert {"dogs", "ball"} <= set(result["words"])
    assert result["count"] == len(result["words"])
    assert empty == {"count": 0, "words": []}


async def test_verb_count(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = (
                await client.call_tool(
                    "verb_count", {"text": "running and jumping"}
                )
            ).data
            empty = (await client.call_tool("verb_count", {"text": ""})).data

    assert result == {"count": 2, "words": ["running", "jumping"]}
    assert empty == {"count": 0, "words": []}


async def test_word_count(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = (
                await client.call_tool(
                    "word_count", {"text": "the cat and the hat"}
                )
            ).data
            empty = (await client.call_tool("word_count", {"text": ""})).data

    assert result == {"words": 5, "unique_words": 4}
    assert empty == {"words": 0, "unique_words": 0}
