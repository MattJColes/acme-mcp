# Support Agent Specification

## Purpose

Put an LLM agent behind a tool on a tight leash. Deterministic answers stay
deterministic (`support_macro` never touches the agent); the one
agent-fronted tool (`draft_refund_email`) allowlist-validates its input
before any of it reaches the agent prompt; and the agent itself sits behind
an injectable seam so tests never hit a real model.

## Requirements

### Requirement: Macros are deterministic and skip the agent

<!-- anchor: support.macro --> `support_macro` SHALL be a `support`-tagged tool that answers known topics
(`refund`, `shipping`, `returns`) from a static macro table. It SHALL NOT
invoke the inner agent.

#### Scenario: Known topic returns canned text
- **WHEN** `support_macro` is called with topic `refund`
- **THEN** the canned macro text is returned and the agent is never called

### Requirement: Agent-fronted drafting validates before prompting

<!-- anchor: support.draft-refund-email --> `draft_refund_email` SHALL be a `support`-tagged tool that validates
`order_id` against the safe-id allowlist (`[A-Za-z0-9._-]+` full match, max
64 chars, non-blank) and reject with `ToolError` BEFORE interpolating it
into the agent prompt or invoking the agent. Only a validated id may appear
in the prompt.

#### Scenario: Injection-shaped input never reaches the agent
- **WHEN** `draft_refund_email` is called with an order id containing
  spaces, prose, newlines, NULs, or exceeding 64 chars
- **THEN** a `ToolError` is raised and the agent is not invoked

#### Scenario: Safe id is drafted
- **WHEN** `draft_refund_email` is called with an id like `ORD-1042.v2`
- **THEN** the agent runs with a scoped prompt containing that id and its
  text is returned

### Requirement: Injectable agent seam

<!-- anchor: support.agent-seam --> The inner agent SHALL be reachable only through the module seam: an `Agent`
protocol (single `async run(prompt) -> str`), a `set_agent` setter for
injection, and a deterministic offline `StubSupportAgent` default. Tests
inject fakes through `set_agent`; nothing constructs a real model client.

#### Scenario: Tests inject a fake agent
- **GIVEN** a fake agent registered via `set_agent`
- **WHEN** `draft_refund_email` runs
- **THEN** the fake's output is returned verbatim

#### Scenario: Default stub is offline and deterministic
- **WHEN** the default `StubSupportAgent` runs twice on the same prompt
- **THEN** it returns identical text without any network access
