"""Port of `ruby/07_the_run_dsl/lib/boukensha/errors.rb`.

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


class LoopError(Exception):
    """Declared for runaway agents and never raised — `Agent` handles its iteration ceiling by
    winding down. Added in step 05, deleted in step 06, restored here; still with no caller
    anywhere in either tree. Each state change is mirrored in sequence so the two trees stay
    diffable step by step. See the step-07 plan §8."""

