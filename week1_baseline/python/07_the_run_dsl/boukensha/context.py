"""Port of `ruby/07_the_run_dsl/lib/boukensha/context.rb`.

Holds everything Boukensha needs to make an API call. Nothing lives outside of this.

A plain class rather than a dataclass, mirroring Ruby: unlike Tool and Message it has behaviour
(register_tool / add_message) and its collections must be per-instance.
"""

from .message import Message


class Context:
    def __init__(self, *, task, system=None):
        # Ruby's `initialize(task:, system: nil)` makes `task` a REQUIRED keyword argument.
        # Keyword-only here so Context(Player) fails the same way Ruby's does.
        self.task = task
        self.system = system
        self.messages = []
        self.tools = {}

    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def add_message(self, role, content, tool_use_id=None):
        self.messages.append(Message(role, content, tool_use_id))

    @property
    def tool_count(self):
        return len(self.tools)

    @property
    def turn_count(self):
        return len(self.messages)

    def __str__(self):
        # Ruby's `task&.task_name` yields nil for a nil task, which interpolates as "".
        task_name = "" if self.task is None else self.task.task_name()
        return f"#<Context task={task_name} turns={self.turn_count} tools={self.tool_count}>"

    __repr__ = __str__
