"""Port of `ruby/06_the_logger/lib/boukensha/backends/base.rb`.

The shared backend contract. Two jobs:

1. **Model validation.** Each backend owns a table of the models it supports and refuses to
   initialize on anything else, so a typo in `settings.yaml` fails immediately with a clear
   message instead of becoming a confusing 400 from the provider.
2. **Model metadata.** Context window, token pricing, and how usage is measured.

Serialization itself lives in the subclasses — every provider disagrees about it.
"""

from ..errors import UnsupportedModelError


class Base:
    MODELS = None

    @classmethod
    def backend_name(cls):
        # Ruby's `name` on the class yields "Boukensha::Backends::Anthropic". Kept literally so
        # the error text matches the Ruby tree, as `Config.__str__` already does for `#<Boukensha::…>`.
        return f"Boukensha::Backends::{cls.__name__}"

    @classmethod
    def models(cls):
        # Ruby rescues the NameError from `const_get(:MODELS)`. Both forms see an inherited
        # constant, and the base class defines none.
        if cls.MODELS is None:
            raise NotImplementedError(f"{cls.backend_name()} must define MODELS")
        return cls.MODELS

    @classmethod
    def model_info_for(cls, model):
        # Ruby has both `self.model_info(model)` and an instance `model_info`. Python cannot bind
        # one name to both, so the class-level lookup is `model_info_for`.
        return cls.models().get(str(model))

    @classmethod
    def validate_model(cls, model):
        model = str(model)
        if cls.model_info_for(model):
            return model

        supported = ", ".join(sorted(cls.models()))
        # Ruby's `model.inspect` renders double quotes; Python's repr() would render single ones.
        raise UnsupportedModelError(
            f'{cls.backend_name()} does not support model "{model}". Supported models: {supported}'
        )

    @property
    def model_info(self):
        return self._model_info

    @property
    def context_window(self):
        # Ruby uses `fetch`, which raises when the key is missing. `[...]` does the same.
        return self._model_info["context_window"]

    @property
    def input_token_cost_per_million(self):
        return self._model_info["cost_per_million"]["input"]

    @property
    def output_token_cost_per_million(self):
        return self._model_info["cost_per_million"]["output"]

    @property
    def usage_unit(self):
        return self._model_info["usage_unit"]

    @property
    def usage_level(self):
        # Ruby's `model_info[:usage_level]` yields nil when absent — not an error, unlike `fetch`.
        return self._model_info.get("usage_level")

    def estimate_cost(self, *, input_tokens, output_tokens):
        input_cost = self.input_token_cost_per_million
        output_cost = self.output_token_cost_per_million
        # Ruby guards with `unless input_cost && output_cost`, where 0.0 is TRUTHY. Every local
        # Ollama model prices at 0.0, so a literal `if not input_cost` would wrongly return None
        # for all of them. Only a genuine nil/None means "pricing unknown".
        if input_cost is None or output_cost is None:
            return None

        return ((input_tokens * input_cost) + (output_tokens * output_cost)) / 1_000_000.0

    def _configure_model(self, model):
        self._model = self.validate_model(model)
        self._model_info = self.model_info_for(self._model)

    @property
    def model(self):
        return self._model
