# acme-mcp

A worked example of a **secure [FastMCP](https://gofastmcp.com) 3 server**: JWT
auth, per-group tool access, audit logging, multi-domain composition, and file
delivery via S3 signed URLs. Companion to the post *"Building and securing MCP
servers with FastMCP"*.

This is the "wired up and runnable" version of the snippets in that post, so you
can see how the pieces fit instead of stitching them together yourself.

## What's in here

| Concern | Where | What it shows |
| --- | --- | --- |
| Auth | `src/acme_mcp/auth.py` | `JWTVerifier` in prod, `StaticTokenVerifier` for local dev; the group → tag map |
| Per-group access | `src/acme_mcp/access.py` | `GroupTagFilter` middleware: hides tools **and** blocks calls to hidden ones |
| Audit trail | `src/acme_mcp/audit.py` | `AuditLog` middleware logging user / tool / timing on every call |
| Deterministic domains | `src/acme_mcp/domains/{orders,billing,admin}.py` | plain typed tools over a data backend |
| Agent behind a tool | `src/acme_mcp/domains/support.py` + `agents.py` | an injectable, mockable inner agent on a tight leash |
| File delivery | `src/acme_mcp/domains/reports.py` + `storage.py` | upload to S3, return a short-lived signed URL — never the bytes |
| Composition | `src/acme_mcp/server.py` | mount in-process domains; proxy a separately-owned one |
| Companion skill | `skills/handle-downloads/SKILL.md` | how an agent should treat a returned `download_url` |

## Install

```bash
pip install -e ".[dev]"
```

## Run

Local (stdio) — a convenience for a single user, e.g. wired into an editor:

```bash
python -m acme_mcp.server
```

Remote (HTTP) — production infrastructure: reachable, multi-user, authenticated:

```bash
ACME_MCP_REMOTE=1 ACME_MCP_ENV=prod python -m acme_mcp.server
```

### Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `ACME_MCP_ENV` | `dev` | `dev` uses static dev tokens; anything else uses JWT verification |
| `ACME_MCP_REMOTE` | unset | when set, serve over HTTP instead of stdio |
| `ACME_MCP_HOST` / `ACME_MCP_PORT` | `0.0.0.0` / `8000` | HTTP bind address |
| `ACME_MCP_JWKS_URI` / `ACME_MCP_ISSUER` / `ACME_MCP_AUDIENCE` | acme defaults | JWT verifier settings (prod) |
| `ACME_MCP_ANALYTICS_URL` | unset | when set, proxy a remote analytics MCP service and mount it |

In `dev`, the `StaticTokenVerifier` accepts these bearer tokens, each mapped to a
group: `dev-support`, `dev-finance`, `dev-admin` (see `auth.py`). A `support`
caller sees orders/billing/support/reports tools; `finance` sees billing/reports;
`admin` sees everything.

## How access control works

Every request is authenticated, then two middleware run:

1. `AuditLog` records who called what.
2. `GroupTagFilter` enforces access in **two** places — it hides tools the caller
   isn't cleared for (`on_list_tools`) *and* blocks calls to them
   (`on_call_tool`), so a guessed tool name still fails. Filtering only the list
   would leave a named tool callable; filtering the call is what shuts the door.

Tools are tagged by domain (`orders`, `billing`, `admin`, `support`, `reports`);
`GROUP_TAGS` in `auth.py` maps each org group to the tags it may use. The
identity tool `whoami` is tagged `public` so any authenticated caller can see it.

> **Note on the post's `Transform`:** the draft post sketches this filter as a
> `Transform`/`add_transform`. This repo implements it as FastMCP **middleware**
> (`on_list_tools` + `on_call_tool`), which is the supported per-request
> mechanism in FastMCP 3 and delivers the same two-layer guarantee.

## Test

The whole example is covered with TDD and mocks — no real AWS, IdP, or network:

```bash
python -m pytest -q
```

Tests use FastMCP's in-memory `Client`, simulate authenticated callers by setting
the auth context to a token with specific claims (`tests/conftest.py`), mock S3
with `moto`, and inject a fake inner agent for the agent-backed tool.
