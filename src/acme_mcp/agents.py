"""Inner agents that sit *behind* a tool.

Most tools in this server are deterministic: given the same input they do the
same thing, and that's exactly what you want for anything that touches money or
customer data. But some tasks are genuinely open-ended -- "write a warm, on-brand
refund email for this order" is not something you express as an if/else. That's
when you put an AI agent *behind* a tool.

The discipline that keeps this safe is twofold:

* **Narrow scope.** The inner agent gets one job and (in production) its own
  small set of tools and credentials -- not the keys to the whole company. The
  tool in front of it is the boundary that the rest of the system reasons about.
* **Injectability.** The agent is an interface (:class:`Agent`), and the tool
  calls whatever instance is currently injected. In production you'd inject a
  Claude-backed implementation; in tests you inject a fake. The tool code never
  changes, and a test never makes a network call to a real model.
"""

from __future__ import annotations

import typing


@typing.runtime_checkable
class Agent(typing.Protocol):
    """The narrow interface an inner agent must satisfy.

    Deliberately tiny: a single ``run(prompt) -> text`` method. The tool in
    front knows nothing about how the answer is produced -- real model, canned
    stub, or test fake -- which is what makes the agent swappable.
    """

    async def run(self, prompt: str) -> str:  # pragma: no cover - protocol
        ...


class StubSupportAgent:
    """A deterministic stand-in for a real, Claude-backed support agent.

    In production this would wrap a real model call -- its own narrow system
    prompt, its own scoped tools, and its own credentials -- to actually reason
    over the prompt and draft prose. Here it returns a templated string so the
    server runs end-to-end with no network and no LLM. Because the tool injects
    its agent (see :mod:`acme_mcp.domains.support`), swapping this stub for the
    real implementation -- or for a test fake -- is a one-line change.
    """

    async def run(self, prompt: str) -> str:
        return (
            "Hi there,\n\n"
            "Thanks for your patience. We've processed your refund request "
            f"and a confirmation will follow shortly.\n\n"
            "(drafted by the support agent for: "
            f"{prompt})\n\n"
            "Best,\nAcme Support"
        )
