import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boukensha

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

# Config is loaded automatically inside boukensha.run — system prompt, model, and API key all
# come from ~/.boukensha (or BOUKENSHA_DIR) by default. Any of them can still be overridden as
# a keyword argument.

base_dir = Path(__file__).resolve().parent.parent

print("=== BOUKENSHA Step 7: The boukensha.run DSL ===")
print()
print(f"Config: {boukensha.config()}")
print()


def register(dsl):
    """Ruby passes a block and `instance_eval`s it so a bare `tool "..."` resolves against the
    RunDSL. Python has no equivalent, so the DSL arrives as an argument instead — see
    `boukensha/run_dsl.py`. Everything else about the block is the same, including closing over
    `base_dir` from the enclosing scope.
    """

    @dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={"path": {"type": "string", "description": "The file path to read"}},
    )
    def read_file(*, path):
        return (base_dir / path).read_text()

    @dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={"path": {"type": "string", "description": "The directory path to list"}},
    )
    def list_directory(*, path):
        return ", ".join(e for e in sorted(os.listdir(base_dir / path)) if not e.startswith("."))


result = boukensha.run(
    task="Read the README.md file and summarise what this MUD player assistant framework can do.",
    block=register,
)

print()
print("=== FINAL RESPONSE ===")
print(result)
