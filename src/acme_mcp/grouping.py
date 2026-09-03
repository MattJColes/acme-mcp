"""Keep a facade's members out of ``tools/list`` while leaving them callable.

A category facade (``perform_maths``) is only worth registering if it actually
shrinks what the model reads. On its own it does not: the facade and the four
maths tools it indexes all carry the ``maths`` tag, so a cleared caller sees
both the door and everything behind it.

The fix is to split visibility from permission, which FastMCP already keeps
apart. :class:`acme_mcp.access.group_access` decides what a caller *may* reach
and runs on every request. This middleware only touches the ``tools/list``
response, so a hidden tool is still callable by name -- which is the whole
point, because the facade hands the model those names and their input schemas.

That is a deliberate loosening of "hidden means unreachable", and it is safe
here for one reason: nothing about *authorization* changed. A caller who was
never cleared for ``maths`` still cannot see or call any of it. Hiding applies
only to tools the caller is already allowed to run.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Sequence
from contextvars import ContextVar

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import Tool

# Set while a facade is building its answer. The facade asks the server for the
# caller's tools through the normal pipeline, because that is what applies the
# access check -- but it must see the members it exists to index, so hiding
# stands down for the duration. Nothing else in the pipeline is skipped.
_listing_for_facade: ContextVar[bool] = ContextVar(
    "acme_listing_for_facade", default=False
)


@contextlib.contextmanager
def listing_for_facade() -> Iterator[None]:
    """Ask :class:`HideFacadeMembers` to stand down for this listing."""
    token = _listing_for_facade.set(True)
    try:
        yield
    finally:
        _listing_for_facade.reset(token)


class HideFacadeMembers(Middleware):
    """Drop tools from ``tools/list`` when a visible facade already indexes them.

    ``facades`` maps a category tag to the name of the tool that fronts it. A
    tool is hidden when it carries one of those tags and is not itself a facade.
    """

    def __init__(self, facades: dict[str, str]) -> None:
        self.facades = facades

    async def on_list_tools(
        self, context: MiddlewareContext, call_next
    ) -> Sequence[Tool]:
        tools = await call_next(context)
        if _listing_for_facade.get():
            return tools
        doors = {tool.name for tool in tools} & set(self.facades.values())
        # Only hide behind a door the caller can actually see. If the facade was
        # filtered out (not cleared, or disabled), leave its members listed
        # rather than stranding tools the caller is allowed to call.
        hidden = {tag for tag, name in self.facades.items() if name in doors}
        return [
            tool
            for tool in tools
            if tool.name in doors or not (hidden & set(tool.tags))
        ]
