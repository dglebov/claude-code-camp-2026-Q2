require "json"

require_relative "tool_table"
require_relative "daemon_client"

module MudManager
  # MCP server over stdio — a *shim*, deliberately.
  #
  # MCP's stdio transport makes the server a child of the host, so a server that
  # owned the session would lose it every time the agent restarted: a fresh
  # 7-step login and a visible disconnect/reconnect in-game, every run, which is
  # exactly when a student iterates fastest.
  #
  # So this process owns nothing. It translates JSON-RPC into daemon requests
  # and back. Restart the agent as often as you like; the character stays in
  # the world. (This is option (b) from the exploration doc §3.)
  #
  # Credentials arrive as environment variables from the host's `mcp_servers:`
  # config block — MUD_HOST, MUD_PORT, MUD_USERNAME, MUD_PASSWORD.
  class McpServer
    PROTOCOL_VERSION = "2024-11-05".freeze
    SERVER_INFO = { "name" => "mud-manager", "version" => "0.1.0" }.freeze

    def initialize(input: $stdin, output: $stdout, client: DaemonClient.new, env: ENV)
      @in     = input
      @out    = output
      @client = client
      @env    = env
    end

    def run
      # Line-buffered: the host is waiting on each response and a full buffer
      # would deadlock the handshake.
      @out.sync = true

      while (line = @in.gets)
        line = line.strip
        next if line.empty?

        begin
          message = JSON.parse(line)
        rescue JSON::ParserError => e
          respond(nil, error: { "code" => -32700, "message" => "Parse error: #{e.message}" })
          next
        end

        dispatch(message)
      end
    end

    # ---- JSON-RPC ----------------------------------------------------------

    private

    def dispatch(message)
      id     = message["id"]
      method = message["method"]

      # Notifications have no id and must not be answered at all.
      notification = !message.key?("id")

      result =
        case method
        when "initialize"                then initialize_result
        when "notifications/initialized" then nil
        when "ping"                      then {}
        when "tools/list"                then { "tools" => ToolTable.mcp_tools }
        when "tools/call"                then call_tool(message["params"] || {})
        else
          return if notification

          return respond(id, error: {
            "code" => -32601, "message" => "Method not found: #{method}"
          })
        end

      return if notification

      respond(id, result: result)
    rescue StandardError => e
      return if !message.key?("id")

      respond(message["id"], error: { "code" => -32603, "message" => "#{e.class}: #{e.message}" })
    end

    def initialize_result
      {
        "protocolVersion" => PROTOCOL_VERSION,
        "capabilities"    => { "tools" => {} },
        "serverInfo"      => SERVER_INFO
      }
    end

    def respond(id, result: nil, error: nil)
      payload = { "jsonrpc" => "2.0", "id" => id }
      if error
        payload["error"] = error
      else
        payload["result"] = result || {}
      end
      @out.puts(JSON.generate(payload))
    end

    # ---- tools -------------------------------------------------------------

    # MCP reports tool failures inside a successful result with isError:true,
    # not as a JSON-RPC error. A protocol-level error would suggest the *call*
    # was malformed; "you can't wield a corpse" is a normal outcome the model
    # should read and react to.
    def call_tool(params)
      name = params["name"]
      args = params["arguments"] || {}
      session = args["session"] || @env["MUD_SESSION"] || "default"

      reply =
        case name
        when "mud_connect"    then connect(args, session)
        when "mud_disconnect" then @client.request({ "op" => "close", "session" => session })
        when "mud_status"     then @client.request({ "op" => "sessions" })
        else
          unless ToolTable.gameplay_tool?(name)
            return text_result("Unknown tool: #{name}", error: true)
          end

          send_gameplay(name, args, session)
        end

      format_reply(name, reply)
    rescue ArgumentError => e
      # Raised by Primitives when an enum or required argument is wrong. This is
      # the validation the tool schema is supposed to prevent reaching — but a
      # model can still send a bad value, and it should see why.
      text_result("Invalid arguments for #{name}: #{e.message}", error: true)
    rescue DaemonClient::Error => e
      text_result("MUD daemon unavailable: #{e.message}", error: true)
    end

    def connect(args, session)
      @client.request({
        "op"       => "open",
        "session"  => session,
        "host"     => args["host"]     || @env["MUD_HOST"],
        "port"     => args["port"]     || @env["MUD_PORT"],
        "username" => args["username"] || @env["MUD_USERNAME"],
        "password" => args["password"] || @env["MUD_PASSWORD"]
      }.compact)
    end

    def send_gameplay(name, args, session)
      reply = @client.request({
        "op" => "send", "session" => session, "tool" => name, "args" => args
      })

      # Auto-connect on first use: a model that calls `look` before
      # `mud_connect` gets the sensible thing rather than a lecture — but only
      # when credentials are configured, otherwise it needs to be told.
      if !reply["ok"] && reply["error"].to_s.include?("no such session") && @env["MUD_USERNAME"]
        opened = connect(args, session)
        return opened unless opened["ok"]

        reply = @client.request({
          "op" => "send", "session" => session, "tool" => name, "args" => args
        })
      end

      reply
    end

    def format_reply(name, reply)
      return text_result(reply["error"].to_s, error: true) unless reply["ok"]

      if reply.key?("sessions")
        list = reply["sessions"]
        return text_result("No MUD sessions open.") if list.empty?

        lines = list.map do |s|
          "#{s['name']}: #{s['open'] ? 'connected' : 'disconnected'} " \
            "(#{s['host']}:#{s['port']} as #{s['username']})"
        end
        return text_result(lines.join("\n"))
      end

      body = reply["output"].to_s
      # Surfaced, not hidden: a reconnect silently drops everything said while
      # the socket was down, and an agent that doesn't know will misread the room.
      body = "[session reconnected]\n#{body}" if reply["reconnected"]
      text_result(body)
    end

    def text_result(text, error: false)
      { "content" => [{ "type" => "text", "text" => text }], "isError" => error }
    end
  end
end
