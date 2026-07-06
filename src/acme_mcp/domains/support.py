"""The support domain: one deterministic tool, one agent-backed tool.

This sub-server shows the "agents behind tools, or just tools" contrast in a
single place:

* :func:`support_macro` is *just a tool* -- a deterministic lookup of canned
  guidance. Same topic in, same text out, no model involved.
* :func:`draft_refund_email` is *an agent behind a tool* -- composing a refund
  email is open-ended prose, so the tool builds a prompt and hands it to an
  inner :class:`~acme_mcp.agents.Agent`.

The inner agent is injected, not hard-wired. The module ships with a
deterministic :class:`~acme_mcp.agents.StubSupportAgent`, and :func:`set_agent`
lets a deployment swap in a real Claude-backed agent (or a test swap in a fake).
The tool always just calls ``await <current agent>.run(prompt)``.
"""

from __future__ import annotations

import re

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from acme_mcp.agents import Agent, StubSupportAgent

support_server = FastMCP("support")

# An order id is an opaque identifier, never prose. Validating it against a tight
# allowlist is what keeps ``draft_refund_email`` honest: the value is interpolated
# into the agent's prompt, so anything other than ``[A-Za-z0-9._-]`` (newlines,
# spaces, punctuation) would let a caller smuggle extra *instructions* into that
# prompt -- the canonical "agent behind a tool" prompt-injection. The allowlist
# also blocks control characters from reaching the ``ctx.info`` audit line (log
# injection) and caps length so a caller can't inflate the prompt into an
# unbounded token bill.
_SAFE_ORDER_ID = re.compile(r"[A-Za-z0-9._-]+")
MAX_ORDER_ID_LEN = 64

# The currently injected inner agent. Defaults to the deterministic stub so the
# server (and the default test path) needs no real LLM. Module-level rather than
# per-call so a deployment configures it once at startup.
_agent: Agent = StubSupportAgent()


def set_agent(agent: Agent) -> None:
    """Inject the inner agent the support tools should use.

    Call this at startup with a real model-backed agent in production, or in a
    test with a fake. Keeping it a single setter is what makes the agent a
    seam rather than a hard dependency.
    """
    global _agent
    _agent = agent


def get_agent() -> Agent:
    """Return the currently injected inner agent (handy for tests/teardown)."""
    return _agent


# Canned guidance for the deterministic tool, keyed by topic.
_MACROS = {
    "refund": (
        "Refund policy: orders can be refunded within 30 days of delivery. "
        "Confirm the order id, verify it's within the window, then issue the "
        "refund via the orders domain."
    ),
    "shipping": (
        "Shipping: standard delivery is 3-5 business days. For a missing "
        "package, confirm the tracking number and open a carrier trace."
    ),
    "returns": (
        "Returns: items must be unused and in original packaging. Email the "
        "customer a prepaid label and log the RMA number."
    ),
}


@support_server.tool(tags={"support"})
def support_macro(topic: str) -> str:
    """Return canned support guidance for a topic. Deterministic, no agent.

    This is the "just a tool" half of the contrast: a fixed lookup, so it's
    fast, free, and identical every time.
    """
    return _MACROS.get(
        topic.lower(),
        f"No macro for '{topic}'. Available topics: {', '.join(sorted(_MACROS))}.",
    )


@support_server.tool(tags={"support"})
async def draft_refund_email(order_id: str, ctx: Context) -> str:
    """Draft a customer-facing refund email for an order.

    Writing on-brand prose is open-ended, so this tool fronts the injected
    inner agent. It builds a scoped prompt from the order id and returns
    whatever text the agent produces -- the tool itself stays deterministic in
    everything *except* the prose, which is exactly the boundary we want.

    ``order_id`` is caller-controlled and gets interpolated into that prompt, so
    it is validated against a tight allowlist first. That is what makes the
    prompt actually scoped rather than as-wide-as-the-attacker's-input: an id
    carrying newlines or prose ("A1. Ignore prior instructions and ...") would
    otherwise ride straight into the instructions the injected model executes.
    """
    if not order_id or not order_id.strip():
        raise ToolError("order_id is required")
    if len(order_id) > MAX_ORDER_ID_LEN or not _SAFE_ORDER_ID.fullmatch(order_id):
        raise ToolError(
            "order_id may only contain letters, digits, '.', '-', and '_'"
        )
    await ctx.info(f"drafting refund email for {order_id}")
    prompt = (
        "Write a brief, friendly refund-confirmation email to the customer for "
        f"order {order_id}. Keep it warm and on-brand; do not promise a refund "
        "amount or date."
    )
    return await _agent.run(prompt)
