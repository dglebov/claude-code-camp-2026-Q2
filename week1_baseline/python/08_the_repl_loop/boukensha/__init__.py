"""Port of `ruby/08_the_repl_loop/lib/boukensha.rb` — the top-level aggregator.

Step 06 adds module-level state to this file, mirroring Ruby's `@config` / `@debug` / `@quiet`
module instance variables. It is a departure from five steps of dependency injection — `Agent`
still takes every collaborator by constructor argument — and only `Logger` reads it.

Ruby's `self.config` is a method and Python's is a function, but call sites read `config()` in
both. `debug?` and `quiet?` become `is_debug()` and `is_quiet()`: `?` is not legal in a Python
identifier, and the bare names are taken by the setters.
"""

import os

from . import backends
from .agent import Agent
from .client import Client
from .config import Config
from .context import Context
from .errors import ApiError, UnknownToolError, UnsupportedModelError
from .logger import Logger
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .repl import Repl
from .run_dsl import RunDSL
from .tasks.player import Player
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


def run(
    *,
    task,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
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
    `config.model`. They do not — there are no such methods. Both resolve through Tasks::Player,
    as below. The code is ported; the comment's claim is not (plan §8).
    """
    # Ruby's `ensure logger&.close` is safe because a local is defined from parse time. Python
    # would raise UnboundLocalError in `finally` and MASK the real error — and only ever on the
    # failure path. Hence the explicit None (plan §5.2).
    logger = None
    try:
        cfg = config()  # loads .env; populates os.environ
        task_class = Player
        task_settings = cfg.tasks(task_class.task_name())
        if system is None:
            system = task_class.system_prompt(
                task_settings,
                user_prompts_dir=cfg.user_prompts_dir,
                default_prompts_dir=Config.PROMPTS_DIR,
            )
        if model is None:
            model = task_class.model(task_settings)
        if backend is None:
            # Ruby calls .to_sym here; the Python tree has used strings for roles and providers
            # since step 01, so provider() already returns what the branch below matches on.
            backend = task_class.provider(task_settings)
        if api_key is None:
            api_key = {
                "anthropic": lambda: os.environ.get("ANTHROPIC_API_KEY"),
                "openai": lambda: os.environ.get("OPENAI_API_KEY"),
                "gemini": lambda: os.environ.get("GEMINI_API_KEY"),
                "ollama_cloud": lambda: os.environ.get("OLLAMA_API_KEY"),
            }.get(backend, lambda: None)()

        ctx = Context(task=task_class, system=system)
        registry = Registry(ctx)

        if block:
            block(RunDSL(registry))

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
        effective_max_iterations = task_class.max_iterations(task_settings)
        effective_max_output_tokens = max_output_tokens or task_class.max_output_tokens(task_settings)
        logger = Logger(
            log=log,
            snapshot={
                "task": task_class.task_name(),
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
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
        )

        ctx.add_message("user", task)
        return agent.run()
    finally:
        if logger is not None:
            logger.close()


def repl(
    *,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
    max_output_tokens=None,
    block=None,
):
    """Interactive REPL: register tools once, then loop — reading tasks from stdin, running the
    agent, and printing replies — until the user types /exit or sends EOF.

    Conversation history accumulates across every turn, so the agent always sees the full
    transcript.

    Arguments are `run`'s, minus `task` — the user supplies tasks interactively. Everything else
    resolves from config exactly as it does for `run`.
    """
    # Same UnboundLocalError guard as run() (step-07 plan §5.2): a failure before the Logger is
    # constructed must propagate as itself, not as a NameError from the finally clause.
    logger = None
    try:
        cfg = config()  # loads .env; populates os.environ
        task_class = Player
        task_settings = cfg.tasks(task_class.task_name())
        if system is None:
            system = task_class.system_prompt(
                task_settings,
                user_prompts_dir=cfg.user_prompts_dir,
                default_prompts_dir=Config.PROMPTS_DIR,
            )
        if model is None:
            model = task_class.model(task_settings)
        if backend is None:
            backend = task_class.provider(task_settings)
        if api_key is None:
            api_key = {
                "anthropic": lambda: os.environ.get("ANTHROPIC_API_KEY"),
                "openai": lambda: os.environ.get("OPENAI_API_KEY"),
                "gemini": lambda: os.environ.get("GEMINI_API_KEY"),
                "ollama_cloud": lambda: os.environ.get("OLLAMA_API_KEY"),
            }.get(backend, lambda: None)()

        ctx = Context(task=task_class, system=system)
        registry = Registry(ctx)

        if block:
            block(RunDSL(registry))

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
        effective_max_iterations = task_class.max_iterations(task_settings)
        effective_max_output_tokens = max_output_tokens or task_class.max_output_tokens(task_settings)
        logger = Logger(
            log=log,
            snapshot={
                "task": task_class.task_name(),
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )

        Repl(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
            config_dir=cfg.dir,
            provider=backend,
            model=model,
            version=VERSION,
            api_key=api_key,
        ).start()
    except KeyboardInterrupt:
        # Ruby's `rescue Interrupt`. Ctrl-C leaves the REPL gracefully rather than dumping a
        # traceback over the session.
        print("\nInterrupted.")
    finally:
        if logger is not None:
            logger.close()


__all__ = [
    "VERSION",
    "Agent",
    "ApiError",
    "Client",
    "Config",
    "Context",
    "Logger",
    "Message",
    "Player",
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
    "quiet",
    "repl",
    "run",
]
