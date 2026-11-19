"""Targets turn an input string into an output string. A target error is an ERROR, never a pass."""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Callable


class TargetError(RuntimeError):
    pass


def python_target(spec: str) -> Callable[[str], str]:
    """'package.module:function' where function(str) -> str."""
    mod, _, fn = spec.partition(":")
    if not fn:
        raise ValueError("python target must look like module:function")
    return getattr(importlib.import_module(mod), fn)


def command_target(cmd: str, timeout: float = 60.0) -> Callable[[str], str]:
    """Runs `cmd` with the input on stdin; stdout is the output."""
    def call(text: str) -> str:
        try:
            p = subprocess.run(cmd, shell=True, input=text, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise TargetError(f"command timed out after {timeout}s") from e
        if p.returncode != 0:
            raise TargetError(f"command exited {p.returncode}: {p.stderr.strip()[:200]}")
        return p.stdout.strip()
    return call


def http_target(base_url: str, model: str, api_key_env: str = "OPENAI_API_KEY", system: str | None = None, timeout: float = 60.0) -> Callable[[str], str]:
    """Any OpenAI-compatible /chat/completions endpoint (OpenAI, vLLM, Ollama, LM Studio, ...)."""
    key = os.environ.get(api_key_env, "")

    def call(text: str) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": text}]
        req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps({"model": model, "messages": msgs, "temperature": 0}).encode(),
                                     headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode())
            return body["choices"][0]["message"]["content"]
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as e:
            raise TargetError(f"http target failed: {e}") from e
    return call
