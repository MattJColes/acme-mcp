"""Tests for the maths domain: deterministic arithmetic via the assembled server.

The tools are exercised through the in-memory ``Client`` against the full
assembled server (auth, audit, and group filtering included) as an ``admin``
caller: the wildcard group is cleared for every domain, so these tests do
not depend on ``GROUP_TAGS`` grants. Group-scoped visibility is covered by
``test_tool_discovery.py``.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from tests.conftest import as_caller

async def test_addition_int_and_float(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            assert (
                await client.call_tool("addition", {"a": 2, "b": 3})
            ).data == 5
            assert (
                await client.call_tool("addition", {"a": 0.5, "b": 1.25})
            ).data == 1.75


async def test_subtraction_negative_result(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            assert (
                await client.call_tool("subtraction", {"a": 3, "b": 10})
            ).data == -7


async def test_multiplication_float(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            assert (
                await client.call_tool("multiplication", {"a": 4, "b": 2.5})
            ).data == 10.0


async def test_division_returns_float(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            assert (
                await client.call_tool("division", {"a": 7, "b": 2})
            ).data == 3.5


async def test_division_by_zero_raises(server):
    with as_caller(groups=["admin"]):
        async with Client(server) as client:
            with pytest.raises(Exception, match="division by zero"):
                await client.call_tool("division", {"a": 1, "b": 0})
