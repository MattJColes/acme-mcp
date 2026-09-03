"""Tests for the English text-analysis domain via the assembled server."""

from __future__ import annotations

from fastmcp import Client

from tests.conftest import as_caller

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


async def test_word_count_ignores_standalone_apostrophes(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            result = (
                await client.call_tool(
                    "word_count", {"text": "' ''' don't"}
                )
            ).data

    assert result == {"words": 1, "unique_words": 1}
