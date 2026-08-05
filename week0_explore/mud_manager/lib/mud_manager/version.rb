module MudManager
  # Single source for the version. The gemspec reads it, and McpServer reports
  # it in serverInfo during the MCP handshake — a hardcoded copy in either place
  # goes stale on the next bump and then lies to every client that asks.
  VERSION = "0.2.0".freeze
end
