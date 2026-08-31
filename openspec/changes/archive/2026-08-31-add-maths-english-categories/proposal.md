## Why

The demo server only shows business domains and one companion skill. Clients
have no way to discover that the server can also do general-purpose work
(maths, text analysis), and with no per-category entry point a client has to
guess which of a growing tool list belongs to which capability. Two new
functional domains — `maths` and `english` — plus a facade tool per domain
give clients a self-describing top level: `perform_maths` and
`perform_english` are visible in `tools/list`, and calling one returns the
particulars (sub-tools with input schemas, companion skill URIs).

## What Changes

- New `maths` domain sub-server with four deterministic tools: `addition`,
  `subtraction`, `multiplication`, `division` (division by zero is a
  `ToolError`).
- New `english` domain sub-server with four tools: `vowel_count` (returns an
  int), `noun_count` and `verb_count` (return `{count, words}`), and
  `word_count` (returns `{words, unique_words}`). Noun/verb detection is a
  deliberate lexicon + suffix heuristic (no NLP dependencies), documented as
  such in a companion skill.
- New facade tools `perform_maths` and `perform_english`, each tagged with its
  domain tag. Called with no arguments, a facade returns the category's
  description, its sub-tools with name/description/input schema, and its
  companion skill URIs. Facade contents are derived live from
  `list_tools()`/`list_resources()` under the caller's own auth context, so
  the facade can never advertise a tool or skill the caller cannot call.
- Skill publishing moves from a single `SkillProvider` to
  `SkillsDirectoryProvider` over `src/acme_mcp/skills/`; two new companion
  skills land: `calculator-usage` (tag `maths`) and
  `english-analysis-caveats` (tag `english`).
- `GROUP_TAGS`: `support` and `finance` are cleared for `maths` and `english`;
  `admin` covers them via the wildcard. Existing group grants unchanged.
- Business domains (orders, billing, admin, support, reports) and their tools
  are untouched.

## Capabilities

### New Capabilities

- `maths`: arithmetic over int/float with per-operation tools and a guarded
  division.
- `english`: text analysis (vowel count, noun/verb detection, word count)
  using a documented heuristic, with result shapes.
- `category-facades`: per-domain facade tools that surface a category's
  sub-tools and companion skills to a caller, derived live and scoped by the
  existing tag-based access regime.

### Modified Capabilities

- `composition`: `build_server` mounts two additional domain servers
  (`maths`, `english`) and publishes skills via a directory provider instead
  of a single-skill provider.
- `auth`: `support` and `finance` gain clearance for the new `maths` and
  `english` tags; all existing grants and admin's wildcard remain unchanged.

## Impact

- Code: new `src/acme_mcp/domains/maths.py`, `src/acme_mcp/domains/english.py`;
  modified `src/acme_mcp/server.py` (mounts, provider, facade factory),
  `src/acme_mcp/auth.py` (`GROUP_TAGS`); new skill dirs
  `src/acme_mcp/skills/calculator-usage/`,
  `src/acme_mcp/skills/english-analysis-caveats/`.
- Wire surface: +10 tools (`addition`, `subtraction`, `multiplication`,
  `division`, `vowel_count`, `noun_count`, `verb_count`, `word_count`,
  `perform_maths`, `perform_english`) and 4 new skill resources (2 skills ×
  SKILL.md + _manifest). All group-filtered like existing components.
- Tests: new `tests/test_maths.py`, `tests/test_english.py`,
  `tests/test_facades.py`; extended `tests/test_skills.py`.
- Dependencies: none (stdlib only — no NLP or math libraries).
- Spec anchors: new anchor ymls for `maths`, `english`, `category-facades`;
  the existing `composition.build-server` anchor re-matches unchanged code
  while its section text changes (drift gate should see a deliberate update,
  not a dangling rule).
