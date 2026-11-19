from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .checks import run_check


def load_cases(path: str | Path) -> list[dict]:
    cases, seen = [], set()
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        c = json.loads(line)
        for k in ("id", "input", "checks"):
            if k not in c:
                raise ValueError(f"{path}:{n}: case is missing {k!r}")
        if c["id"] in seen:
            raise ValueError(f"{path}:{n}: duplicate id {c['id']!r}")
        seen.add(c["id"])
        cases.append(c)
    return cases


def run_case(case: dict, target: Callable[[str], str], repeats: int = 1) -> dict:
    """status: pass | fail | flaky (mixed across repeats) | error (target failed). Errors are never passes."""
    runs = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        try:
            out = target(case["input"])
        except Exception as e:  # noqa: BLE001  a broken target must be reported, whatever it raised
            runs.append({"ok": None, "error": f"{type(e).__name__}: {e}", "seconds": time.perf_counter() - t0})
            continue
        details = []
        ok = True
        for spec in case["checks"]:
            passed, detail = run_check(spec, out)
            ok &= passed
            details.append({"check": spec["type"], "pass": passed, "detail": detail})
        runs.append({"ok": ok, "output": out, "checks": details, "seconds": time.perf_counter() - t0})
    if any(r["ok"] is None for r in runs):
        status = "error"
    elif all(r["ok"] for r in runs):
        status = "pass"
    elif not any(r["ok"] for r in runs):
        status = "fail"
    else:
        status = "flaky"
    return {"id": case["id"], "tags": case.get("tags", []), "status": status, "runs": runs}


def run_all(cases: list[dict], target: Callable[[str], str], repeats: int = 1) -> dict:
    results = [run_case(c, target, repeats) for c in cases]
    counts: dict[str, int] = {}
    by_tag: dict[str, dict[str, int]] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        for t in r["tags"] or ["untagged"]:
            d = by_tag.setdefault(t, {"pass": 0, "total": 0})
            d["total"] += 1
            d["pass"] += r["status"] == "pass"
    secs = sorted(x["seconds"] for r in results for x in r["runs"])
    return {"total": len(results), "counts": counts, "passed": counts.get("pass", 0), "repeats": repeats, "by_tag": by_tag,
            "latency_p50_s": round(secs[len(secs) // 2], 4) if secs else None, "results": results}


def compare(current: dict, baseline: dict) -> list[str]:
    """Regressions: a case that passed in the baseline and does not pass now (or is missing)."""
    base = {r["id"]: r["status"] for r in baseline["results"]}
    now = {r["id"]: r["status"] for r in current["results"]}
    out = [f"{i}: was pass, now {now.get(i, 'missing')}" for i, s in base.items() if s == "pass" and now.get(i) != "pass"]
    return out
