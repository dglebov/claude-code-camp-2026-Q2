"""Port of `ruby/04_api_client/lib/boukensha/registry.rb`.

The Registry has two jobs: storing tools and dispatching them when asked.

The agent never calls a tool directly. It emits a structured request (a name and a dict of
arguments) and the Registry looks the tool up and runs it.

Note that tools are still *stored* on the Context — `Registry` holds a reference and writes
through to it. That mirrors the Ruby original. (`week1_baseline/ITERATIONS.md` flags the
arrangement as something that ought to move onto the Registry; changing it here would break
parity with the Ruby tree, so it is left alone.)
"""

from .errors import UnknownToolError
from .tool import Tool


class Registry:
    def __init__(self, context):
        self._context = context

    def tool(self, name, *, description, parameters=None):
        """Register a tool. Used as a decorator on the function that implements it.

            @registry.tool("move", description="...", parameters={"direction": {...}})
            def move(*, direction):
                ...

        Ruby captures the implementation as a trailing block:

            registry.tool("move", description: "...", parameters: {...}) do |direction:|
              ...
            end

        Python has no block syntax, so `tool` returns a decorator instead. Two consequences worth
        knowing when diffing against the Ruby: Ruby's `tool` returns the Tool it built, whereas
        this returns a decorator — and after the decorator runs, the name stays bound to the
        original function, not to the Tool. Neither return value is used by the example.

        `parameters` defaults to None rather than `{}`: Ruby's `parameters: {}` allocates a fresh
        hash per call, but a Python default is evaluated once at definition time and would be
        shared by every tool registered without explicit parameters.
        """

        def decorator(block):
            self._context.register_tool(Tool(str(name), description, parameters or {}, block))
            return block

        return decorator

    def dispatch(self, name, args=None):
        """Look up a tool by name and call it with the provided args."""
        tool = self._context.tools.get(str(name))
        if not tool:
            # Interpolate the original `name`, not str(name), so it renders as it was passed.
            raise UnknownToolError(f"No tool registered as '{name}'")
        # Ruby needs `args.transform_keys(&:to_sym)` here — the API hands back string-keyed JSON
        # while a Ruby block expects symbol keys. Python keyword arguments *are* strings, so the
        # translation is a no-op. The seam is kept deliberately: it is the one place every tool
        # call passes through, and later steps feed it straight from an API response.
        #
        # One real difference: Ruby's `to_sym` accepts any string, while `**` in Python rejects a
        # key that is not a valid identifier unless the callable takes **kwargs.
        return tool.block(**(args or {}))
