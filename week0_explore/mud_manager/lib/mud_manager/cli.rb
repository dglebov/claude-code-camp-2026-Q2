require "json"

require_relative "daemon"
require_relative "daemon_client"
require_relative "mcp_server"
require_relative "tool_table"

module MudManager
  # Command-line front-end over the same daemon the MCP server uses.
  #
  # Two audiences:
  #   * us, debugging — `mud-manager send look` beats hand-writing JSON-RPC
  #   * a bootcamper whose language has no comfortable MCP library yet, who can
  #     still shell out from the standard library with zero dependencies
  #
  # Both front-ends talk to one daemon, so a session opened by the CLI is
  # visible to the MCP server and vice versa.
  class CLI
    USAGE = <<~USAGE
      mud-manager — MUD session manager

      Session-owning process:
        mud-manager daemon              run the daemon in the foreground
        mud-manager --mcp               MCP server over stdio (for agent hosts)

      Client commands (auto-start the daemon if needed):
        mud-manager connect [--session NAME] [--host H] [--port P] \\
                            [--user U] [--password P]
        mud-manager send [--session NAME] <line...>     send a raw line
        mud-manager tool [--session NAME] <name> [k=v...]
        mud-manager sessions
        mud-manager disconnect [--session NAME]
        mud-manager tools [--json]      list the tool surface
        mud-manager stop                shut the daemon down

      Environment:
        MUD_HOST MUD_PORT MUD_USERNAME MUD_PASSWORD MUD_SESSION
        MUD_MANAGER_SOCKET   override the daemon socket path
    USAGE

    def initialize(argv, out: $stdout, err: $stderr, env: ENV)
      @argv = argv.dup
      @out  = out
      @err  = err
      @env  = env
    end

    # Returns a process exit status.
    def run
      return run_mcp if @argv.include?("--mcp")

      command = @argv.shift
      case command
      when nil, "-h", "--help", "help" then @out.puts(USAGE); 0
      when "daemon"     then run_daemon
      when "connect"    then run_connect
      when "send"       then run_send
      when "tool"       then run_tool
      when "sessions"   then run_sessions
      when "disconnect" then run_disconnect
      when "tools"      then run_tools
      when "stop"       then run_stop
      else
        @err.puts("unknown command: #{command}\n\n#{USAGE}")
        2
      end
    rescue DaemonClient::Error => e
      @err.puts("mud-manager: #{e.message}")
      1
    end

    private

    def run_mcp
      McpServer.new.run
      0
    end

    def run_daemon
      Daemon.new(logger: @err).start
      0
    end

    def run_connect
      opts = flags
      reply = client.request({
        "op"       => "open",
        "session"  => session_name(opts),
        "host"     => opts["host"]     || @env["MUD_HOST"],
        "port"     => opts["port"]     || @env["MUD_PORT"],
        "username" => opts["user"]     || @env["MUD_USERNAME"],
        "password" => opts["password"] || @env["MUD_PASSWORD"]
      }.compact)
      emit(reply)
    end

    def run_send
      opts = flags
      line = @argv.join(" ")
      if line.strip.empty?
        @err.puts("mud-manager send: nothing to send")
        return 2
      end
      emit(client.request({ "op" => "raw", "session" => session_name(opts), "line" => line }))
    end

    # `mud-manager tool move direction=north`
    def run_tool
      opts = flags
      name = @argv.shift
      unless name
        @err.puts("mud-manager tool: needs a tool name")
        return 2
      end

      args = {}
      @argv.each do |pair|
        k, v = pair.split("=", 2)
        next unless v

        args[k] = v.match?(/\A-?\d+\z/) ? v.to_i : v
      end

      emit(client.request({ "op" => "send", "session" => session_name(opts),
                            "tool" => name, "args" => args }))
    end

    def run_sessions
      reply = client.request({ "op" => "sessions" })
      return emit(reply) unless reply["ok"]

      if reply["sessions"].empty?
        @out.puts("no sessions")
      else
        reply["sessions"].each do |s|
          @out.puts(format("%-12s %-12s %s:%s as %s", s["name"],
                           s["open"] ? "connected" : "disconnected",
                           s["host"], s["port"], s["username"]))
        end
      end
      0
    end

    def run_disconnect
      emit(client.request({ "op" => "close", "session" => session_name(flags) }))
    end

    def run_tools
      if @argv.include?("--json")
        @out.puts(JSON.pretty_generate(ToolTable.mcp_tools))
      else
        ToolTable.mcp_tools.each do |t|
          required = (t.dig("inputSchema", "required") || []).join(", ")
          @out.puts(format("%-16s %s", t["name"], required.empty? ? "" : "(#{required})"))
        end
      end
      0
    end

    def run_stop
      return 0.tap { @out.puts("daemon not running") } unless client(autostart: false).running?

      emit(client(autostart: false).request({ "op" => "shutdown" }))
    end

    # ---- helpers -----------------------------------------------------------

    def client(autostart: true)
      @client ||= {}
      @client[autostart] ||= DaemonClient.new(autostart: autostart)
    end

    def session_name(opts) = opts["session"] || @env["MUD_SESSION"] || "default"

    # Pull leading --key value pairs off @argv, leaving positional args behind.
    def flags
      found = {}
      while @argv.first&.start_with?("--")
        key = @argv.shift.sub(/\A--/, "")
        found[key] = @argv.shift
      end
      found
    end

    def emit(reply)
      if reply["ok"]
        text = reply["output"].to_s
        @out.puts("[session reconnected]") if reply["reconnected"]
        @out.puts(text) unless text.empty?
        0
      else
        @err.puts("mud-manager: #{reply['error']}")
        1
      end
    end
  end
end
