# Audit Specification

## Purpose

Record who called what, with timing and outcome, for every tool call —
including failing ones. The audit trail is middleware, so no tool can opt
out of it.

## Requirements

### Requirement: Every tool call is audited

<!-- anchor: audit.on-call --> `AuditLog.on_call_tool` SHALL emit one `tool_call` log record per call on
the `acme_mcp.audit` logger, carrying the caller's `sub` (or `"anon"` when
unauthenticated), their `groups` (or `[]`), the tool name, and the elapsed
milliseconds. Failures SHALL still be recorded — the exception type name is
captured in an `error` field and the exception re-raised — with emission in
a `finally` block so no path skips it.

#### Scenario: Successful call is recorded
- **GIVEN** an authenticated caller invoking a tool
- **WHEN** the call completes
- **THEN** a record with user, groups, tool, and integer `ms` is logged with
  `error` unset

#### Scenario: Failing call is recorded
- **GIVEN** a tool that raises `ToolError`
- **WHEN** the call fails
- **THEN** a record is still logged with `error: "ToolError"` and the error
  propagates to the caller

#### Scenario: Anonymous caller is recorded
- **GIVEN** no access token in context
- **WHEN** a call is attempted
- **THEN** the record shows user `"anon"` and empty groups
