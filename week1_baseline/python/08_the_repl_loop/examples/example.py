import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boukensha

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

# Config is loaded automatically inside boukensha.repl — system prompt, model, and API key all
# come from ~/.boukensha (or BOUKENSHA_DIR) by default.

# The base directory tools will operate relative to — this step's own folder makes a good
# playground since it already has source files to read.
base_dir = Path(__file__).resolve().parent.parent

print(f"Config: {boukensha.config()}")
print()


def register(dsl):
    """Ruby passes a block and `instance_eval`s it so a bare `tool "..."` resolves against the
    RunDSL. Python has no equivalent, so the DSL arrives as an argument instead — see
    `boukensha/run_dsl.py`. Unchanged from step 07; only the entry point below differs.
    """

    @dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={
            "path": {"type": "string", "description": "File path (relative to the working directory)"}
        },
    )
    def read_file(*, path):
        return (base_dir / path).read_text()

    @dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={
            "path": {
                "type": "string",
                "description": "Directory path (relative to the working directory, or '.' for root)",
            }
        },
    )
    def list_directory(*, path):
        return ", ".join(e for e in sorted(os.listdir(base_dir / path)) if not e.startswith("."))


boukensha.repl(block=register)
