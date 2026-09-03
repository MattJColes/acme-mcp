## MODIFIED Requirements

### Requirement: Server assembly and middleware order

<!-- anchor: composition.build-server --> `build_server` SHALL construct the `acme` FastMCP server with authentication, mount the seven domain servers (orders, billing, admin, support, reports, maths, english) un-namespaced, publish companion skills from the skills directory, and return every native tool permitted by the caller's domain-tag grants. Audit middleware SHALL wrap group-based access enforcement so blocked calls are recorded.

#### Scenario: Mounted domains expose their tools
- **GIVEN** an `admin` caller on a built server
- **WHEN** tools are listed
- **THEN** the full native surface appears, including `export_report`, `draft_refund_email`, `addition`, and `vowel_count`
- **AND** `perform_maths` and `perform_english` do not appear

#### Scenario: Tag grants filter native discovery
- **GIVEN** a `finance` caller on a built server
- **WHEN** tools are listed
- **THEN** native tools tagged `maths` and `english` appear
- **AND** tools outside the caller's tag grants do not appear

#### Scenario: Skills publish from the directory
- **GIVEN** a built server with skills under the skills directory
- **WHEN** an `admin` caller lists resources
- **THEN** each skill's `SKILL.md` and `_manifest` resources appear

#### Scenario: Blocked call still audited
- **GIVEN** a caller invoking a tool they are not cleared for
- **WHEN** group-based access enforcement rejects the call
- **THEN** the audit record for the attempt is still emitted
