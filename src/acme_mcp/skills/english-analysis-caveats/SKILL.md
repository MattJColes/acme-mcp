---
name: english-analysis-caveats
description: How to interpret acme-mcp English analysis results. Use whenever vowel, noun, verb, or word counts are returned — report exact counts but describe noun and verb matches as approximate.
tags: ["english"]
---

# Interpreting acme-mcp English analysis

The English tools are deliberately lightweight and deterministic:

- `vowel_count` counts `a`, `e`, `i`, `o`, and `u` case-insensitively. It does
  not treat `y` as a vowel.
- `word_count` counts punctuation-stripped alphanumeric tokens and distinct
  lowercase tokens.
- `noun_count` and `verb_count` use a small lexicon plus common word suffixes.
  Their `words` field shows exactly what matched, and `count` is its length.

Present vowel and word counts directly. Present noun and verb results as
**approximate matches**, include the returned words when useful, and do not
claim that the result is a full grammatical analysis. If linguistic accuracy
matters, tell the user this heuristic is not an NLP model.
