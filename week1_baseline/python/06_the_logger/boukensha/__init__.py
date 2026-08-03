"""Port of `ruby/06_the_logger/lib/boukensha.rb` — the top-level aggregator.

Step 06 adds module-level state to this file, mirroring Ruby's `@config` / `@debug` / `@quiet`
module instance variables. It is a departure from five steps of dependency injection — `Agent`
still takes every collaborator by constructor argument — and only `Logger` reads it.

Ruby's `self.config` is a method and Python's is a function, but call sites read `config()` in
both. `debug?` and `quiet?` become `is_debug()` and `is_quiet()`: `?` is not legal in a Python
identifier, and the bare names are taken by the setters.
"""

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
from .tasks.player import Player
from .tool import Tool

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


__all__ = [
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
]
