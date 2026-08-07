require "json"
require "open3"

require_relative "../errors"

module Boukensha
  module Mcp
    # A minimal MCP client over the stdio transport.
    #
    # Spawns a server process, performs the initialize handshake, then supports
    # tools/list and tools/call. Server-agnostic: `command` / `args` / `env` is
    # the standard stdio server config, so this talks to the MUD server, a
    # filesystem server, or anything else that speaks MCP.
    #
    # Messages are newline-delimited JSON-RPC 2.0, which is what the stdio
    # transport specifies — no Content-Length framing.
    class Client
      PROTOCOL_VERSION = "2024-11-05".freeze
      CLIENT_INFO = { "name" => "boukensha", "version" => "0.10.0" }.freeze
      DEFAULT_TIMEOUT = 30.0

      class Error < Boukensha::ApiError; end

      attr_reader :name, :server_info

      def initialize(name:, command:, args: [], env: {}, timeout: DEFAULT_TIMEOUT)
        @name    = name.to_s
        @command = command
        @args    = Array(args).map(&:to_s)
        @env     = (env || {}).transform_keys(&:to_s).transform_values(&:to_s)
        @timeout = timeout
        @next_id = 0
        @started = false
      end

      def start
        return self if @started

        @stdin, @stdout, @stderr, @wait = Open3.popen3(@env, @command, *@args)
        @stdin.sync = true
        @started = true

        result = request("initialize", {
          "protocolVersion" => PROTOCOL_VERSION,
          "capabilities"    => {},
          "clientInfo"      => CLIENT_INFO
        })
        @server_info = result["serverInfo"] || {}

        # A notification: no id, and the server must not answer it.
        notify("notifications/initialized")
        self
      rescue Errno::ENOENT => e
        raise Error, "MCP server #{@name.inspect}: command not found: #{@command} (#{e.message})"
      end

      def tools
        request("tools/list")["tools"] || []
      end

      # Returns the text content of the result. MCP reports tool failures as a
      # normal result with isError:true — that is a message for the model to
      # read and react to, not a transport failure, so it comes back as text.
      def call_tool(name, arguments = {})
        result = request("tools/call", { "name" => name, "arguments" => arguments })
        text = Array(result["content"])
               .select { |c| c["type"] == "text" }
               .map { |c| c["text"] }
               .join("\n")
        text = text.empty? ? JSON.generate(result) : text
        result["isError"] ? "ERROR: #{text}" : text
      end

      def close
        return unless @started

        @stdin&.close rescue nil
        @stdout&.close rescue nil
        @stderr&.close rescue nil
        # Give it a moment to exit on its own before insisting.
        unless @wait&.join(1)
          Process.kill("TERM", @wait.pid) rescue nil
        end
        @started = false
      end

      def alive?
        @started && @wait&.alive?
      end

      private

      def request(method, params = nil)
        start unless @started

        id = (@next_id += 1)
        write({ "jsonrpc" => "2.0", "id" => id, "method" => method }.tap { |m|
          m["params"] = params if params
        })

        message = read_until_id(id)
        if (err = message["error"])
          raise Error, "MCP server #{@name.inspect} #{method}: #{err['message']} (code #{err['code']})"
        end

        message["result"] || {}
      end

      def notify(method, params = nil)
        write({ "jsonrpc" => "2.0", "method" => method }.tap { |m|
          m["params"] = params if params
        })
      end

      def write(message)
        @stdin.puts(JSON.generate(message))
      rescue Errno::EPIPE
        raise Error, "MCP server #{@name.inspect} exited: #{drain_stderr}"
      end

      # Skip anything that is not the response we asked for. A server may
      # legitimately interleave notifications, and discarding them here keeps
      # request/response correlation honest rather than assuming strict ordering.
      def read_until_id(id)
        deadline = monotime + @timeout
        loop do
          raise Error, "MCP server #{@name.inspect}: timed out after #{@timeout}s" if monotime > deadline

          line = @stdout.gets
          raise Error, "MCP server #{@name.inspect} closed stdout: #{drain_stderr}" if line.nil?

          line = line.strip
          next if line.empty?

          begin
            message = JSON.parse(line)
          rescue JSON::ParserError
            next # not JSON — server noise on stdout; ignore rather than die
          end

          return message if message["id"] == id
        end
      end

      def drain_stderr
        return "" unless @stderr

        @stderr.read_nonblock(4096).to_s.strip
      rescue StandardError
        ""
      end

      def monotime = Process.clock_gettime(Process::CLOCK_MONOTONIC)
    end
  end
end
