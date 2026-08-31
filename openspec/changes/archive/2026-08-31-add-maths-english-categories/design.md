## Context

The server is assembled in `build_server` (`src/acme_mcp/server.py`):
domain sub-servers are mounted un-namespaced, one skill is published via a
single `SkillProvider`, and the `AuthMiddleware` (backed by
`group_access`/`tags_for_groups`) filters both listings and calls by the
caller's tag clearance. See proposal.md for motivation. Constraints:
Python >=3.10, fastmcp>=3.4,<4, TDD with the in-memory `Client`, no real
AWS/IdP/network in tests, no new runtime dependencies.

Verified against the installed fastmcp 3.4: `FastMCP.list_tools()` /
`list_resources()` (async) run the full middleware chain — including the
auth filter — against the caller token present in the request context, and
`Tool` objects expose `name`, `description`, `tags`, `parameters`.
`AuditLog` implements only `on_call_tool`, so nested list calls are not
double-audited.

## Goals / Non-Goals

**Goals:**

- A self-describing top level: `perform_maths` / `perform_english` in
  `tools/list`, each returning the particulars of its category.
- Facade responses that can never over-advertise (no tool or skill the
  caller cannot call or read).
- Deterministic, dependency-free math and text tools with honest error and
  result shapes.

**Non-Goals:**

- No NLP-grade POS accuracy (heuristic, documented as such).
- No tool hierarchy on the wire — sub-tools remain individually listed and
  callable (MCP has no such mechanism; the facade is a door, not a gate).
- No facades for the business domains (orders, billing, admin, support,
  reports) — they keep their plain tools.
- No natural-language routing through the facades (no `task` parameter).
- No expression evaluation for maths (per-operation tools only).

## Decisions

1. **Per-operation maths tools over `calculate(expression)`.**
   `addition`/`subtraction`/`multiplication`/`division` are one-liners,
   trivially testable, and leave no expression-parsing surface to spec.
   Alternative considered: an AST-safe expression evaluator (rejected —
   extra attack surface and spec surface the demo does not need).

2. **Heuristic detection for `english`, stdlib only.** A small lexicon plus
   suffix rules (`-tion/-ment/-ness/-ity` → noun; `-ize/-ise/-ify/-ate/-ed/
   -ing` → verb), lowercase tokens, stopwords excluded. Deterministic and
   offline. Alternatives: `spacy` (≈100 MB model, download step, version
   drift) and `nltk` (corpus downloads) — both rejected on dependency and
   test-isolation grounds. The ceiling and upgrade path are noted in code
   and in the companion skill.

3. **Facades derive contents live from `list_tools()` /
   `list_resources()` under the caller's own auth context.** The facade
   keeps no registry of its own, so it cannot drift from the wire surface,
   and per-group scoping is inherited rather than reimplemented.
   Alternatives: a static catalog built at assembly (drift risk plus a
   second copy of the filtering logic), or hard-coded per-facade lists
   (duplication). Cost accepted: two middleware runs per facade call —
   negligible at demo scale.

4. **One facade factory, two instances, tagged with the domain tag.**
   `perform_maths`/`perform_english` are produced by a small factory
   (name, tag, blurb) rather than two hand-written tools; tagging them with
   the domain tag means the existing `AuthMiddleware` hides uncleared
   facades from listings and blocks direct calls with its permission error.
   That error may name the facade, matching the server's existing contract.

5. **Skill publishing via `SkillsDirectoryProvider`.** The built-in
   multi-skill provider replaces the single `SkillProvider`; each
   subdirectory with a `SKILL.md` becomes a skill. No custom provider code.
   Frontmatter `tags` remain the access key, so category tags and clearance
   stay one source of truth.

6. **Result shapes.** `vowel_count` → int; `noun_count`/`verb_count` →
   `{count, words}` (the matched words prove what the heuristic did);
   `word_count` → `{words, unique_words}`. Division returns float
   (`7 / 2 == 3.5`) and says so in its description.

## Risks / Trade-offs

- [Heuristic POS misclassifies words] → documented as approximate in the
  requirement and in the `english-analysis-caveats` skill; counts are
  demo-grade by design.
- [Nested `list_tools()` re-enters middleware] → verified `AuditLog` wraps
  only tool calls (no duplicate audit entries) and the auth list filter is
  idempotent; a facade test asserts the wire-level shape so regression is
  loud.
- [fastmcp API drift (`Tool.tags`, middleware semantics of `list_tools`)] →
  pinned by `fastmcp>=3.4,<4`; facade tests assert externally visible
  behavior, so a semantic change fails tests rather than silently
  over-advertising.
- [A facade could list a skill whose resources are hidden for the caller] →
  the skill list comes from `list_resources()` under the caller's context,
  so hidden skills are absent from the response by construction.

## Migration Plan

New surface only; nothing existing changes behavior (existing tools, tags,
and the `handle-downloads` skill are untouched). Rollback is a revert. The
`composition.build-server` anchor re-matches unchanged code; only its
section text changes (carried by the delta), so the drift gate sees a
deliberate spec update, not a dangling rule.

## Open Questions

None — group clearance, result shapes, naming, and scope were settled in
planning.
