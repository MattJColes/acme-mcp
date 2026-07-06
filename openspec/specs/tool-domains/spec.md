# Tool Domains Specification

## Purpose

Deterministic, typed business tools over a data backend: read-only lookups
for orders and billing, and one privileged money-moving write (refunds) that
validates its inputs before touching the backend. Every tool is tagged with
its domain so access control can key off tags alone.

## Requirements

### Requirement: Read-only order lookup

<!-- anchor: domains.order-status --> `order_status` SHALL be an `orders`-tagged tool that looks up an order by id
and returns its status. Unknown ids SHALL return a `not_found` status rather
than raising, and the tool SHALL NOT write to the backend.

#### Scenario: Known order
- **WHEN** `order_status` is called with an existing order id
- **THEN** the order's status is returned

#### Scenario: Unknown order
- **WHEN** `order_status` is called with an unknown id
- **THEN** the result has status `not_found`

### Requirement: Read-only invoice lookup

<!-- anchor: domains.get-invoice --> `get_invoice` SHALL be a `billing`-tagged tool that looks up an invoice by
id. Unknown ids SHALL return status `not_found` with amount `0.0`, and the
tool SHALL NOT write to the backend.

#### Scenario: Unknown invoice
- **WHEN** `get_invoice` is called with an unknown id
- **THEN** the result has status `not_found` and amount `0.0`

### Requirement: Refund input guards

<!-- anchor: domains.issue-refund --> `issue_refund` SHALL be an `admin`-tagged tool that validates before it
writes: a blank or whitespace `order_id` is rejected; an `amount` that is a
bool, not a number, not finite, or not strictly positive is rejected. Each
rejection SHALL be a `ToolError` raised before the backend records
anything. On success the refund is recorded and a `refund_issued`
confirmation returned.

#### Scenario: Non-positive amount rejected
- **WHEN** `issue_refund` is called with amount `0` or `-1`
- **THEN** a `ToolError` is raised and no refund is recorded

#### Scenario: Blank order id rejected
- **WHEN** `issue_refund` is called with an empty or whitespace order id
- **THEN** a `ToolError` is raised and no refund is recorded

#### Scenario: Valid refund recorded
- **WHEN** `issue_refund` is called with a real order id and positive amount
- **THEN** the backend records it and the result has status `refund_issued`
