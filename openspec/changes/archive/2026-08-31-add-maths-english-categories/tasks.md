## 1. Maths domain (TDD)

- [x] 1.1 Write `tests/test_maths.py` covering the `maths` spec scenarios (addition `2+3=5` and `0.5+1.25=1.75`; subtraction `3-10=-7`; multiplication `4*2.5=10.0`; division `7/2=3.5`; division by zero raises `ToolError`) driving the assembled server with the in-memory `Client` as a cleared caller, and verify the tests fail while the domain does not exist
- [x] 1.2 Implement `src/acme_mcp/domains/maths.py` (`maths_server` sub-server; `addition`, `subtraction`, `multiplication`, `division` tools tagged `maths`, int/float args, zero-divisor guard) and verify `python -m pytest tests/test_maths.py -q` passes

## 2. English domain (TDD)

- [x] 2.1 Write `tests/test_english.py` covering the `english` spec scenarios (`vowel_count("Hello, World!")=3`, no-letters and empty inputs `0`; `noun_count("The dogs chased the ball")` includes `dogs` and `ball` with `count == len(words)`, empty `{count: 0, words: []}`; `verb_count("running and jumping")` includes both inflected forms, empty zeros; `word_count("the cat and the hat")={words: 5, unique_words: 4}`, empty zeros), and verify the tests fail while the domain does not exist
- [x] 2.2 Implement `src/acme_mcp/domains/english.py` (`english_server` sub-server; `vowel_count`, `noun_count`, `verb_count`, `word_count` tagged `english`; shared `_pos_scan` lexicon + suffix heuristic with a `ponytail:` comment naming the accuracy ceiling and spaCy upgrade path) and verify `python -m pytest tests/test_english.py -q` passes

## 3. Wiring and facades (TDD)

- [x] 3.1 In `src/acme_mcp/server.py` mount `maths_server` and `english_server` un-namespaced and replace the single `SkillProvider` with `SkillsDirectoryProvider(roots=SKILLS_DIR)`; in `src/acme_mcp/auth.py` add `maths` and `english` to the `support` and `finance` entries of `GROUP_TAGS`, and verify `python -m pytest -q` passes with all pre-existing tests green (including the unchanged `handle-downloads` skill URIs)
- [x] 3.2 Write `tests/test_facades.py` for the tool side of the `category-facades` spec: as `admin`, `perform_maths` returns exactly `addition`/`subtraction`/`multiplication`/`division` with input schemas and does not list itself or any other domain's tool; `perform_english` returns exactly its four tools; as `engineering` (uncleared) both facades are absent from `tools/list` and a direct call is blocked with the existing permission error; a tool named in a facade response is callable (`addition(1, 2) == 3`), and verify the tests fail while the facades do not exist
- [x] 3.3 Add the facade factory in `src/acme_mcp/server.py` producing `perform_maths` (tag `maths`) and `perform_english` (tag `english`), each no-arg and deriving contents live from `mcp.list_tools()`/`list_resources()` under the caller's auth context, and verify `python -m pytest tests/test_facades.py -q` passes

## 4. Companion skills

- [x] 4.1 Add `src/acme_mcp/skills/calculator-usage/SKILL.md` (`tags: ["maths"]`) and `src/acme_mcp/skills/english-analysis-caveats/SKILL.md` (`tags: ["english"]`) in the existing "direction for agents" tone, extend `tests/test_facades.py` to assert each facade's `skills` contains its companion with a `skill://…/SKILL.md` URI that `read_resource` returns, and verify `python -m pytest tests/test_facades.py -q` passes
- [x] 4.2 Extend `tests/test_skills.py` so both new skills are discoverable and readable for `support`, `finance`, and `admin`, and hidden from `engineering` (listing and direct read), and verify `python -m pytest tests/test_skills.py -q` passes

## 5. Anchors and spec hygiene

- [x] 5.1 Validate the change's draft `anchors/maths.yml`, `anchors/english.yml`, and `anchors/category-facades.yml` each resolve exactly once against the implementation; keep them in the change until sync/archive installs them alongside their new main specs, and verify `python scripts/spec_drift_gate.py --check-anchors` remains clean for currently installed anchors
- [x] 5.2 Run `python scripts/spec_drift_gate.py --resolve` over the changed `src/acme_mcp/` files and verify `composition.build-server` still resolves to `build_server` and `auth.group-tags` resolves to `GROUP_TAGS`; carry both changed sections in their corresponding deltas

## 6. Full verification

- [x] 6.1 Run `python -m pytest -q` and verify the complete suite is green
- [x] 6.2 Run `openspec validate add-maths-english-categories --strict` and verify it reports no errors; hand the whole change (code + spec deltas + anchors) to the human for review — spec prose is diff-only per `AGENTS.md`
