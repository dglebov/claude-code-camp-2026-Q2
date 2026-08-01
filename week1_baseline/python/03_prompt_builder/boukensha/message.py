"""Port of `ruby/03_prompt_builder/lib/boukensha/message.rb`.

A single unit of conversation. `role` is user / assistant / tool_result; `tool_use_id` pairs a
tool result back to the call that requested it, and is omitted from the output when absent.
"""

from dataclasses import dataclass

# Ruby's `content.to_s[0..60]` is an INCLUSIVE range — 61 characters, not 60.
CONTENT_LIMIT = 61


@dataclass
class Message:
    role: str | None = None
    content: str | None = None
    tool_use_id: str | None = None

    def __str__(self):
        id_tag = f" [{self.tool_use_id}]" if self.tool_use_id else ""
        # Ruby's `.to_s` on nil yields "" — never let None reach the f-string.
        content = "" if self.content is None else str(self.content)
        return f"#<Message role={self.role}{id_tag} content={content[:CONTENT_LIMIT]}...>"

    __repr__ = __str__
