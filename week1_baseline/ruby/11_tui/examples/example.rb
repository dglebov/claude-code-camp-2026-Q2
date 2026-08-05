#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Step 11 — A Terminal UI (one-shot demo)
#
# This is the non-interactive counterpart to the TUI. It runs a single task to
# completion and prints the result, so it exercises the same tool set without
# taking over the screen.
#
# For the TUI itself, run the REPL instead:
#
#   bin/boukensha              # charm TUI
#   bin/boukensha --no-tui     # plain terminal REPL
#
# MUD gameplay tools are served by the `mud-manager --mcp` server declared under
# `mcp_servers:` in settings.yaml — there is no built-in MUD tool module as of
# step 10. Config is found by walking up from the working directory to the
# nearest .boukensha; BOUKENSHA_DIR overrides that.
#
#   ruby examples/example.rb
#   BOUKENSHA_DIR=/path/to/.boukensha ruby examples/example.rb

ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)

$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha"

cfg = Boukensha.config
puts "Config: #{cfg}"
puts "API key set? #{!ENV['ANTHROPIC_API_KEY'].nil?}"
puts

Boukensha.run(
  task: "Connect to the MUD, look at your surroundings, check your score, " \
        "then look at the available exits and tell me what you see.",
  # system/model/api_key all come from config automatically
  working_dir: false   # no filesystem tools needed for MUD play
  # MUD tools arrive from the mcp_servers: block in settings.yaml
)
