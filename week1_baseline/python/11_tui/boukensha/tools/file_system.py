"""Port of `ruby/11_tui/lib/boukensha/tools/file_system.rb`.

Registers the standard file-oriented tools against a registry, all sandboxed to a single root.

Every path the agent supplies is resolved relative to that root. A path that would escape it
returns an error *string* rather than raising — the agent sees the message and can try something
sensible, whereas an exception would end the turn.

Path containment mirrors Ruby deliberately (plan §5.4). `File.expand_path` normalises `..`
without resolving symlinks, so `os.path.abspath` (not `Path.resolve`, not `os.path.realpath`) is
the faithful equivalent. The consequence is real: a symlink inside the root pointing outside it
is permitted by both trees. `realpath` would be the stricter, arguably safer choice — matching
Ruby is the diffability choice, and `test_tools_file_system.py` pins it in both directions so the
behaviour is deliberate rather than incidental.
"""

import os
import re


def register(registry, *, working_dir):
    root = os.path.abspath(os.path.expanduser(str(working_dir)))

    def resolve(path):
        """Absolute path inside root, or an error string."""
        # Ruby's File.expand_path(path, root): an absolute path ignores root entirely, which is
        # why the containment check below has to run on the RESULT, not on the input.
        absolute = os.path.abspath(os.path.join(root, os.path.expanduser(str(path))))
        if absolute == root or absolute.startswith(root + os.sep):
            return absolute
        return f"error: path '{path}' escapes the working directory"

    def oops(msg):
        return f"error: {msg}"

    def failed(value):
        return isinstance(value, str) and value.startswith("error:")

    @registry.tool(
        "pwd",
        description="Return the working directory — the root that all file paths are relative to.",
        parameters={},
    )
    def pwd():
        return root

    @registry.tool(
        "list_directory",
        description=(
            "List files and subdirectories at a path relative to the working directory. "
            "Defaults to the working directory itself."
        ),
        parameters={"path": {"type": "string", "description": "Relative path to list (default '.')"}},
        required=[],
    )
    def list_directory(*, path="."):
        target = resolve(path)
        if failed(target):
            return target
        if not os.path.isdir(target):
            return oops(f"'{path}' is not a directory")

        entries = sorted(os.listdir(target))
        rendered = [
            f"{name}/" if os.path.isdir(os.path.join(target, name)) else name for name in entries
        ]
        return "\n".join(rendered) if rendered else "(empty)"

    @registry.tool(
        "read_file",
        description=(
            "Read and return the full contents of a file. Path is relative to the working directory."
        ),
        parameters={"path": {"type": "string", "description": "Relative path to the file"}},
    )
    def read_file(*, path):
        target = resolve(path)
        if failed(target):
            return target
        if not os.path.isfile(target):
            return oops(f"'{path}' is not a file")

        try:
            with open(target, encoding="utf-8") as handle:
                return handle.read()
        except OSError as error:
            return oops(str(error))
        except UnicodeDecodeError as error:
            # Ruby's File.read returns bytes tagged UTF-8 without validating, so a binary file
            # comes back as mojibake rather than an error. Python raises. An error string is the
            # more useful outcome for the agent, and is a documented divergence.
            return oops(f"cannot decode as UTF-8: {error}")

    @registry.tool(
        "write_file",
        description=(
            "Write content to a file, creating it (and any missing parent directories) if needed, "
            "overwriting if it exists. Path is relative to the working directory."
        ),
        parameters={
            "path": {"type": "string", "description": "Relative path to the file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
    )
    def write_file(*, path, content):
        target = resolve(path)
        if failed(target):
            return target

        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as error:
            return oops(str(error))

        rel = target[len(root) + 1 :] if target.startswith(root + os.sep) else target
        # bytesize, not length: Ruby reports bytes, and a multibyte string would differ.
        return f"ok: wrote {len(content.encode('utf-8'))} bytes to {rel}"

    @registry.tool(
        "delete_file",
        description=(
            "Delete a file. Directories are not deleted. Path is relative to the working directory."
        ),
        parameters={"path": {"type": "string", "description": "Relative path to the file to delete"}},
    )
    def delete_file(*, path):
        target = resolve(path)
        if failed(target):
            return target
        if not os.path.isfile(target):
            return oops(f"'{path}' is not a file")

        try:
            os.remove(target)
        except OSError as error:
            return oops(str(error))
        return f"ok: deleted {path}"

    @registry.tool(
        "search_files",
        description=(
            "Search for a text pattern (literal string or regex) across all files in the working "
            "directory tree. Returns matching lines in 'path:line_number:content' format."
        ),
        parameters={
            "pattern": {"type": "string", "description": "The text or regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Subdirectory or file to search within (default '.' = entire working directory)",
            },
            "glob": {
                "type": "string",
                "description": "File glob to restrict which files are searched, e.g. '*.py' (default '*')",
            },
        },
        required=["pattern"],
    )
    def search_files(*, pattern, path=".", glob="*"):
        target = resolve(path)
        if failed(target):
            return target

        try:
            regex = re.compile(pattern)
        except re.error as error:
            return oops(f"invalid pattern: {error}")

        if os.path.isfile(target):
            files = [target]
        else:
            import glob as globlib

            files = sorted(
                globlib.glob(os.path.join(target, "**", glob), recursive=True)
            )

        matches = []
        for file in files:
            if not os.path.isfile(file):
                continue
            rel = file[len(root) + 1 :] if file.startswith(root + os.sep) else file
            try:
                with open(file, encoding="utf-8") as handle:
                    for lineno, line in enumerate(handle, start=1):
                        if regex.search(line):
                            matches.append(f"{rel}:{lineno}:{line.rstrip(chr(10))}")
            except (OSError, UnicodeDecodeError) as error:
                matches.append(f"{rel}: error reading file: {error}")

        return "\n".join(matches) if matches else "no matches"
