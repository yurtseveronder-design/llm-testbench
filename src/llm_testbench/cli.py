"""llm-testbench run cases.jsonl --target python:examples.toy:answer [--repeats 3] [--out r.json] [--baseline b.json]
Exit codes: 0 all good, 1 failures/regressions (see flags), 2 usage or setup error."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import compare, load_cases, run_all
from .targets import command_target, http_target, python_target


def build_target(spec: str, args):
    kind, _, rest = spec.partition(":")
    if kind == "python":
        return python_target(rest)
    if kind == "command":
        return command_target(rest)
    if kind == "http":
        if not args.model:
            raise ValueError("--model is required for an http target")
        return http_target(rest if rest.startswith("http") else "https:" + rest, args.model, args.api_key_env, args.system)
    raise ValueError("target must start with python:, command: or http:")


def markdown(res: dict) -> str:
    lines = [f"**{res['passed']}/{res['total']} passed** ({res['counts']}), repeats={res['repeats']}", "", "| tag | passed |", "|---|---|"]
    lines += [f"| {t} | {d['pass']}/{d['total']} |" for t, d in sorted(res["by_tag"].items())]
    bad = [r for r in res["results"] if r["status"] != "pass"]
    if bad:
        lines += ["", "Not passing:"] + [f"- {r['id']} ({r['status']})" for r in bad]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="llm-testbench")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("cases")
    r.add_argument("--target", required=True)
    r.add_argument("--model")
    r.add_argument("--system")
    r.add_argument("--api-key-env", default="OPENAI_API_KEY")
    r.add_argument("--repeats", type=int, default=1)
    r.add_argument("--out")
    r.add_argument("--baseline", help="exit 1 if a case that passed there does not pass now")
    r.add_argument("--allow-failures", action="store_true", help="exit 0 even if cases fail (still 1 on regression)")
    a = p.parse_args(argv)
    try:
        cases = load_cases(a.cases)
        target = build_target(a.target, a)
    except (ValueError, OSError, ImportError, AttributeError) as e:
        print(f"setup error: {e}", file=sys.stderr)
        return 2
    res = run_all(cases, target, a.repeats)
    print(markdown(res))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    code = 0
    if res["passed"] != res["total"] and not a.allow_failures:
        code = 1
    if a.baseline:
        reg = compare(res, json.loads(Path(a.baseline).read_text(encoding="utf-8")))
        for line in reg:
            print("REGRESSION", line)
        if reg:
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
