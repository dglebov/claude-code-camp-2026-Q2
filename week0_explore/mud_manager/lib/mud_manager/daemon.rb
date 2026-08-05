require "socket"
require "json"
require "fileutils"
require "thread"

require_relative "session"
require_relative "tool_table"

module MudManager
  # A long-lived process that owns MUD sessions so that short-lived clients
  # don't have to.
  #
  # Why this exists: a MUD connection carries login state, in-world state, and
  # asynchronous chatter that arrives between commands. A client that opened its
  # own connection per command would re-run the 7-step login every time and the
  # character would visibly disconnect and reconnect between actions. So the
  # session must outlive the client, and this is the thing that outlives it.
  #
  # Clients (the CLI, the MCP stdio shim, or anything in any language) speak
  # newline-delimited JSON over a UNIX socket. One request per line, one
  # response per line.
  #
  #   -> {"op":"send","session":"alice","tool":"look","args":{}}
  #   <- {"ok":true,"output":"A damp stone corridor...","reconnected":false}
  #
  # Operations: ping, open, send, raw, sessions, close, shutdown.
  class Daemon
    DEFAULT_SOCKET = File.join(Dir.home, ".mud_manager", "daemon.sock").freeze
    PROTOCOL_VERSION = 1

    # How long to wait for a command's output before giving up and returning
    # whatever arrived. Generous: MUD round-trips are slow and variable.
    DEFAULT_READ_TIMEOUT = 10.0

    def self.socket_path
      ENV["MUD_MANAGER_SOCKET"] || DEFAULT_SOCKET
    end

    def initialize(socket_path: self.class.socket_path, logger: nil)
      @socket_path = socket_path
      @logger      = logger
      @sessions    = {}          # name => {session:, opts:}
      # @mu guards the two hashes ONLY. It must never be held across network
      # I/O: a login is ~7 telnet round trips, and holding a global lock for
      # that long stalls every other player's commands. @locks gives each
      # session its own lock so logins run concurrently, and so two commands on
      # the *same* session can't interleave on one socket and steal each
      # other's output.
      @locks       = {}          # name => Mutex
      @mu          = Mutex.new
      @server      = nil
      @running     = false
    end

    def start
      FileUtils.mkdir_p(File.dirname(@socket_path))
      # A stale socket file from a crashed daemon would make bind fail. Only
      # remove it if nothing is actually listening — otherwise we would be
      # stealing a healthy daemon's socket.
      if File.exist?(@socket_path)
        if listening?
          raise "daemon already running at #{@socket_path}"
        else
          File.unlink(@socket_path)
        end
      end

      @server  = UNIXServer.new(@socket_path)
      File.chmod(0o600, @socket_path)
      @running = true
      log "listening on #{@socket_path}"

      while @running
        begin
          client = @server.accept
        rescue IOError, Errno::EBADF
          break
        end
        Thread.new(client) { |c| serve(c) }
      end
    ensure
      shutdown!
    end

    def listening?
      UNIXSocket.new(@socket_path).close
      true
    rescue StandardError
      false
    end

    def shutdown!
      @running = false
      @mu.synchronize do
        @sessions.each_value { |h| h[:session].close rescue nil }
        @sessions.clear
      end
      @server&.close rescue nil
      File.unlink(@socket_path) if @socket_path && File.exist?(@socket_path)
    rescue StandardError
      nil
    end

    # ---- request handling --------------------------------------------------

    private

    def serve(client)
      while (line = client.gets)
        line = line.strip
        next if line.empty?

        response =
          begin
            handle(JSON.parse(line))
          rescue JSON::ParserError => e
            { "ok" => false, "error" => "malformed request: #{e.message}" }
          rescue StandardError => e
            log "error: #{e.class}: #{e.message}"
            { "ok" => false, "error" => "#{e.class}: #{e.message}" }
          end

        client.puts(JSON.generate(response))
        break if response["shutdown"]
      end
    rescue Errno::EPIPE, IOError
      # client vanished mid-exchange; the session survives, which is the point
    ensure
      client.close rescue nil
    end

    def handle(req)
      case req["op"]
      when "ping"     then { "ok" => true, "protocol" => PROTOCOL_VERSION, "pid" => Process.pid }
      when "open"     then op_open(req)
      when "send"     then op_send(req)
      when "raw"      then op_raw(req)
      when "sessions" then op_sessions
      when "close"    then op_close(req)
      when "shutdown" then op_shutdown
      else { "ok" => false, "error" => "unknown op: #{req['op'].inspect}" }
      end
    end

    def session_name(req) = (req["session"] || "default").to_s

    def op_open(req)
      name = session_name(req)
      opts = {
        host:     req["host"]     || Session::DEFAULT_HOST,
        port:     (req["port"]    || Session::DEFAULT_PORT).to_i,
        username: req["username"],
        password: req["password"]
      }

      lock_for(name).synchronize do
        existing = @mu.synchronize { @sessions[name] }
        if existing && existing[:session].open?
          return { "ok" => true, "session" => name, "already_open" => true,
                   "output" => "session #{name} already connected to #{opts[:host]}:#{opts[:port]}" }
        end

        # Network I/O happens holding only this session's lock.
        session = connect_and_login(opts)
        @mu.synchronize { @sessions[name] = { session: session, opts: opts } }
        { "ok" => true, "session" => name, "already_open" => false,
          "output" => "connected to #{opts[:host]}:#{opts[:port]} as #{opts[:username]}" }
      end
    end

    # Per-session lock, created on demand.
    def lock_for(name)
      @mu.synchronize { @locks[name] ||= Mutex.new }
    end

    def op_send(req)
      name = session_name(req)
      tool = req["tool"]
      line =
        if tool
          ToolTable.build_line(tool, req["args"] || {})
        else
          req["command"].to_s
        end
      dispatch(name, line, timeout: req["timeout"])
    end

    def op_raw(req)
      dispatch(session_name(req), req["line"].to_s, timeout: req["timeout"])
    end

    # Send a line and collect the response, reconnecting first if the socket
    # died while we weren't looking.
    #
    # Reconnection is transparent but NOT silent: `reconnected` comes back in
    # the response so the caller can tell the model its session was rebuilt.
    # A reconnect loses whatever was said while the socket was down, and an
    # agent that believes otherwise will misread the room.
    def dispatch(name, line, timeout: nil)
      entry = @mu.synchronize { @sessions[name] }
      return { "ok" => false, "error" => "no such session: #{name}. Call mud_connect first." } unless entry

      reconnected = false

      # One command at a time per session: a telnet socket has no request ids,
      # so two interleaved sends would let each read steal the other's output.
      # Different sessions still run fully in parallel.
      lock_for(name).synchronize do
        entry = @mu.synchronize { @sessions[name] }
        return { "ok" => false, "error" => "session #{name} disappeared" } unless entry

        unless entry[:session].open?
          opts = entry[:opts]
          return { "ok" => false, "error" => "session #{name} is closed and has no stored credentials" } unless opts[:username]

          entry = entry.merge(session: connect_and_login(opts))
          @mu.synchronize { @sessions[name] = entry }
          reconnected = true
        end

        session = entry[:session]
        session.send_command(line)
        output = session.read_until_prompt(timeout: (timeout || DEFAULT_READ_TIMEOUT).to_f)

        { "ok" => true, "session" => name, "sent" => line,
          "output" => output.to_s, "reconnected" => reconnected }
      end
    rescue Session::Error => e
      { "ok" => false, "error" => "#{e.class.name.split('::').last}: #{e.message}" }
    end

    def op_sessions
      list = @mu.synchronize do
        @sessions.map do |name, h|
          { "name" => name, "open" => h[:session].open?,
            "host" => h[:opts][:host], "port" => h[:opts][:port],
            "username" => h[:opts][:username] }
        end
      end
      { "ok" => true, "sessions" => list }
    end

    def op_close(req)
      name = session_name(req)
      @mu.synchronize do
        entry = @sessions.delete(name)
        return { "ok" => false, "error" => "no such session: #{name}" } unless entry

        entry[:session].close
        { "ok" => true, "output" => "session #{name} closed" }
      end
    end

    def op_shutdown
      @running = false
      { "ok" => true, "output" => "daemon shutting down", "shutdown" => true }
    end

    def connect_and_login(opts)
      session = Session.new(host: opts[:host], port: opts[:port])
      session.open
      session.login(opts[:username], opts[:password]) if opts[:username]
      session
    end

    def log(msg)
      @logger&.puts("[mud-manager daemon] #{msg}")
    end
  end
end
