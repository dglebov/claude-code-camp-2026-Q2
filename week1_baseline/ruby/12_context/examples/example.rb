#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Step 12 — Context Window Management (one-shot demo)
#
# The non-interactive counterpart to the TUI: one task run to completion, so the same tools and
# the same context-window accounting are exercised without taking over the screen.
#
# For the TUI itself:
#   bin/boukensha              # charm TUI, with the ctx N/M (P%) readout
#   bin/boukensha --no-tui     # plain terminal REPL
#
# MUD gameplay tools are served by the `mud-manager --mcp` server declared under mcp_servers: in
# settings.yaml — there is no built-in MUD tool module as of step 10. Config is found by walking
# up from the working directory to the nearest .boukensha; BOUKENSHA_DIR overrides that.
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
