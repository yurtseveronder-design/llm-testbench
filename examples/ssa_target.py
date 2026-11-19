"""Target for sentinel-support-assistant. Set SSA_ROOT (repo path), SSA_GUARD (none|local|sentinel), SSA_MODEL (extractive|gullible)."""
import os
import sys
from pathlib import Path

root = Path(os.environ["SSA_ROOT"])
sys.path.insert(0, str(root / "src"))
from support_assistant.cli import build  # noqa: E402

_asst = build(root, os.environ.get("SSA_GUARD", "none"), os.environ.get("SSA_MODEL", "extractive"))


def answer(text: str) -> str:
    return _asst.ask(text).text
