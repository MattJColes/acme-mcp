"""English domain: lightweight, deterministic text analysis."""

from __future__ import annotations

import re

from fastmcp import FastMCP

english_server = FastMCP("english")

_NOUNS = {
    "account",
    "ball",
    "cat",
    "customer",
    "dog",
    "dogs",
    "file",
    "invoice",
    "order",
    "report",
    "user",
}
_VERBS = {
    "be",
    "calculate",
    "chase",
    "chased",
    "count",
    "detect",
    "have",
    "jump",
    "make",
    "read",
    "run",
    "send",
    "write",
}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
_NOUN_SUFFIXES = ("tion", "sion", "ment", "ness", "ity", "ship", "age")
_VERB_SUFFIXES = ("ize", "ise", "ify", "ate", "ed", "ing")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*", text.lower())


# ponytail: lexicon+suffix POS is demo-grade; replace _pos_scan with spaCy
# when accuracy matters.
def _pos_scan(text: str) -> tuple[list[str], list[str]]:
    words = [word for word in _tokens(text) if word not in _STOPWORDS]
    nouns = [
        word for word in words if word in _NOUNS or word.endswith(_NOUN_SUFFIXES)
    ]
    verbs = [
        word for word in words if word in _VERBS or word.endswith(_VERB_SUFFIXES)
    ]
    return nouns, verbs


@english_server.tool(tags={"english"})
def vowel_count(text: str) -> int:
    """Count a, e, i, o and u in text, case-insensitively."""
    return sum(char in "aeiou" for char in text.lower())


@english_server.tool(tags={"english"})
def noun_count(text: str) -> dict:
    """Return approximate noun matches and their count."""
    nouns, _ = _pos_scan(text)
    return {"count": len(nouns), "words": nouns}


@english_server.tool(tags={"english"})
def verb_count(text: str) -> dict:
    """Return approximate verb matches and their count."""
    _, verbs = _pos_scan(text)
    return {"count": len(verbs), "words": verbs}


@english_server.tool(tags={"english"})
def word_count(text: str) -> dict:
    """Count words and distinct lowercase words in text."""
    words = _tokens(text)
    return {"words": len(words), "unique_words": len(set(words))}
