## Purpose

Deterministic arithmetic over int and float values: one tagged tool per
operation, with division guarded against zero, so callers can compute
without a calculator round-trip and the server never evaluates arbitrary
expressions.

## ADDED Requirements

### Requirement: Addition

<!-- anchor: maths.addition --> `addition` SHALL be a `maths`-tagged tool that takes two numeric
arguments (int or float) and returns their sum. It SHALL NOT accept or
evaluate arbitrary expressions.

#### Scenario: Integer and float operands
- **WHEN** `addition` is called with `2` and `3`
- **THEN** the result is `5`
- **AND** called with `0.5` and `1.25` the result is `1.75`

### Requirement: Subtraction

<!-- anchor: maths.subtraction --> `subtraction` SHALL be a `maths`-tagged tool that takes two numeric
arguments (int or float) and returns their difference. Negative
results SHALL be returned as-is, not rejected.

#### Scenario: Negative difference
- **WHEN** `subtraction` is called with `3` and `10`
- **THEN** the result is `-7`

### Requirement: Multiplication

<!-- anchor: maths.multiplication --> `multiplication` SHALL be a `maths`-tagged tool that takes two
numeric arguments (int or float) and returns their product.

#### Scenario: Integer and float operands
- **WHEN** `multiplication` is called with `4` and `2.5`
- **THEN** the result is `10.0`

### Requirement: Division guards zero

<!-- anchor: maths.division --> `division` SHALL be a `maths`-tagged tool that takes two numeric
arguments (int or float) and returns their quotient as a float. A zero
divisor SHALL be rejected with a `ToolError` before any result, and the
error SHALL name the cause (division by zero) without leaking anything
else.

#### Scenario: Non-zero divisor
- **WHEN** `division` is called with `7` and `2`
- **THEN** the result is `3.5`

#### Scenario: Zero divisor rejected
- **WHEN** `division` is called with any numerator and divisor `0`
- **THEN** a `ToolError` is raised and no result is returned
