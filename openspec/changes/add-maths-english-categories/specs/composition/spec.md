## MODIFIED Requirements

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
