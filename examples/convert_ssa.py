"""Convert sentinel-support-assistant's eval/questions.jsonl to llm-testbench cases.
Usage: python examples/convert_ssa.py path/to/questions.jsonl > examples/ssa_cases.jsonl"""
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    q = json.loads(line)
    if q["type"] == "not_in_docs":
        checks = [{"type": "abstains"}]
    elif "contains_all" in q:
        checks = [{"type": "contains_all", "values": q["contains_all"]}]
    else:
        checks = [{"type": "must_not_contain", "values": q["must_not_contain"]}]
    print(json.dumps({"id": q["id"], "tags": [q["type"]], "input": q["question"], "checks": checks}, ensure_ascii=False))
