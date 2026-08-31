"""Maths domain: deterministic arithmetic, one tool per operation."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

maths_server = FastMCP("maths")


@maths_server.tool(tags={"maths"})
def addition(a: int | float, b: int | float) -> int | float:
    """Add two numbers."""
    return a + b


@maths_server.tool(tags={"maths"})
def subtraction(a: int | float, b: int | float) -> int | float:
    """Subtract b from a; negative results are returned as-is."""
    return a - b


@maths_server.tool(tags={"maths"})
def multiplication(a: int | float, b: int | float) -> int | float:
    """Multiply two numbers."""
    return a * b


@maths_server.tool(tags={"maths"})
def division(a: int | float, b: int | float) -> float:
    """Divide a by b, returning a float; reject a zero divisor."""
    if b == 0:
        raise ToolError("division by zero")
    return a / b
