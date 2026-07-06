# Access Control Specification

## Purpose

Enforce per-group tool access in two places. The `GroupTagFilter` middleware
hides tools the caller isn't cleared for when listing, and blocks calls to
them by name, so a guessed tool name fails exactly like a nonexistent one.
Filtering only the list would leave a named tool callable; filtering the
call is what shuts the door.

## Requirements

### Requirement: Listing hides uncleared tools

<!-- anchor: access.list-filter --> `GroupTagFilter.on_list_tools` SHALL return only the tools whose tags
intersect the caller's allowed tags. An unauthenticated caller (empty tag
set) sees an empty list.

#### Scenario: Support sees only support-cleared tools
- **GIVEN** a caller in the `support` group
- **WHEN** tools are listed
- **THEN** orders/billing/support/reports tools appear and `admin`-tagged
  tools do not

#### Scenario: No token, no tools
- **GIVEN** an unauthenticated caller
- **WHEN** tools are listed
- **THEN** the list is empty

### Requirement: Calls to uncleared tools are blocked with a uniform error

<!-- anchor: access.call-block --> `GroupTagFilter.on_call_tool` SHALL resolve the requested tool and reject
the call unless the tool exists and the caller is cleared for its tags. The
rejection SHALL be a `ToolError` reading `Unknown tool: <name>` in every
failure mode — uncleared, nonexistent, or an internal lookup error — so the
response leaks neither a hidden tool's existence nor backend detail.

#### Scenario: Guessed hidden tool name fails
- **GIVEN** a `support` caller who cannot see `issue_refund`
- **WHEN** they call `issue_refund` by name
- **THEN** the call fails with `Unknown tool: issue_refund`

#### Scenario: Internal lookup errors do not leak
- **GIVEN** the tool registry raises while resolving a name
- **WHEN** the call is rejected
- **THEN** the error is the same uniform `Unknown tool` message

### Requirement: Wildcard clearance

<!-- anchor: access.cleared-for --> Clearance SHALL be computed by `cleared_for`: a caller holding `ALL_TAGS` is
cleared for every tool; otherwise clearance requires a non-empty
intersection between the tool's tags and the caller's allowed tags.

#### Scenario: Admin reaches a later-composed domain
- **GIVEN** an `admin` caller and a proxied `analytics` domain mounted after
  deployment
- **WHEN** they list or call an analytics tool
- **THEN** the wildcard clears them without any change to `GROUP_TAGS`

#### Scenario: Non-admin stays walled off
- **GIVEN** a `support` caller
- **WHEN** they attempt the same analytics tool
- **THEN** listing hides it and calling it is blocked
