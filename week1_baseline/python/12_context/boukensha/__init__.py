"""Port of `ruby/11_tui/lib/boukensha.rb` — the top-level aggregator.

Step 06 adds module-level state to this file, mirroring Ruby's `@config` / `@debug` / `@quiet`
module instance variables. It is a departure from five steps of dependency injection — `Agent`
still takes every collaborator by constructor argument — and only `Logger` reads it.

Ruby's `self.config` is a method and Python's is a function, but call sites read `config()` in
both. `debug?` and `quiet?` become `is_debug()` and `is_quiet()`: `?` is not legal in a Python
identifier, and the bare names are taken by the setters.
"""

import os
import sys

from . import backends, models, tools
from .agent import Agent
from .client import Client
from .config import Config
from .context import Context
from .errors import ApiError, UnknownToolError, UnsupportedModelError
from .logger import Logger
from .mcp.client import Client as McpClient
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .repl import Repl
from .run_dsl import RunDSL
from .tool import Tool
from .version import VERSION

_config = None
_quiet = False
_debug = False


def config():
    """Ruby: `@config ||= Config.new`. Memoized for the life of the process."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def quiet():
    """Ruby's `quiet!`. Declared and never consumed — nothing reads the flag."""
    global _quiet
    _quiet = True


def loud():
    """Ruby's `loud!`."""
    global _quiet
    _quiet = False


def is_quiet():
    return _quiet


def debug():
    """Ruby's `debug!`. Makes `Logger.raw` write the full provider response."""
    global _debug
    _debug = True


def is_debug():
    return _debug


def _missing_config_message(directory):
    """Says where it looked and how to fix it.

    Config resolution has three tiers and none of them are visible from a traceback, so spell all
    three out. Kept identical to Ruby's `missing_config_message`.
    """
    return (
        "boukensha: no `tasks.player` configuration found.\n"
        "\n"
        f"  looked in: {directory}/settings.yaml\n"
        "\n"
        "Config is resolved in this order:\n"
        "  1. $BOUKENSHA_DIR, if set\n"
        "  2. the nearest .boukensha at or above the current directory\n"
        "  3. ~/.boukensha\n"
        "\n"
        "You are most likely running from outside a project. Either cd into one, or:\n"
        "  BOUKENSHA_DIR=/path/to/.boukensha boukensha\n"
    )


def run(
    *,
    task,
    working_dir=None,
    allowed_commands=None,
    shell_timeout=30,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
    context_window=None,
    max_output_tokens=None,
    block=None,
):
    """The top-level entry point. Wires together every primitive so the caller only has to
    describe *what* to do, not *how* to plumb it.

        def register(dsl):
            @dsl.tool("read_file", description="Read a file from disk",
                      parameters={"path": {"type": "string", "description": "File path"}})
            def read_file(*, path):
                return Path(path).read_text()

        result = boukensha.run(task="Summarise boukensha/__init__.py", block=register)

    Arguments:
      task:              (required) the user message to hand the agent.
      system:            system prompt. Defaults to the task's resolved prompt.
      model:             model name. Defaults to the task's configured model.
      backend:           "anthropic" (default), "openai", "gemini", "ollama", "ollama_cloud".
      api_key:           defaults to the matching ANTHROPIC_/OPENAI_/GEMINI_/OLLAMA_API_KEY env
                         var, loaded from .boukensha/.env. Not needed for "ollama".
      ollama_host:       Ollama base URL.
      log:               JSONL path override. Defaults to .boukensha/sessions/<session-id>.jsonl.
      max_output_tokens: per-reply output cap. Defaults to the task's configured value.
      block:             callable taking a RunDSL, for registering tools (see run_dsl.py — Ruby
                         passes a block and `instance_eval`s it; Python cannot).

    Ruby's doc comment claims `system:` and `model:` default to `config.system_prompt` and
    `config.model`. They do not — there are no such methods. Both resolve through Config,
    as below. The code is ported; the comment's claim is not (plan §8).
    """
    # Ruby's `ensure logger&.close` is safe because a local is defined from parse time. Python
    # would raise UnboundLocalError in `finally` and MASK the real error — and only ever on the
    # failure path. Hence the explicit None (plan §5.2).
    logger = None
    # Same UnboundLocalError guard as `logger`: a failure before this is assigned must propagate
    # as itself, not as a NameError raised from the finally clause.
    mcp_clients = []
    try:
        cfg = config()  # loads .env; populates os.environ

        # Step 12 gives provider/model/limits defaults, so an unconfigured run no longer fails —
        # it quietly starts a session with a default model, no MCP servers and no credentials,
        # which is more confusing than an error. Say so instead. Explicit condition, not an
        # except, so nothing else is swallowed.
        if not cfg.settings:
            print(_missing_config_message(cfg.dir), file=sys.stderr)
            return None

        if system is None:
            system = cfg.system_prompt
        if model is None:
            model = cfg.model()
        if context_window is None:
            context_window = models.context_window(model)
        if backend is None:
            # Ruby calls .to_sym here; the Python tree has used strings for roles and providers
            # since step 01, so provider() already returns what the branch below matches on.
            backend = cfg.provider_type()
        if api_key is None:
            api_key = {
                "anthropic": lambda: os.environ.get("ANTHROPIC_API_KEY"),
                "openai": lambda: os.environ.get("OPENAI_API_KEY"),
                "gemini": lambda: os.environ.get("GEMINI_API_KEY"),
                "ollama_cloud": lambda: os.environ.get("OLLAMA_API_KEY"),
            }.get(backend, lambda: None)()

        # working_dir defaults to the invocation directory, matching Ruby's `working_dir: Dir.pwd`.
        # Pass working_dir=False to opt out of the filesystem and shell tools entirely.
        if working_dir is None:
            working_dir = os.getcwd()

        ctx = Context(system=system, context_window=context_window,
                      working_dir=working_dir or None,
                      compaction_threshold=cfg.agent_compaction_threshold())
        registry = Registry(ctx)

        if working_dir:
            tools.file_system.register(registry, working_dir=working_dir)
            tools.shell.register(
                registry, working_dir=working_dir,
                timeout=shell_timeout, allowed_commands=allowed_commands,
            )

        if block:
            block(RunDSL(registry))

        # Tools declared in settings.yaml under mcp_servers:. Started after the block so a
        # collision with a block-registered tool raises rather than being hidden.
        # This is the ONLY path to MUD tools in the Python tree (plan §5.1).
        mcp_clients = tools.mcp.register_all(registry, cfg.mcp_servers())

        if backend == "anthropic":
            be = backends.Anthropic(api_key=api_key, model=model)
        elif backend == "openai":
            be = backends.OpenAI(api_key=api_key, model=model)
        elif backend == "gemini":
            be = backends.Gemini(api_key=api_key, model=model)
        elif backend == "ollama":
            be = backends.Ollama(host=ollama_host, model=model)
        elif backend == "ollama_cloud":
            be = backends.OllamaCloud(api_key=api_key, model=model)
        else:
            raise ValueError(
                f"Unknown backend {backend!r}. Use 'anthropic', 'openai', 'gemini', 'ollama', "
                f"or 'ollama_cloud'."
            )

        builder = PromptBuilder(ctx, be)
        client = Client(builder)
        effective_max_iterations = cfg.agent_max_iterations()
        effective_max_turn_tokens = cfg.agent_max_turn_tokens()
        effective_max_output_tokens = max_output_tokens or cfg.agent_max_output_tokens()
        logger = Logger(
            log=log,
            snapshot={
                "context_window": context_window,
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )
        agent = Agent(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            max_turn_tokens=effective_max_turn_tokens,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
        )

        ctx.add_message("user", task)
        return agent.run()
    finally:
        if logger is not None:
            logger.close()
        for client in mcp_clients or []:
            client.close()


def repl(
    *,
    working_dir=None,
    allowed_commands=None,
    shell_timeout=30,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
    context_window=None,
    max_output_tokens=None,
    tui=True,
    block=None,
):
    """Interactive REPL: register tools once, then loop — reading tasks from stdin, running the
    agent, and printing replies — until the user types /exit or sends EOF.

    Conversation history accumulates across every turn, so the agent always sees the full
    transcript.

    Arguments are `run`'s, minus `task` — the user supplies tasks interactively. Everything else
    resolves from config exactly as it does for `run`.

    `tui=True` (default, new in step 11) wraps the REPL in the Textual front-end. Pass
    `tui=False`, or the `--no-tui` launcher flag, for the plain terminal REPL — which is also
    what the test suite and `week1_baseline/mcp/verify-python` use, since neither can drive a
    full-screen app.
    """
    # Same UnboundLocalError guard as run() (step-07 plan §5.2): a failure before the Logger is
    # constructed must propagate as itself, not as a NameError from the finally clause.
    logger = None
    # Same UnboundLocalError guard as `logger`: a failure before this is assigned must propagate
    # as itself, not as a NameError raised from the finally clause.
    mcp_clients = []
    try:
        cfg = config()  # loads .env; populates os.environ

        # Step 12 gives provider/model/limits defaults, so an unconfigured run no longer fails —
        # it quietly starts a session with a default model, no MCP servers and no credentials,
        # which is more confusing than an error. Say so instead. Explicit condition, not an
        # except, so nothing else is swallowed.
        if not cfg.settings:
            print(_missing_config_message(cfg.dir), file=sys.stderr)
            return

        if system is None:
            system = cfg.system_prompt
        if model is None:
            model = cfg.model()
        if context_window is None:
            context_window = models.context_window(model)
        if backend is None:
            backend = cfg.provider_type()
        if api_key is None:
            api_key = {
                "anthropic": lambda: os.environ.get("ANTHROPIC_API_KEY"),
                "openai": lambda: os.environ.get("OPENAI_API_KEY"),
                "gemini": lambda: os.environ.get("GEMINI_API_KEY"),
                "ollama_cloud": lambda: os.environ.get("OLLAMA_API_KEY"),
            }.get(backend, lambda: None)()

        # working_dir defaults to the invocation directory, matching Ruby's `working_dir: Dir.pwd`.
        # Pass working_dir=False to opt out of the filesystem and shell tools entirely.
        if working_dir is None:
            working_dir = os.getcwd()

        ctx = Context(system=system, context_window=context_window,
                      working_dir=working_dir or None,
                      compaction_threshold=cfg.agent_compaction_threshold())
        registry = Registry(ctx)

        if working_dir:
            tools.file_system.register(registry, working_dir=working_dir)
            tools.shell.register(
                registry, working_dir=working_dir,
                timeout=shell_timeout, allowed_commands=allowed_commands,
            )

        if block:
            block(RunDSL(registry))

        # Tools declared in settings.yaml under mcp_servers:. Started after the block so a
        # collision with a block-registered tool raises rather than being hidden.
        # This is the ONLY path to MUD tools in the Python tree (plan §5.1).
        mcp_clients = tools.mcp.register_all(registry, cfg.mcp_servers())

        if backend == "anthropic":
            be = backends.Anthropic(api_key=api_key, model=model)
        elif backend == "openai":
            be = backends.OpenAI(api_key=api_key, model=model)
        elif backend == "gemini":
            be = backends.Gemini(api_key=api_key, model=model)
        elif backend == "ollama":
            be = backends.Ollama(host=ollama_host, model=model)
        elif backend == "ollama_cloud":
            be = backends.OllamaCloud(api_key=api_key, model=model)
        else:
            raise ValueError(
                f"Unknown backend {backend!r}. Use 'anthropic', 'openai', 'gemini', 'ollama', "
                f"or 'ollama_cloud'."
            )

        builder = PromptBuilder(ctx, be)
        client = Client(builder)
        effective_max_iterations = cfg.agent_max_iterations()
        effective_max_turn_tokens = cfg.agent_max_turn_tokens()
        effective_max_output_tokens = max_output_tokens or cfg.agent_max_output_tokens()
        logger = Logger(
            log=log,
            snapshot={
                "context_window": context_window,
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )

        the_repl = Repl(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            max_turn_tokens=effective_max_turn_tokens,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
            config_dir=cfg.dir,
            provider=backend,
            model=model,
            version=VERSION,
            api_key=api_key,
        )

        # A full-screen app needs a real terminal. Under pytest, a pipe, or CI, stdin/stdout are
        # not a tty and Textual would either fail outright or swallow the session — so fall back
        # to the plain REPL. This is what lets the test suite and week1_baseline/mcp/verify-python
        # call repl() without special-casing it. Ruby relies on the --no-tui flag alone here; the
        # extra guard is Python-side only, and deliberate.
        if tui and not (sys.stdin.isatty() and sys.stdout.isatty()):
            tui = False

        if tui:
            # Imported here rather than at module scope so steps that never launch the TUI — and
            # any environment without Textual installed — can still import boukensha. Mirrors the
            # `defined?(Tui)` guard Ruby needs for the same reason.
            from .tui import Tui

            Tui(the_repl).run()
        else:
            the_repl.start()
    except KeyboardInterrupt:
        # Ruby's `rescue Interrupt`. Ctrl-C leaves the REPL gracefully rather than dumping a
        # traceback over the session.
        print("\nInterrupted.")
    finally:
        if logger is not None:
            logger.close()
        for client in mcp_clients or []:
            client.close()


__all__ = [
    "VERSION",
    "Agent",
    "ApiError",
    "Client",
    "Config",
    "Context",
    "Logger",
    "McpClient",
    "Message",
    "PromptBuilder",
    "Registry",
    "Repl",
    "RunDSL",
    "Tool",
    "UnknownToolError",
    "UnsupportedModelError",
    "backends",
    "config",
    "debug",
    "is_debug",
    "is_quiet",
    "loud",
    "models",
    "quiet",
    "repl",
    "run",
    "tools",
]
