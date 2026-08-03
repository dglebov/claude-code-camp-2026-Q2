"""Port of `ruby/06_the_logger/lib/boukensha/errors.rb`.

Boukensha-specific error classes. A harness needs explicit error boundaries — an unrecognised
tool name, a model a backend cannot talk to, or a provider that rejected the request should
never silently fail.

Ruby subclasses StandardError, the tier a bare `rescue` catches. Python's equivalent is
`Exception`, not `BaseException` — the latter sits alongside KeyboardInterrupt and SystemExit
and would escape a normal `except Exception` handler.
"""


class UnknownToolError(Exception):
    """Raised when `Registry.dispatch` is given a name that has no registered tool."""


class ApiError(Exception):
    """Raised when a provider request fails: a non-2xx that survived retries, or a transport
    failure that was still failing after the last attempt."""


class UnsupportedModelError(Exception):
    """Raised when a backend is constructed with a model outside its MODELS table."""

