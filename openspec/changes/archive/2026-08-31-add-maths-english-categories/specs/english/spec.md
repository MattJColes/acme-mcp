## Purpose

Lightweight text analysis — vowel counting, approximate noun/verb
detection, and word counting — as tagged tools, with the detection
quality honestly described as heuristic rather than presented as
language-model output.

## ADDED Requirements

### Requirement: Vowel count

<!-- anchor: english.vowel-count --> `vowel_count` SHALL be an `english`-tagged tool that takes a text
string and returns an integer counting occurrences of `a`, `e`, `i`,
`o`, `u` — case-insensitively and among letters only. Empty or
whitespace-only input SHALL return `0`.

#### Scenario: Mixed-case text
- **WHEN** `vowel_count` is called with `"Hello, World!"`
- **THEN** the result is `3`

#### Scenario: No letters
- **WHEN** `vowel_count` is called with `""` or `12345`
- **THEN** the result is `0`

### Requirement: Noun count

<!-- anchor: english.noun-count --> `noun_count` SHALL be an `english`-tagged tool that takes text and
returns `{count, words}` where `words` are the lowercase tokens the
server's documented heuristic (a small lexicon plus common noun
suffixes) identifies as nouns, and `count` SHALL equal the number of
words returned. The detection SHALL be presented as approximate.

#### Scenario: Content words detected
- **WHEN** `noun_count` is called with `"The dogs chased the ball"`
- **THEN** `words` includes `dogs` and `ball` and `count` equals the
number of returned words

#### Scenario: Empty input
- **WHEN** `noun_count` is called with `""`
- **THEN** the result is `{count: 0, words: []}`

### Requirement: Verb count

<!-- anchor: english.verb-count --> `verb_count` SHALL be an `english`-tagged tool that takes text and
returns `{count, words}` where `words` are the lowercase tokens the
server's documented heuristic (a small lexicon plus common verb
suffixes) identifies as verbs, and `count` SHALL equal the number of
words returned. The detection SHALL be presented as approximate.

#### Scenario: Inflected forms detected
- **WHEN** `verb_count` is called with `"running and jumping"`
- **THEN** `words` includes `running` and `jumping` and `count` equals
the number of returned words

#### Scenario: Empty input
- **WHEN** `verb_count` is called with `""`
- **THEN** the result is `{count: 0, words: []}`

### Requirement: Word count

<!-- anchor: english.word-count --> `word_count` SHALL be an `english`-tagged tool that takes text and
returns `{words, unique_words}`: `words` counts whitespace-separated
alphanumeric tokens with punctuation stripped, and `unique_words`
counts distinct lowercase tokens. Empty input SHALL return zeros.

#### Scenario: Repeated words
- **WHEN** `word_count` is called with `"the cat and the hat"`
- **THEN** the result is `{words: 5, unique_words: 4}`

#### Scenario: Empty input
- **WHEN** `word_count` is called with `""`
- **THEN** the result is `{words: 0, unique_words: 0}`
