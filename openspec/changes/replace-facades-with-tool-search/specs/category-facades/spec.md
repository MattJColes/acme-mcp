## REMOVED Requirements

### Requirement: Facade surfaces the category's particulars

<!-- anchor: facades.perform -->
**Reason**: The facade hides native tool definitions from host-provided tool search and replaces their typed interfaces with a broad `operation` and `arguments` call.

**Migration**: Call `addition`, `subtraction`, `multiplication`, `division`, `vowel_count`, `noun_count`, `verb_count`, and `word_count` directly. Tool-search capable hosts can defer these native definitions; other hosts receive the caller's permitted tools from `tools/list`.

The server SHALL expose a `perform_maths` tool (tag `maths`) and a
`perform_english` tool (tag `english`), each callable with no
arguments, returning an object with `category` (the domain tag),
`description`, `tools` (every other tool carrying that tag: name,
description, input schema) and `skills` (every companion skill carrying
that tag: name, description, and its `skill://…/SKILL.md` URI, excluding
manifests). The contents SHALL be derived under the caller's own auth
context, so a response can never name a tool or skill the caller cannot
call or read. A caller not cleared for the tag SHALL NOT see the
facade in listings nor be able to call it. The blocked call SHALL use
the existing permission error, which may name the facade.

#### Scenario: Maths facade lists its tools
- **WHEN** a cleared caller calls `perform_maths`
- **THEN** `tools` contains exactly `addition`, `subtraction`,
`multiplication` and `division`, each with its input schema
- **AND** `skills` contains `calculator-usage` with its SKILL.md URI

#### Scenario: English facade lists its tools
- **WHEN** a cleared caller calls `perform_english`
- **THEN** `tools` contains exactly `vowel_count`, `noun_count`,
`verb_count` and `word_count`
- **AND** `skills` contains `english-analysis-caveats` with its SKILL.md URI

#### Scenario: Facade excludes itself and other domains
- **WHEN** a cleared caller calls `perform_maths`
- **THEN** no tool carrying another domain's tag appears in `tools`
- **AND** the facade itself is not listed in `tools`

#### Scenario: Uncleared caller is walled off
- **GIVEN** a caller not cleared for `maths`
- **WHEN** they list tools or call `perform_maths` by name
- **THEN** the facade is absent from the listing and the call is
blocked with the existing permission error

#### Scenario: Returned skill URI is readable
- **WHEN** a cleared caller reads a SKILL.md URI returned by a facade
- **THEN** the skill content is returned
