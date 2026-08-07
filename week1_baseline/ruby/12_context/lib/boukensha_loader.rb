# BoukenshaLoader resolves which step folder to load from, then boots the REPL.
#
# Resolution order:
#   1. BOUKENSHA_PATH environment variable (selects which *step* lib to load)
#   2. ~/.boukensharc  (a file containing a single path)
#   3. The lib/ directory bundled inside this gem (step 10 — the latest release)
#
# Config directory (settings.yaml, .env, system.md) is separate:
#   BOUKENSHA_DIR=~/.boukensha  (default; set to override)
#
# MUD connection details come from the mcp_servers: env block in settings.yaml,
# where they are passed to the `mud-manager --mcp` server. Setting MUD_NAME still
# means "MUD session only" (filesystem tools are dropped), but the host/port/
# password values themselves are no longer read here.
#
# Examples:
#   boukensha                                                              # uses bundled lib + ~/.boukensha
#   boukensha --no-tui                                                     # plain terminal REPL
#   BOUKENSHA_PATH=~/Sites/boukensha/04_api_client boukensha              # loads step 4
#   BOUKENSHA_DIR=~/projects/mybot/.boukensha boukensha                   # custom config dir
#   echo ~/Sites/boukensha/10_standard_tool_library > ~/.boukensharc && boukensha
module BoukenshaLoader
  # Absolute path to this gem's own bundled boukensha lib.
  BUNDLED_LIB = File.expand_path("../boukensha.rb", __FILE__)

  def self.resolve
    # 1. Env var wins.
    if ENV["BOUKENSHA_PATH"]
      dir  = File.expand_path(ENV["BOUKENSHA_PATH"])
      main = File.join(dir, "lib", "boukensha.rb")
      return main if File.exist?(main)

      abort <<~MSG
        boukensha: BOUKENSHA_PATH is set but no lib/boukensha.rb found at:
               #{dir}
               Make sure BOUKENSHA_PATH points to a step folder, e.g.:
               BOUKENSHA_PATH=~/Sites/boukensha/07_the_repl_loop boukensha
      MSG
    end

    # 2. ~/.boukensharc
    rc = File.expand_path("~/.boukensharc")
    if File.exist?(rc)
      dir  = File.read(rc).strip
      unless dir.empty?
        main = File.join(File.expand_path(dir), "lib", "boukensha.rb")
        return main if File.exist?(main)

        abort <<~MSG
          boukensha: ~/.boukensharc points to #{dir}
                 but no lib/boukensha.rb was found there.
                 Update ~/.boukensharc or remove it to use the bundled default.
        MSG
      end
    end

    # 3. Bundled default.
    BUNDLED_LIB
  end

  def self.load_and_start_repl
    main = resolve
    step_dir = File.dirname(File.dirname(main))

    puts "[boukensha] loading from: #{step_dir}" if ENV["BOUKENSHA_DEBUG"]

    require main

    unless Boukensha.respond_to?(:repl)
      abort <<~MSG
        boukensha: the step at #{step_dir}
               does not support the interactive REPL (added in step 7).
               Run its examples directly, e.g.:
                 ruby #{step_dir}/examples/*.rb
               Or point BOUKENSHA_PATH at step 7 or later.
      MSG
    end

    # --no-tui falls back to the plain terminal REPL (no charm gems needed).
    no_tui = ARGV.delete("--no-tui")

    repl_opts = { tui: !no_tui }

    # MUD_NAME is set: play the MUD and nothing else, so drop the filesystem tools.
    #
    # The legacy MUD_HOST/PORT/NAME/PASSWORD values are NOT forwarded as a `mud:`
    # option any more — since step 10 there is no built-in MUD tool module to
    # receive them, and passing `mud:` to .repl raised ArgumentError (a latent
    # bug carried in step 10's copy of this file). MUD connection details now
    # live in the mcp_servers: env block in settings.yaml.
    if ENV["MUD_NAME"]
      repl_opts[:working_dir] = false
    end

    Boukensha.repl(**repl_opts)
  end
end
