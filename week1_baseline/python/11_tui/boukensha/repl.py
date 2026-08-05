"""Port of `ruby/11_tui/lib/boukensha/repl.rb`.

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

**What step 11 changed.** Two seams, so something other than a terminal can drive this class:

  * `on_output` — redirect everything the REPL would otherwise print
  * `handle_command` — command dispatch, lifted out of the read loop

`Tui` uses both. Neither changes behaviour when no callback is registered, which is what keeps
the `--no-tui` path byte-identical to step 10. `banner` and `run_turn` also became public
(`_banner`/`_run_turn` in step 10) because the TUI calls them directly.

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
        self._output_cb = None
        self._cancel = None

    # ---------- accessors --------------------------------------------------
    #
    # Ruby gained `attr_reader :logger, :context, :model, :version` in step 11 so a front-end can
    # subscribe to log events and render a status line. Properties are the Python equivalent; the
    # underscore attributes stay authoritative so nothing else in the class changes.

    @property
    def logger(self):
        return self._logger

    @property
    def context(self):
        return self._context

    @property
    def model(self):
        return self._model

    @property
    def version(self):
        return self._version

    # ---------- output redirection ----------------------------------------

    def on_output(self, callback):
        """Register a callable that receives every string the REPL would otherwise print.

        Once set, nothing reaches stdout — all output is routed through the callback instead.
        Ruby takes a block; Python takes any callable.
        """
        self._output_cb = callback

    def _output(self, text):
        text = "" if text is None else str(text)
        if self._output_cb:
            self._output_cb(text)
        else:
            # Mirror Ruby's `puts`: it appends a newline only when the string lacks one.
            # Python's print always appends, which would double-space HELP and the banner.
            print(text, end="" if text.endswith("\n") else "\n")

    # ---------- session ----------------------------------------------------

    def _step_line(self):
        """Which copy of the library is actually running.

        There are a dozen step folders in this tree, each shipping a complete `boukensha`
        package. The version string alone does not answer "which code is this?" unless you
        already know that 0.11.0 means 11_tui — so say it plainly. Derived from this file's own
        location, which is the only thing that cannot lie about it.
        """
        return os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def banner(self):
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
            f"  step:      {self._step_line()}\n"
            f"  config:    {config_line}\n"
            f"  provider:  {provider_line}\n"
            "\n"
            "  /quiet or /loud   toggle logging\n"
            "  /clear           reset conversation history\n"
            "  /exit or /quit    leave the REPL\n"
            # Ruby's heredoc carries a blank line before BANNER, so the string ends "\n\n".
            # Step 10 got the same on-screen result by accident: its banner string ended with a
            # single newline and `print` unconditionally added the second. Now that _output
            # mimics `puts` (which adds nothing to a string already ending in a newline), the
            # blank line has to be in the string — where Ruby actually has it.
            "\n"
        )

    def handle_command(self, entry):
        """Dispatch a slash command.

        Returns "quit", "command", or None (not a command at all). Ruby returns the symbols
        :quit / :command / nil; plain strings are the closest Python equivalent, and the caller
        only ever compares them.
        """
        if entry in ("/exit", "/quit"):
            self._output("Goodbye.")
            return "quit"
        if entry == "/help":
            self._output(HELP)
            return "command"
        if entry == "/quiet":
            # Imported at call time, not module scope: __init__.py imports this module while
            # it is still executing, so a top-level `import boukensha` would be circular.
            import boukensha

            boukensha.quiet()
            self._output("(logging suppressed — type /loud to re-enable)")
            return "command"
        if entry == "/loud":
            import boukensha

            boukensha.loud()
            self._output("(logging enabled)")
            return "command"
        if entry == "/clear":
            self._context.clear_messages()
            self._turn = 0
            self._output("(conversation history cleared)")
            return "command"
        return None

    def run_turn(self, entry, cancel=None):
        """Run one agent turn.

        `cancel` is a `threading.Event` the TUI sets when the user presses ESC. See
        `agent.py` — Python cannot raise asynchronously into another thread the way Ruby's
        `Thread#raise` does, so cancellation is cooperative and lands at an iteration boundary.
        """
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
            cancel=cancel,
        )

        try:
            result = agent.run()
        except LoopError as error:
            self._output(f"\n[error] {error}")
            return
        except ApiError as error:
            self._output(f"\n[error] API call failed: {error}")
            return

        # Routed through _output rather than print so the reply stays visible even when
        # boukensha.quiet() is active — the whole point of /quiet is to keep the conversation and
        # drop the telemetry — and so a front-end can capture it.
        self._output("")
        self._output(result)

    def start(self):
        self._output(self.banner())

        while True:
            # A front-end draws its own prompt; only the bare terminal needs this.
            if not self._output_cb:
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

            result = self.handle_command(entry)
            if result == "quit":
                break
            if result:
                continue

            self.run_turn(entry)
