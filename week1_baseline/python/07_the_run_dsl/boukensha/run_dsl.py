"""Port of `ruby/07_the_run_dsl/lib/boukensha/run_dsl.rb`.

The object a `run` block is handed. It exposes only `tool`, keeping the DSL surface
intentionally small.

**This is the one place the two trees deliberately diverge.** Ruby writes:

    RunDSL.new(registry).instance_eval(&block)

`instance_eval` rebinds `self` inside the caller's block, so a bare `tool "..."` resolves to
`RunDSL#tool`. Python has no supported equivalent — a function's name resolution is fixed at
compile time, and every workaround (rewriting `__globals__`, `exec` against a namespace, frame
inspection) is fragile and breaks tooling. So the block takes the DSL as an argument instead:

    def register(dsl):
        @dsl.tool("read_file", description="...", parameters={...})
        def read_file(*, path):
            ...

    boukensha.run(task="...", block=register)

The containment Ruby gets from rebinding `self`, Python gets from the block only ever receiving
this object. See `docs/plans/python_port/07_the_run_dsl.md` §5.1.
"""


class RunDSL:
    def __init__(self, registry):
        self._registry = registry

    def tool(self, name, *, description, parameters=None):
        # Ruby captures the implementation as a trailing block; Python takes the decorated
        # function, matching `Registry.tool`, which this delegates to unchanged.
        return self._registry.tool(name, description=description, parameters=parameters)
