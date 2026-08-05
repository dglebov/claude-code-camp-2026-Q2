"""MCP client package.

Split into a package rather than a module so it mirrors `ruby/.../lib/boukensha/mcp/client.rb`.
"""

from .client import Client

__all__ = ["Client"]
