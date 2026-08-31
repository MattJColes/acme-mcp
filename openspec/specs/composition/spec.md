# Composition Specification

## Purpose

Assemble the server from independently-owned domains: mount the in-process
domain servers, optionally proxy a remote analytics service, and register
the security middleware in an order that keeps the audit trail outermost.

## Requirements

### Requirement: Server assembly and middleware order

<!-- anchor: composition.build-server --> `build_server` SHALL construct the `acme` FastMCP server with auth from
`build_auth`, mount the seven domain servers (orders, billing, admin,
support, reports, maths, english) un-namespaced, publish companion
skills from the skills directory (a SKILL.md and manifest resource per
skill), and register middleware with `AuditLog` added BEFORE
`GroupTagFilter` — audit wraps outermost so even blocked calls are
recorded.

#### Scenario: Mounted domains expose their tools
- **GIVEN** an `admin` caller on a built server
- **WHEN** tools are listed
- **THEN** the full surface appears, including `export_report`,
  `draft_refund_email` and `perform_maths`

#### Scenario: Skills publish from the directory
- **GIVEN** a built server with skills under the skills directory
- **WHEN** an `admin` caller lists resources
- **THEN** each skill's `SKILL.md` and `_manifest` resources appear

#### Scenario: Blocked call still audited
- **GIVEN** a caller invoking a tool they are not cleared for
- **WHEN** `GroupTagFilter` rejects the call
- **THEN** the audit record for the attempt is still emitted

### Requirement: Opt-in analytics proxy

<!-- anchor: composition.analytics-proxy --> `mount_analytics` SHALL mount a `create_proxy` of the remote analytics MCP
service, and the entrypoint SHALL invoke it only when
`ACME_MCP_ANALYTICS_URL` is set. Proxied tools join the same tag-based
access regime: admin's wildcard reaches them, other groups do not.

#### Scenario: Proxy mounts only when configured
- **GIVEN** `ACME_MCP_ANALYTICS_URL` is unset
- **WHEN** the server starts
- **THEN** no analytics tools are mounted

### Requirement: Public identity tool

<!-- anchor: composition.whoami --> The server SHALL expose a `whoami` tool tagged `public`, returning the
verified `sub` and `groups` from the caller's token, so every authenticated
caller — including those in unknown groups — can see who the server thinks
they are, and nothing more.

#### Scenario: Unknown group sees only whoami
- **GIVEN** a caller whose groups match no `GROUP_TAGS` entry
- **WHEN** they list tools
- **THEN** only `whoami` appears
