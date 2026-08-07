"""Port of `ruby/12_context/lib/boukensha/models.rb`.

Static model → capability table.

`context_window` is a known *model* fact — the physical input ceiling — not a value the user sets.
The agent looks it up from its configured model id; the user never configures it in settings.yaml.
Unknown models fall back to a conservative default so an unrecognised id cannot silently assume a
huge window and let the conversation run past what the provider will accept.

Ruby exposes this as a module with a `TABLE` constant and a module function. Python has no
separate constant namespace, so both are module level and read the same at the call site:
`Models.context_window(model)` in Ruby, `models.context_window(model)` here.
"""

TABLE = {
    "claude-opus-4-8": {"context_window": 200_000},
    "claude-sonnet-4-6": {"context_window": 200_000},
    "claude-haiku-4-5": {"context_window": 200_000},
}

DEFAULT_CONTEXT_WINDOW = 32_000


def context_window(model):
    """The model's input ceiling, or DEFAULT_CONTEXT_WINDOW for an unknown id.

    Ruby's `TABLE.dig(model.to_s, :context_window) || DEFAULT_CONTEXT_WINDOW` coerces the argument
    with to_s, so nil becomes "" and misses the table rather than raising. `str(model)` does the
    same for None here — deliberate, because an unconfigured model must degrade to the
    conservative default rather than blowing up at startup.
    """
    entry = TABLE.get(str(model))
    if not entry:
        return DEFAULT_CONTEXT_WINDOW

    return entry.get("context_window") or DEFAULT_CONTEXT_WINDOW
