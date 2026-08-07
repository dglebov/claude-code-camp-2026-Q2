"""Port of `ruby/12_context/lib/boukensha/context.rb`.

Holds everything Boukensha needs to make an API call. Nothing lives outside of this.

**New in step 12: the context window is a first-class fact.** The Context now tracks two
independent numbers, and conflating them is the easy mistake:

  * `current_tokens` — how full the window is *right now*, refreshed from each response's
    `input_tokens`. This is about **fitting**, and it is what triggers compaction.
  * `turn_tokens` — cumulative input+output spent across the whole turn. This is about **cost**,
    and it is what the Agent's `max_turn_tokens` ceiling watches.

One can be tiny while the other is huge: a long turn of small calls spends a lot without ever
filling the window.

**`task` is gone.** Step 12 deletes the Tasks class hierarchy in favour of direct Config readers,
so Context no longer carries one. The `tasks.player.*` settings keys still exist — only the
classes went.

A plain class rather than a dataclass, mirroring Ruby: unlike Tool and Message it has behaviour
and its collections must be per-instance.
"""

import math
import os

from .message import Message


class Context:
    def __init__(self, *, system=None, context_window=200_000, working_dir=None,
                 compaction_threshold=0.85):
        self.system = system
        self.context_window = context_window
        # Ruby: `working_dir ? File.expand_path(working_dir) : nil`. False and None both mean
        # "no working directory", which is why this is a truthiness test rather than `is None`.
        self.working_dir = os.path.abspath(working_dir) if working_dir else None
        self.compaction_threshold = compaction_threshold
        self.messages = []
        self.tools = {}
        self.current_tokens = 0
        self.turn_tokens = 0

    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def add_message(self, role, content, tool_use_id=None):
        self.messages.append(Message(role, content, tool_use_id))

    # ---------- token accounting -------------------------------------------

    def update_tokens(self, n):
        """Refresh the known context size from the last response's input_tokens."""
        self.current_tokens = int(n or 0)

    def reset_turn_tokens(self):
        """Zero the cumulative per-turn spend. Called at the top of a turn."""
        self.turn_tokens = 0

    def add_turn_tokens(self, input_tokens, output_tokens):
        """Add one API call's input+output to the cumulative per-turn total.

        This is the spend budget — distinct from current_tokens, which is window pressure.
        """
        self.turn_tokens += int(input_tokens or 0) + int(output_tokens or 0)

    def usage_fraction(self):
        """Fraction of the context window in use (0.0–1.0)."""
        return self.current_tokens / self.context_window if self.context_window > 0 else 0.0

    def usage_pct(self):
        """Integer percentage (0–100).

        Ruby is `(usage_fraction * 100).round`, and Ruby's Float#round rounds halves **away from
        zero** while Python's built-in round() uses banker's rounding (ties to even):

            Ruby:   (0.5).round  => 1
            Python: round(0.5)   => 0

        Left to round(), a context at exactly 70.5% would read 71% in Ruby and 70% here — and 70
        is precisely where the TUI switches to its warning colour. math.floor(x + 0.5) reproduces
        Ruby's rule. Values here are never negative, so the asymmetry of that expression for
        negative inputs does not arise.
        """
        return math.floor(self.usage_fraction() * 100 + 0.5)

    def needs_compaction(self, threshold=None):
        """True when we should compact before the next API call."""
        limit = self.compaction_threshold if threshold is None else threshold
        return self.usage_fraction() >= limit

    # ---------- history ----------------------------------------------------

    def compact_messages(self, target_fraction=0.60):
        """Drop the oldest 40% of messages to free space, keeping at least 2.

        Resets current_tokens to 0; the next API response supplies the real figure. Returns the
        number of messages dropped.

        Ruby names this `compact_messages!` — the bang suffix is not a legal Python identifier,
        and `clear_messages!` already drops it for the same reason.

        The arithmetic is ported exactly:

            drop_count = [(size * 0.40).ceil, size - 2].min
            drop_count = [drop_count, 0].max

        The `size - 2` term is what keeps a short history from being wiped out, and the final
        max(_, 0) is what stops a 0- or 1-message context from producing a negative drop.

        `target_fraction` is accepted and unused, exactly as in Ruby — the 40% is hardcoded in the
        expression above. Carried so the signatures match.
        """
        size = len(self.messages)
        drop_count = min(math.ceil(size * 0.40), size - 2)
        drop_count = max(drop_count, 0)
        self.messages = self.messages[drop_count:]
        self.current_tokens = 0
        return drop_count

    def clear_messages(self):
        """Drop all conversation history, keeping tools and the system prompt intact.

        Used by the REPL's /clear command. Ruby names this `clear_messages!`.
        """
        self.messages = []
        self.current_tokens = 0

    @property
    def tool_count(self):
        return len(self.tools)

    @property
    def turn_count(self):
        return len(self.messages)

    def __str__(self):
        return (
            f"#<Context turns={self.turn_count} tools={self.tool_count} "
            f"window={self.context_window} current={self.current_tokens}>"
        )

    __repr__ = __str__
