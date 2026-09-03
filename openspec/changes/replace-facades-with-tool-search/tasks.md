## 1. Native Tool Discovery

- [x] 1.1 Rewrite the facade discovery tests to assert that permitted maths and English tools appear directly with their domain tags and typed schemas; verify the focused tests fail before implementation.
- [x] 1.2 Remove facade registration and member-hiding middleware from server assembly, then verify permitted native tools can be listed and called directly through the in-memory client.
- [x] 1.3 Remove obsolete facade implementation and tests while retaining tag-based authorization for tools and skills; verify callers cannot list or call tools outside their tag grants.

## 2. Engineering Guide

- [x] 2.1 Rewrite `docs/tool-grouping.md` with a summary, direct native-tool example, and a diagram showing `identity groups -> domain tags -> permitted tools -> host tool search -> typed call`; verify the prose does not claim providers search FastMCP tags.
- [x] 2.2 Add concise Claude and OpenAI deferred-loading examples linked to their official documentation, plus the facade fallback trade-off for hosts without tool search; verify each example matches the current provider syntax.
- [x] 2.3 Explain how the same tags group companion skills for access while skill resource discovery remains separate from tool search; verify the example tags match the registered tools and skill frontmatter.

## 3. Specifications and Verification

- [x] 3.1 Remove the obsolete category-facade anchor and re-run anchor resolution for every changed implementation file; verify each remaining anchor resolves exactly once.
- [x] 3.2 Run the focused discovery, maths, English, access, and composition tests, then run `.venv/bin/python -m pytest -q`; verify the complete suite passes without network access.
- [x] 3.3 Review the final diff for stale facade names and provider-specific runtime dependencies; verify only migration documentation and archived proposal history retain facade references.
