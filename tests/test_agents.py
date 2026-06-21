"""Agent-behind-a-tool: testing the inner agent with a fake.

The blog's "agents behind tools, or just tools" section says: most tools are
deterministic, but when a task needs open-ended reasoning you put an AI agent
*behind* a tool. The teaching point these tests prove is that the inner agent is
*injectable*, so we can swap in a ``FakeAgent`` and never touch a real LLM in a
test. We assert two contrasting things in one domain:

* the agent-backed ``draft_refund_email`` tool actually fronts the injected
  agent (it forwards a prompt mentioning the order and returns the agent's text);
* the deterministic ``support_macro`` tool returns canned text without ever
  touching the agent.
"""

import pytest
from fastmcp import Client

from acme_mcp.agents import Agent
from acme_mcp.domains import support


class FakeAgent:
    """An inner agent that records its prompt and returns a sentinel."""

    SENTINEL = "FAKE-AGENT-DRAFTED-EMAIL"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.SENTINEL


@pytest.fixture
def fake_agent() -> Agent:
    """Inject a FakeAgent for the duration of a test, then restore the default.

    Restoring matters because the injected agent is module-level global state;
    leaking it would couple tests to each other.
    """
    original = support.get_agent()
    fake = FakeAgent()
    support.set_agent(fake)
    try:
        yield fake
    finally:
        support.set_agent(original)


async def test_draft_refund_email_returns_agent_text(fake_agent):
    async with Client(support.support_server) as client:
        result = await client.call_tool("draft_refund_email", {"order_id": "A1"})
    assert result.data == FakeAgent.SENTINEL


async def test_draft_refund_email_calls_agent_with_order_id(fake_agent):
    async with Client(support.support_server) as client:
        await client.call_tool("draft_refund_email", {"order_id": "ORDER-99"})
    assert len(fake_agent.calls) == 1
    assert "ORDER-99" in fake_agent.calls[0]


async def test_support_macro_is_deterministic_and_skips_agent(fake_agent):
    async with Client(support.support_server) as client:
        result = await client.call_tool("support_macro", {"topic": "refund"})
    assert isinstance(result.data, str)
    assert result.data
    # The deterministic tool must never reach for the inner agent.
    assert fake_agent.calls == []


async def test_support_macro_returns_canned_text_for_known_topic(fake_agent):
    async with Client(support.support_server) as client:
        result = await client.call_tool("support_macro", {"topic": "refund"})
    assert "refund" in result.data.lower()
    assert fake_agent.calls == []


async def test_both_tools_are_tagged_support():
    draft = await support.support_server.get_tool("draft_refund_email")
    macro = await support.support_server.get_tool("support_macro")
    assert "support" in draft.tags
    assert "support" in macro.tags


async def test_default_stub_is_deterministic_and_offline():
    """The shipped default is a deterministic stub, not a real LLM client."""
    from acme_mcp.agents import StubSupportAgent

    stub = StubSupportAgent()
    out_a = await stub.run("draft for order A1")
    out_b = await stub.run("draft for order A1")
    assert isinstance(out_a, str) and out_a
    assert out_a == out_b  # deterministic: no model, same input -> same output
