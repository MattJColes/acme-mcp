#!/usr/bin/env python3
"""Spec anchors: resolve, lint, and drift-gate.

Specs in openspec/specs/<capability>/spec.md carry section ids as invisible
HTML comments (``<!-- anchor: id -->``). Sidecar files in
openspec/specs/anchors/<capability>.yml map each id to ast-grep rules that
locate the code the section describes structurally, so the link survives
moves and refactors and breaks only on renames.

Modes:
  --resolve FILE...   print the anchor ids (and their spec sections) whose
                      rules match the given files — run this before a change
                      to pull only the relevant spec context
  --check-anchors     anchor hygiene lint: every rule must resolve to exactly
                      one place, and ids must exist on both sides (spec
                      comment and sidecar entry); exits non-zero on problems
  --gate --base SHA   the PR drift gate: warn (never fail) when anchored code
                      changed but its spec section didn't (DRIFT), or when a
                      rule that matched at the merge-base no longer matches
                      (DANGLING, usually a rename)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ANCHOR_DIR = REPO_ROOT / "openspec" / "specs" / "anchors"
SPEC_DIR = REPO_ROOT / "openspec" / "specs"
ANCHOR_COMMENT = re.compile(r"<!--\s*anchor:\s*(?P<id>[A-Za-z0-9._-]+)\s*-->")


@dataclass
class Anchor:
    id: str
    capability: str
    rule: dict
    files: list[str]
    sidecar: Path

    @property
    def spec_file(self) -> Path:
        return SPEC_DIR / self.capability / "spec.md"


@dataclass
class Match:
    file: str  # repo-relative path
    start: int  # 1-based inclusive
    end: int  # 1-based inclusive


@dataclass
class Warning_:
    kind: str  # DRIFT or DANGLING
    anchor: Anchor
    detail: str
    file: str = ""
    line: int = 0


def load_anchors() -> list[Anchor]:
    anchors: list[Anchor] = []
    for sidecar in sorted(ANCHOR_DIR.glob("*.yml")):
        data = yaml.safe_load(sidecar.read_text()) or {}
        for anchor_id, entry in data.items():
            anchors.append(
                Anchor(
                    id=anchor_id,
                    capability=sidecar.stem,
                    rule=entry["rule"],
                    files=entry.get("files", ["**/*.py"]),
                    sidecar=sidecar,
                )
            )
    return anchors


def scan(anchors: list[Anchor], root: Path) -> dict[str, list[Match]]:
    """Run every anchor rule over *root*; return matches keyed by anchor id."""
    docs = [
        {
            "id": a.id,
            "language": "python",
            "severity": "hint",
            "rule": a.rule,
            "files": a.files,
        }
        for a in anchors
    ]
    inline = "\n---\n".join(yaml.safe_dump(d, sort_keys=False) for d in docs)
    proc = subprocess.run(
        ["ast-grep", "scan", "--inline-rules", inline, "--json=compact", "."],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.exit(f"ast-grep scan failed in {root}:\n{proc.stderr}")
    matches: dict[str, list[Match]] = {a.id: [] for a in anchors}
    for m in json.loads(proc.stdout):
        rng = m["range"]
        matches[m["ruleId"]].append(
            Match(
                file=m["file"].removeprefix("./"),
                start=rng["start"]["line"] + 1,  # ast-grep lines are 0-based
                end=rng["end"]["line"] + 1,
            )
        )
    return matches


def changed_lines(base: str) -> dict[str, set[int]]:
    """New-side changed line numbers per file between *base* and HEAD."""
    out = subprocess.run(
        ["git", "diff", "--unified=0", base, "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changed: dict[str, set[int]] = {}
    current = None
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@") and current:
            hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            start = int(hunk.group(1))
            count = int(hunk.group(2)) if hunk.group(2) is not None else 1
            # a pure deletion (count 0) still touches the line it removed at
            lines = range(start, start + max(count, 1))
            changed.setdefault(current, set()).update(lines)
    return changed


def section_lines(spec_file: Path, anchor_id: str) -> set[int]:
    """1-based lines of the requirement section carrying *anchor_id*.

    The section runs from its ``### `` heading to the line before the next
    heading of level three or shallower.
    """
    if not spec_file.exists():
        return set()
    lines = spec_file.read_text().splitlines()
    hit = next(
        (
            i
            for i, text in enumerate(lines)
            if (m := ANCHOR_COMMENT.search(text)) and m.group("id") == anchor_id
        ),
        None,
    )
    if hit is None:
        return set()
    start = next(
        (i for i in range(hit, -1, -1) if lines[i].startswith("### ")), hit
    )
    end = next(
        (
            i - 1
            for i in range(hit + 1, len(lines))
            if re.match(r"#{1,3} ", lines[i])
        ),
        len(lines) - 1,
    )
    return set(range(start + 1, end + 2))


def sidecar_lines(sidecar: Path, anchor_id: str) -> set[int]:
    """1-based lines of *anchor_id*'s entry in its sidecar yaml."""
    lines = sidecar.read_text().splitlines()
    start = next(
        (i for i, t in enumerate(lines) if t.startswith(f"{anchor_id}:")), None
    )
    if start is None:
        return set()
    end = next(
        (
            i - 1
            for i in range(start + 1, len(lines))
            if lines[i] and not lines[i][0].isspace() and not lines[i].startswith("#")
        ),
        len(lines) - 1,
    )
    return set(range(start + 1, end + 2))


def spec_anchor_ids() -> dict[str, str]:
    """anchor id -> capability, harvested from the spec markdown comments."""
    ids: dict[str, str] = {}
    for spec in sorted(SPEC_DIR.glob("*/spec.md")):
        for m in ANCHOR_COMMENT.finditer(spec.read_text()):
            ids[m.group("id")] = spec.parent.name
    return ids


def rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT))


# ---------------------------------------------------------------- resolve --


def cmd_resolve(paths: list[str]) -> int:
    anchors = load_anchors()
    matches = scan(anchors, REPO_ROOT)
    wanted = {os.path.normpath(p) for p in paths}
    hits = [
        (a, m)
        for a in anchors
        for m in matches[a.id]
        if os.path.normpath(m.file) in wanted
    ]
    if not hits:
        print("no anchors resolve to the given files")
        return 0
    for a, m in hits:
        print(f"{a.id}: {m.file}:{m.start}-{m.end} -> {rel(a.spec_file)}")
    return 0


# ---------------------------------------------------------- check-anchors --


def cmd_check_anchors() -> int:
    anchors = load_anchors()
    matches = scan(anchors, REPO_ROOT)
    in_specs = spec_anchor_ids()
    problems: list[str] = []
    for a in anchors:
        found = matches[a.id]
        if not found:
            problems.append(f"DANGLING {a.id}: rule matches nothing ({rel(a.sidecar)})")
        elif len(found) > 1:
            where = ", ".join(f"{m.file}:{m.start}" for m in found)
            problems.append(
                f"LOOSE {a.id}: rule matches {len(found)} places ({where}) — "
                "tighten it (e.g. add `inside`) until it points at one thing"
            )
        if a.id not in in_specs:
            problems.append(
                f"ORPHAN-RULE {a.id}: sidecar entry has no <!-- anchor --> "
                f"comment in {rel(a.spec_file)}"
            )
    rule_ids = {a.id for a in anchors}
    for anchor_id, capability in in_specs.items():
        if anchor_id not in rule_ids:
            problems.append(
                f"ORPHAN-ID {anchor_id}: spec comment in "
                f"openspec/specs/{capability}/spec.md has no sidecar rule"
            )
    if problems:
        print(f"{len(problems)} anchor problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"ok: {len(anchors)} anchors, each resolving to exactly one place")
    return 0


# ------------------------------------------------------------------- gate --


def scan_at(anchors: list[Anchor], commit: str) -> dict[str, list[Match]]:
    with tempfile.TemporaryDirectory(prefix="spec-drift-base-") as tmp:
        worktree = Path(tmp) / "base"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), commit],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        try:
            return scan(anchors, worktree)
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=REPO_ROOT,
                capture_output=True,
            )


def cmd_gate(base: str, summary_file: str | None) -> int:
    anchors = load_anchors()
    head = scan(anchors, REPO_ROOT)
    base_matches = scan_at(anchors, base)
    changed = changed_lines(base)
    warnings: list[Warning_] = []

    for a in anchors:
        if base_matches[a.id] and not head[a.id]:
            old = base_matches[a.id][0]
            warnings.append(
                Warning_(
                    kind="DANGLING",
                    anchor=a,
                    detail=(
                        f"rule matched {old.file}:{old.start} at the merge-base "
                        "but matches nothing now (rename?) — re-point the rule "
                        f"in {rel(a.sidecar)} and review its spec section"
                    ),
                    file=rel(a.sidecar),
                    line=min(sidecar_lines(a.sidecar, a.id) or {1}),
                )
            )
            continue
        touched = [
            m
            for m in head[a.id]
            if changed.get(m.file, set()) & set(range(m.start, m.end + 1))
        ]
        if not touched:
            continue
        spec_touched = section_lines(a.spec_file, a.id) & changed.get(
            rel(a.spec_file), set()
        )
        rule_touched = sidecar_lines(a.sidecar, a.id) & changed.get(
            rel(a.sidecar), set()
        )
        if spec_touched or rule_touched:
            continue  # handled: code and spec moved together
        m = touched[0]
        warnings.append(
            Warning_(
                kind="DRIFT",
                anchor=a,
                detail=(
                    f"anchored code changed ({m.file}:{m.start}-{m.end}) but "
                    f"its spec section in {rel(a.spec_file)} did not — update "
                    "the section or confirm it still holds"
                ),
                file=m.file,
                line=m.start,
            )
        )

    for w in warnings:
        print(
            f"::warning file={w.file},line={w.line},"
            f"title=spec-drift {w.kind}::{w.anchor.id}: {w.detail}"
        )
    if warnings:
        md = ["### Spec drift warnings", ""]
        md += [f"- **{w.kind}** `{w.anchor.id}` — {w.detail}" for w in warnings]
        md += [
            "",
            "_Non-blocking. Anchors live in `openspec/specs/anchors/`; see "
            "`AGENTS.md` for the convention._",
        ]
        body = "\n".join(md) + "\n"
        if summary_file:
            Path(summary_file).write_text(body)
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            with open(step_summary, "a") as fh:
                fh.write(body)
    else:
        print(f"quiet: {len(anchors)} anchors, no drift against {base[:12]}")
    return 0  # the gate warns; it never fails the build


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--resolve", nargs="+", metavar="FILE")
    mode.add_argument("--check-anchors", action="store_true")
    mode.add_argument("--gate", action="store_true")
    ap.add_argument("--base", help="merge-base commit for --gate")
    ap.add_argument("--summary-file", help="write gate warnings here as markdown")
    args = ap.parse_args()
    if args.resolve:
        return cmd_resolve(args.resolve)
    if args.check_anchors:
        return cmd_check_anchors()
    if not args.base:
        ap.error("--gate requires --base")
    return cmd_gate(args.base, args.summary_file)


if __name__ == "__main__":
    sys.exit(main())
