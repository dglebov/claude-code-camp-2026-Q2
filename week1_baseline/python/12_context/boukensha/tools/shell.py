"""Port of `ruby/11_tui/lib/boukensha/tools/shell.rb`.

Registers `run_command`: run a command inside the working directory, return combined
stdout+stderr, with a timeout and an optional allow-list.

**`shell=True` is deliberate, and so is the caveat that comes with it.** The plan (§5.5) said
to avoid it — that was wrong on the facts. Ruby's `Open3.capture2e(command, chdir:)` is given a
*string*, and Ruby hands a string containing shell metacharacters to the shell. Verified against
the reference: `echo A; echo B` runs both, and `echo hi | tr a-z A-Z` pipes. Splitting the string
in Python instead would silently break every pipeline and redirection the Ruby tree accepts.

**Therefore `allowed_commands` is advisory, not a security boundary — in both trees.** It checks
only the first token, so with `allowed_commands=["git"]` the command `git; rm -rf ~` passes the
check and the shell then runs both halves. This is a pre-existing property of the Ruby step, not
something introduced here; it is written down because a list named "allowed commands" reads like
a sandbox and is not one. Treat it as a guard against the model wandering, never against a
hostile one.
"""

import subprocess


def register(registry, *, working_dir, timeout=30, allowed_commands=None):
    import os

    root = os.path.abspath(os.path.expanduser(str(working_dir)))

    def oops(msg):
        return f"error: {msg}"

    allow_note = ""
    if allowed_commands:
        allow_note = f"Allowed executables: {', '.join(str(c) for c in allowed_commands)}."

    @registry.tool(
        "run_command",
        description=(
            "Run a shell command inside the working directory and return its combined "
            f"stdout+stderr output. Commands run with a {timeout}-second timeout. {allow_note}"
        ),
        parameters={
            "command": {
                "type": "string",
                "description": (
                    "The shell command to execute (e.g. 'python script.py', 'ls -la', 'git status')"
                ),
            }
        },
    )
    def run_command(*, command):
        if allowed_commands is not None:
            executable = str(command).strip().split()
            executable = executable[0] if executable else ""
            if executable not in [str(c) for c in allowed_commands]:
                return oops(
                    f"'{executable}' is not in the allowed-commands list "
                    f"({', '.join(str(c) for c in allowed_commands)})"
                )

        try:
            completed = subprocess.run(
                command,
                shell=True,  # see the module docstring — mirrors Ruby, with its caveat
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
                # A non-zero exit is a normal outcome the model should see, not an exception —
                # the exit code is reported in the returned text instead.
                check=False,
            )
        except subprocess.TimeoutExpired:
            return oops(f"command timed out after {timeout}s: {command}")
        except OSError as error:
            return oops(f"command not found: {error}")
        except Exception as error:  # noqa: BLE001 — Ruby's bare `rescue => e` equivalent
            return oops(str(error))

        # Ruby's capture2e interleaves both streams into one; subprocess keeps them apart, so
        # rejoin in the same order Ruby would have produced.
        combined = (completed.stdout or "") + (completed.stderr or "")
        exit_note = "" if completed.returncode == 0 else f"\n[exit {completed.returncode}]"
        output = combined.strip()
        return f"(no output){exit_note}" if not output else f"{output}{exit_note}"
