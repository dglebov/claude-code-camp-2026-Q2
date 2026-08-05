"""Port of `ruby/10_standard_tool_library/lib/boukensha/prompt_builder.rb`.

Serializes a Context into the exact shape a provider's REST API expects. It owns no format
knowledge itself — every method delegates to the backend it was constructed with.

It does not call the API — `Client` does that. As of step 05 it also runs in reverse:
`parse_response` delegates to the backend to normalize a provider's reply into one common shape,
so `Agent` never has to know which provider it is talking to.
"""


class PromptBuilder:
    def __init__(self, context, backend):
        self._context = context
        self._backend = backend

    @property
    def backend(self):
        # New in step 06: Agent.log_response reads builder.backend to record the provider, model
        # and per-token cost on every response event.
        return self._backend

    def to_messages(self):
        # NOTE: this is broken for three of the five backends, exactly as in Ruby. OpenAI, Ollama
        # and OllamaCloud all declare `to_messages(system, messages)` and raise when called with
        # one argument. Nothing reaches it — `to_api_payload` goes through `to_payload`, which
        # calls the backend's own `to_messages` with both arguments — so the defect is invisible
        # in normal use. Mirrored deliberately rather than fixed, to keep the two trees diffable;
        # `tests/test_prompt_builder.py` pins the behaviour so a later fix is a deliberate change.
        return self._backend.to_messages(self._context.messages)

    def to_tools(self):
        return self._backend.to_tools(self._context.tools)

    def to_api_payload(self, max_output_tokens=1024, tools=None):
        # `tools` overrides the context's tool list when passed. Agent's wind-down call passes
        # [] to disable tools; the backends branch on `is None`, so an empty list survives.
        return self._backend.to_payload(self._context, max_output_tokens=max_output_tokens, tools=tools)

    def parse_response(self, response):
        return self._backend.parse_response(response)

    def headers(self):
        return self._backend.headers()

    def url(self):
        return self._backend.url()
