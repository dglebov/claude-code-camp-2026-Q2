"""Port of `ruby/04_api_client/lib/boukensha/tool.rb`.

Ruby uses `Struct.new(:name, :description, :parameters, :block)`. A dataclass is the closest
equivalent: positional construction, mutable fields, value equality.
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
