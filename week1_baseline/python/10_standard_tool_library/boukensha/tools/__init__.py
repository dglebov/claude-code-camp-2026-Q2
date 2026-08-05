"""Built-in tool modules.

Mirrors `ruby/10_standard_tool_library/lib/boukensha/tools/` with one deliberate omission:
there is no `mud.py`. The Ruby `Tools::Mud` is `require "mud_manager"` — a Ruby gem with no
Python equivalent — so this tree reaches the MUD through an MCP server instead (plan §5.1).

That omission is the point rather than a shortfall: it is what the MCP layer exists to make
possible, and it leaves this tree in the shape `ITERATIONS.md` §10 describes as the target.
"""

from . import file_system, mcp, shell

__all__ = ["file_system", "mcp", "shell"]
