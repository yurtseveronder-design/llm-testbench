# llm-testbench

A small test harness for anything that takes text in and gives text out: an LLM, a RAG app, an agent wrapper. Standard library only.

You write cases in a JSONL file. Each case has an input and some **deterministic checks** (rules you can read, no LLM judge). You point the tool at a target and get a pass/fail report, optionally repeated runs to spot flaky answers, and a regression check against an earlier run.

## Quick start

```bash
git clone https://github.com/yurtseveronder-design/llm-testbench && cd llm-testbench
export PYTHONPATH=src:.
python -m llm_testbench.cli run examples/cases.jsonl --target python:examples.toy:answer --repeats 2
```

Output: a pass count, results by tag, and the list of cases that do not pass. The example toy target fails one case (a prompt injection) on purpose.

## Case format

```json
{"id": "refund-window", "tags": ["lookup"], "input": "What is the refund window?",
 "checks": [{"type": "contains_all", "values": ["30 days", "proof of purchase"]}]}
```

Checks: `contains_all`, `contains_any`, `must_not_contain`, `regex`, `not_regex`, `max_words`, `json_valid` (with `required_keys`), `abstains`, `equals`. Matching is case-insensitive.

## Targets

| Target | Example |
|---|---|
| Python function `f(str) -> str` | `--target python:mypkg.app:answer` |
| Any command (input on stdin, output on stdout) | `--target "command:python my_app.py"` |
| OpenAI-compatible HTTP API (OpenAI, vLLM, Ollama, LM Studio) | `--target http:http://localhost:11434/v1 --model llama3` (key from `OPENAI_API_KEY`, change with `--api-key-env`) |

## Statuses and exit codes

- `pass`: every check passed on every repeat. `fail`: failed every time. `flaky`: passed some repeats, failed others. `error`: the target itself failed (timeout, HTTP error). **An error is never counted as a pass.**
- `--baseline old.json` exits 1 if a case that passed before does not pass now (regression).
- Exit codes: 0 all good, 1 failures or regressions, 2 usage or setup error. `--allow-failures` makes plain failures exit 0 but regressions still exit 1.

## Limits

- Checks are string and structure rules. They cannot judge whether an answer is *good*, only whether it contains or avoids what you listed. A wrong answer that happens to contain the keywords passes.
- Keyword checks are only as good as the cases you write. Cases written by the same person who built the app tend to flatter it; keep a private set you never tune against.
- The HTTP target is tested only against a local fake in unit tests, not against any real provider.
- Temperature is fixed to 0 for HTTP targets, but providers can still vary. Use `--repeats` to see it.
- No parallelism, no cost tracking, no LLM-as-judge. Small on purpose.

## Used with: a real cross-check

`examples/convert_ssa.py` turns the 28 questions of [sentinel-support-assistant](https://github.com/yurtseveronder-design/sentinel-support-assistant) into cases, and `examples/ssa_target.py` wraps that app as a target. Running them through this tool gave the same scores as the app's own runner: **17/28** with no guard and **23/28** with Sentinel's rules (simulated gullible model, 2 repeats, no flaky cases). Two independent runners agreeing is the only validation here; it is not a benchmark of any real LLM.

```bash
export SSA_ROOT=/path/to/sentinel-support-assistant SSA_GUARD=local SSA_MODEL=gullible
PYTHONPATH=src:.:/path/to/ai-sentinel/src python -m llm_testbench.cli run examples/ssa_cases.jsonl --target python:examples.ssa_target:answer --allow-failures
```

## AI assistance

Built with Claude (Anthropic) as part of a demonstration that real tools can be made, tested and honestly reported with AI.

MIT licence.
