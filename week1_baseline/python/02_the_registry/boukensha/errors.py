"""Port of `ruby/02_the_registry/lib/boukensha/errors.rb`.

Boukensha-specific error classes. A harness needs explicit error boundaries — an unrecognised
tool name should never silently fail.

Ruby subclasses StandardError, the tier a bare `rescue` catches. Python's equivalent is
`Exception`, not `BaseException` — the latter sits alongside KeyboardInterrupt and SystemExit
and would escape a normal `except Exception` handler.
"""


class UnknownToolError(Exception):
    """Raised when `Registry.dispatch` is given a name that has no registered tool."""
