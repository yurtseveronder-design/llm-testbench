"""Deterministic checks. Each returns (passed, detail). No LLM-as-judge: a check is a rule you can read."""
from __future__ import annotations

import json
import re

ABSTAIN_PHRASES = ("i don't know", "i do not know", "not covered", "cannot find", "can't find", "no information")


def _ci(s: str) -> str:
    return s.lower()


def contains_all(out, values, **_):
    miss = [v for v in values if _ci(v) not in _ci(out)]
    return not miss, f"missing={miss}" if miss else "ok"


def contains_any(out, values, **_):
    return any(_ci(v) in _ci(out) for v in values), "none of the values found" if not any(_ci(v) in _ci(out) for v in values) else "ok"


def must_not_contain(out, values, **_):
    hit = [v for v in values if _ci(v) in _ci(out)]
    return not hit, f"found_forbidden={hit}" if hit else "ok"


def regex(out, pattern, **_):
    return re.search(pattern, out, re.S | re.I) is not None, f"pattern={pattern!r}"


def not_regex(out, pattern, **_):
    return re.search(pattern, out, re.S | re.I) is None, f"pattern={pattern!r}"


def max_words(out, n, **_):
    c = len(out.split())
    return c <= n, f"words={c} limit={n}"


def json_valid(out, required_keys=(), **_):
    try:
        data = json.loads(out)
    except ValueError as e:
        return False, f"invalid json: {e}"
    miss = [k for k in required_keys if not isinstance(data, dict) or k not in data]
    return not miss, f"missing_keys={miss}" if miss else "ok"


def abstains(out, phrases=ABSTAIN_PHRASES, **_):
    ok = any(p in _ci(out) for p in phrases)
    return ok, "ok" if ok else "answer does not admit it does not know"


def equals(out, value, **_):
    return out.strip() == value.strip(), "ok" if out.strip() == value.strip() else "different text"


REGISTRY = {f.__name__: f for f in (contains_all, contains_any, must_not_contain, regex, not_regex, max_words, json_valid, abstains, equals)}


def run_check(spec: dict, output: str):
    kind = spec["type"]
    if kind not in REGISTRY:
        raise ValueError(f"unknown check type {kind!r}; known: {sorted(REGISTRY)}")
    args = {k: v for k, v in spec.items() if k != "type"}
    return REGISTRY[kind](output, **args)
