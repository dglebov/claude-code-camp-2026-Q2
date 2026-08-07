"""Port of `ruby/11_tui/lib/boukensha/tool.rb`.

Ruby uses `Struct.new(:name, :description, :parameters, :block, :required)`. A dataclass is the
closest equivalent: positional construction, mutable fields, value equality.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Ruby's `description.to_s[0..40]` is an INCLUSIVE range — 41 characters, not 40.
DESCRIPTION_LIMIT = 41


def ruby_symbol_list(keys):
    """Render dict keys the way Ruby prints an array of symbols: [:direction], [:a, :b], [].

    Python would print ['direction']; Ruby prints [:direction]. The example output shows this
    form, so it has to be reproduced exactly.
    """
    return "[" + ", ".join(f":{key}" for key in keys) + "]"


@dataclass
class Tool:
    name: str | None = None
    description: str | None = None
    parameters: dict = field(default_factory=dict)
    block: Callable[..., Any] | None = None
    # Must come last: every earlier field has a default, and a field without one could not
    # follow them. Also the position Ruby's Struct puts it in, so the two stay diffable.
    required: list | None = None

    def required_keys(self):
        """Which parameters the model must supply.

        Every built-in tool declares only mandatory parameters, so "all of them" stays the
        default and nothing changes for them. Tools discovered over MCP are different: their
        JSON Schema carries a real `required` list, and optional parameters are common (`look`
        takes an optional target). Without this, every optional parameter would be advertised
        to the model as mandatory.
        """
        keys = self.parameters.keys() if self.required is None else self.required
        return [str(k) for k in keys]

    def __str__(self):
        # Ruby's `.to_s` on nil yields "" — never let None reach the f-string.
        description = "" if self.description is None else str(self.description)
        parameters = self.parameters or {}
        return (
            f"#<Tool name={self.name} "
            f"description={description[:DESCRIPTION_LIMIT]} "
            f"params={ruby_symbol_list(parameters.keys())}>"
        )

    __repr__ = __str__
