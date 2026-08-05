"""Port of `ruby/10_standard_tool_library/lib/boukensha/repl.rb`.

Repl is the interactive session loop. It wraps the same primitives as a single `boukensha.run`
call, but instead of running once it stays alive: it reads a task from the user, runs the agent,
prints the reply, and loops back to the prompt.

The Context is shared across every turn, so conversation history accumulates naturally — the
agent sees the full transcript each time it is called. A fresh Agent is built per turn, exactly
as Ruby does; the Agent is stateless between runs apart from its iteration counter.

Built-in commands (not sent to the agent):
  /help    print the command list
  /quiet   suppress detailed logging
  /loud    re-enable logging
  /clear   wipe conversation history (tools stay registered)
  /exit    leave the REPL
  /quit    alias for /exit

Ruby has no collision between the `Boukensha::Repl` constant and the `Boukensha.repl` method —
constants and methods live in separate namespaces. Python has one namespace: `def repl(...)` in
`__init__.py` rebinds the `boukensha.repl` attribute from this module to that function. That is
harmless at runtime, because `__init__.py` binds the `Repl` class by name before the rebind
happens. It does mean tests cannot reach this module as `boukensha.repl`; they must use
`importlib.import_module("boukensha.repl")`, which reads `sys.modules`. The filename stays
`repl.py` so it remains diffable against `repl.rb`.
"""

import os
import sys

from .agent import Agent
from .errors import ApiError, LoopError

PROMPT = "boukensha> "

HELP = """Commands:
  /quiet   suppress logging output
  /loud    re-enable logging output
  /clear   wipe conversation history (tools stay)
  /exit    leave the REPL
  /help    show this message
"""


class Repl:
    PROMPT = PROMPT
    HELP = HELP

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger,
        config_dir=None,
        provider=None,
        model=None,
        version=None,
        api_key=None,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
    ):
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        self._logger = logger
        self._task_settings = task_settings
        self._max_iterations = max_iterations
        self._max_output_tokens = max_output_tokens
        self._config_dir = config_dir
        self._provider = provider
        self._model = model
        self._version = version
        self._api_key = api_key
        self._turn = 0

    def start(self):
        print(self._banner())

        while True:
            print(PROMPT, end="", flush=True)

            # readline() rather than input(): Ruby's `$stdin.gets` returns nil at EOF, and an
            # empty string is the direct Python equivalent. input() raises EOFError instead,
            # which would need catching to express the same control flow.
            line = sys.stdin.readline()
            if line == "":  # EOF / Ctrl-D
                break

            entry = line.rstrip("\n").strip()
            if not entry:
                continue

            if entry in ("/exit", "/quit"):
                print("Goodbye.")
                break
            if entry == "/help":
                # end="" because HELP already ends in a newline. Ruby's `puts` does not add a
                # second one when the string has it; Python's print always would.
                print(HELP, end="")
                continue
            if entry == "/quiet":
                # Imported at call time, not module scope: __init__.py imports this module while
                # it is still executing, so a top-level `import boukensha` would be circular.
                import boukensha

                boukensha.quiet()
                print("(logging suppressed — type /loud to re-enable)")
                continue
            if entry == "/loud":
                import boukensha

                boukensha.loud()
                print("(logging enabled)")
                continue
            if entry == "/clear":
                self._context.clear_messages()
                self._turn = 0
                print("(conversation history cleared)")
                continue

            self._run_turn(entry)

    # ---------- private ---------------------------------------------------

    def _banner(self):
        key_status = "✓ API key set" if (self._api_key or "").strip() else "✗ API key not set"
        provider_line = f"{self._provider or 'default'} ({self._model or 'default'})  {key_status}"
        config_exists = self._config_dir and os.path.isdir(self._config_dir)
        config_line = (
            self._config_dir
            if config_exists
            else f"{self._config_dir or '(default)'}  ✗ directory not found"
        )
        ver = self._version or "?.?.?"
        # Ruby's `" " * (9 - ver.length)` raises on a version longer than 9 characters. max()
        # keeps the box from throwing; it will simply widen, which is the lesser failure.
        padding = " " * max(0, 9 - len(ver))

        return (
            "\n"
            "╔══════════════════════════════════════╗\n"
            f"║  BOUKENSHA MUD Assistant (v{ver}){padding}║\n"
            "╚══════════════════════════════════════╝\n"
            f"  config:    {config_line}\n"
            f"  provider:  {provider_line}\n"
            "\n"
            "  /quiet or /loud   toggle logging\n"
            "  /clear           reset conversation history\n"
            "  /exit or /quit    leave the REPL\n"
        )

    def _run_turn(self, entry):
        self._turn += 1
        self._logger.turn(n=self._turn)

        self._context.add_message("user", entry)

        agent = Agent(
            context=self._context,
            registry=self._registry,
            builder=self._builder,
            client=self._client,
            logger=self._logger,
            task_settings=self._task_settings,
            max_iterations=self._max_iterations,
            max_output_tokens=self._max_output_tokens,
        )

        try:
            result = agent.run()
        except LoopError as error:
            print(f"\n[error] {error}")
            return
        except ApiError as error:
            print(f"\n[error] API call failed: {error}")
            return

        # Printed outside the logger so the reply stays visible even when boukensha.quiet() is
        # active — the whole point of /quiet is to keep the conversation and drop the telemetry.
        print()
        print(result)
