require "socket"
require "json"

require_relative "daemon"

module MudManager
  # Thin client for the daemon's UNIX socket. Used by the CLI and by the MCP
  # stdio shim — both are short-lived processes that must not own the session.
  #
  # `autostart:` spawns a detached daemon if none is listening. That is what
  # makes the student experience "just run it": nobody has to remember to start
  # a background process first.
  class DaemonClient
    class Error < StandardError; end

    def initialize(socket_path: Daemon.socket_path, autostart: true)
      @socket_path = socket_path
      @autostart   = autostart
    end

    def request(payload)
      ensure_daemon!
      sock = UNIXSocket.new(@socket_path)
      sock.puts(JSON.generate(payload))
      line = sock.gets
      raise Error, "daemon closed the connection without replying" if line.nil?

      JSON.parse(line)
    rescue Errno::ENOENT, Errno::ECONNREFUSED => e
      raise Error, "cannot reach daemon at #{@socket_path}: #{e.message}"
    ensure
      sock&.close rescue nil
    end

    def running?
      UNIXSocket.new(@socket_path).close
      true
    rescue StandardError
      false
    end

    # Spawn a detached daemon and wait for it to answer a ping.
    def start_daemon!(timeout: 5.0)
      exe = File.expand_path("../../bin/mud-manager", __dir__)
      # Detached so the daemon outlives whichever short-lived client spawned it
      # — the entire point of the design. Output goes nowhere by default; use
      # `mud-manager daemon` in the foreground to see it.
      Process.spawn(
        RbConfig.ruby, exe, "daemon",
        { out: File::NULL, err: File::NULL, in: File::NULL, pgroup: true }
      ).then { |pid| Process.detach(pid) }

      deadline = monotime + timeout
      sleep 0.05 until running? || monotime > deadline
      raise Error, "daemon did not come up within #{timeout}s" unless running?

      true
    end

    private

    def ensure_daemon!
      return if running?
      raise Error, "daemon is not running at #{@socket_path}" unless @autostart

      start_daemon!
    end

    def monotime = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  end
end
