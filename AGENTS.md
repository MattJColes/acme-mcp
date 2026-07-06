# Agent guide for acme-mcp

Secure FastMCP 3 example server. Python >=3.10, src layout
(`src/acme_mcp`), TDD — run `python -m pytest -q` before you call anything
done; tests use FastMCP's in-memory `Client`, fake auth via
`tests/conftest.py`, moto for S3, and an injected fake agent. No real AWS,
IdP, or network in tests.

## Living specs and anchors

Durable behavioral specs live in `openspec/specs/<capability>/spec.md`
(auth, access-control, audit, tool-domains, support-agent, file-delivery,
composition). They are the standing description of how the system works —
read them as context, and keep them honest.

Specs are bound to code **structurally, not by path**. Each
`### Requirement:` section carries an invisible id
(`<!-- anchor: <id> -->`), and `openspec/specs/anchors/<capability>.yml`
maps that id to an ast-grep rule that locates the code the section
describes. The rule survives file moves and refactors; it breaks on a
rename, which is a signal, not noise.

### Before a change

Resolve the anchors for the files you expect to touch and read only the
matching spec sections — don't load whole spec documents into context:

```bash
python scripts/spec_drift_gate.py --resolve src/acme_mcp/access.py ...
```

### After a change

1. Re-run `--resolve` over the files you actually touched.
2. If behavior described by a matching section changed, draft the spec
   update **as a diff for human review** — never commit edits to
   `openspec/specs/` yourself. Most tasks need no spec change; proposing
   nothing is the correct outcome, not a failure.
3. Run the hygiene lint and fix what it reports **in the same PR**:

```bash
python scripts/spec_drift_gate.py --check-anchors
```

### Maintenance rules

- **Diff-only proposals.** You output a spec patch; a human commits it.
- **Size budget.** Requirement sections have a soft cap of ~40 lines. A
  patch that would blow the cap must propose a split, not append.
- **Anchor hygiene.** A rule resolves to exactly one place. Zero matches is
  a dangling anchor; several is a rule too loose (tighten with `inside` or
  an `all` body constraint). Both are drift — fix them in the PR that
  caused them.
- Write anchor rules by node kind + name (see the sidecars for the house
  style); avoid bare `pattern:` for Python defs — it has silently missed
  async functions.

### The drift gate (CI)

`.github/workflows/spec-drift.yml` runs `scripts/spec_drift_gate.py --gate`
on every PR. It warns — never fails — when anchored code changed while its
spec section sat still (DRIFT), or when a rule that used to resolve now
matches nothing (DANGLING, usually a rename). Treat a warning as a prompt
to either patch the section or re-point the rule.

## Change proposals (OpenSpec)

Large features go through OpenSpec change proposals (`/opsx:propose` in
Claude Code; artifacts land under `openspec/changes/`). Proposals are
disposable: they get archived on merge, and durable knowledge folds back
into the living specs above. Project context for proposal authoring is in
`openspec/config.yaml`.
