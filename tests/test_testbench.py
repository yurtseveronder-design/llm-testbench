import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from llm_testbench import checks, cli  # noqa: E402
from llm_testbench.runner import compare, load_cases, run_all, run_case  # noqa: E402


class T(unittest.TestCase):
    def test_checks(self):
        self.assertTrue(checks.contains_all("Hello World", ["hello", "world"])[0])
        self.assertFalse(checks.must_not_contain("it is APPROVED", ["approved"])[0])
        self.assertTrue(checks.abstains("I don't know that.")[0])
        self.assertFalse(checks.json_valid("not json")[0])
        self.assertFalse(checks.json_valid('{"a":1}', required_keys=["b"])[0])
        self.assertFalse(checks.max_words("a b c", 2)[0])

    def test_unknown_check_is_an_error_not_a_pass(self):
        with self.assertRaises(ValueError):
            checks.run_check({"type": "nope"}, "x")

    def test_target_error_is_error_never_pass(self):
        def boom(_):
            raise RuntimeError("down")
        r = run_case({"id": "a", "input": "x", "checks": [{"type": "must_not_contain", "values": ["zzz"]}]}, boom)
        self.assertEqual(r["status"], "error")

    def test_flaky_detected(self):
        calls = iter(["good", "bad", "good"])
        r = run_case({"id": "a", "input": "x", "checks": [{"type": "contains_all", "values": ["good"]}]}, lambda _: next(calls), repeats=3)
        self.assertEqual(r["status"], "flaky")

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.jsonl"
            line = json.dumps({"id": "a", "input": "x", "checks": []})
            p.write_text(line + "\n" + line + "\n")
            with self.assertRaises(ValueError):
                load_cases(p)

    def test_example_run_and_regression(self):
        cases = load_cases(ROOT / "examples" / "cases.jsonl")
        from examples.toy import answer
        res = run_all(cases, answer)
        self.assertEqual(res["passed"], 3)  # the toy is hijackable on purpose: the injection case fails
        self.assertEqual(res["by_tag"]["attack"]["pass"], 0)
        worse = json.loads(json.dumps(res))
        worse["results"][0]["status"] = "fail"
        self.assertEqual(len(compare(worse, res)), 1)

    def test_cli_exit_codes(self):
        argv = ["run", str(ROOT / "examples" / "cases.jsonl"), "--target", "python:examples.toy:answer"]
        self.assertEqual(cli.main(argv), 1)  # one failing case
        self.assertEqual(cli.main(argv + ["--allow-failures"]), 0)
        self.assertEqual(cli.main(["run", "missing.jsonl", "--target", "python:examples.toy:answer"]), 2)


    def test_http_target_against_local_fake(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from llm_testbench.targets import TargetError, http_target

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers["Content-Length"])
                msg = json.loads(self.rfile.read(n))["messages"][-1]["content"]
                body = json.dumps({"choices": [{"message": {"content": "echo: " + msg}}]}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            call = http_target(f"http://127.0.0.1:{srv.server_port}/v1", "m")
            self.assertEqual(call("hi"), "echo: hi")
        finally:
            srv.shutdown()
        with self.assertRaises(TargetError):
            http_target("http://127.0.0.1:1/v1", "m", timeout=1)("hi")


if __name__ == "__main__":
    unittest.main()
