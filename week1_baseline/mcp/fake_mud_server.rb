#!/usr/bin/env ruby
# frozen_string_literal: true
#
# A stub CircleMUD, just real enough to exercise MudManager end to end without
# a live game or a real character.
#
# It speaks the parts Session actually depends on:
#   * the login dance — name prompt, password prompt, Welcome, menu
#   * a "> " prompt after every command, which is the sentinel
#     Session#read_until_prompt waits for
#   * telnet IAC negotiation bytes, so the IAC stripper is exercised rather
#     than assumed
#
# Usage:
#   ruby fake_mud_server.rb [port]        # prints the port it bound to
#
# Binding to port 0 lets the OS pick a free port, so parallel test runs and a
# real MUD already sitting on 4000 don't collide.

require "socket"

port = (ARGV[0] || 0).to_i
server = TCPServer.new("127.0.0.1", port)
actual = server.addr[1]
$stdout.puts(actual)
$stdout.flush

IAC  = 255.chr
WILL = 251.chr
ECHO = 1.chr

ROOM = <<~ROOM.chomp
  The Temple Of Midgaard
    You are in the southern end of the temple hall in the Temple of Midgaard.
  A retired Priest sits here, contemplating.
  Exits: N E S W
ROOM

loop do
  client = server.accept
  Thread.new(client) do |sock|
    begin
      # Some CircleMUDs negotiate echo around the password prompt. Send the
      # bytes unprompted so the stripper has to cope with them mid-stream.
      sock.write("#{IAC}#{WILL}#{ECHO}")
      sock.write("\r\nBy what name do you wish to be known? ")

      name = sock.gets.to_s.strip
      sock.write("Password: ")
      password = sock.gets.to_s.strip

      if password == "wrong"
        sock.write("Wrong password.\r\n")
        sock.close
        next
      end

      sock.write("\r\nWelcome, #{name}!\r\n")
      sock.gets                      # blank line for the menu
      sock.gets                      # "1" to enter the world
      sock.write("\r\n#{ROOM}\r\n\r\n> ")

      while (line = sock.gets)
        cmd = line.strip
        body =
          case cmd
          when "look", ""       then ROOM
          when "score"          then "You are 1 years old.\r\nHit points: 20(20)  Mana: 100(100)"
          when /\Anorth|east|south|west|up|down\z/ then "You walk #{cmd}.\r\n#{ROOM}"
          when /\Asay (.*)\z/   then "You say, '#{Regexp.last_match(1)}'"
          when /\Ahit (.*)\z/   then "You hit #{Regexp.last_match(1)} hard."
          when "quit"           then sock.write("Goodbye.\r\n"); sock.close; break
          else "Huh?!?"
          end
        sock.write("#{body}\r\n\r\n> ")
      end
    rescue StandardError
      # a client vanishing is normal in these tests
    ensure
      sock.close rescue nil
    end
  end
end
