module Boukensha
  # Repl is the interactive session loop.
  #
  # It wraps the same primitives as a single Boukensha.run call, but instead of
  # running once it stays alive: it reads a task from the user, runs the agent,
  # prints the reply, and loops back to the prompt.
  #
  # The Context is shared across every turn so conversation history accumulates
  # naturally — the agent sees the full transcript each time it is called.
  #
  # Built-in commands (not sent to the agent):
  #   /help    print the command list
  #   /quiet   suppress detailed logging
  #   /loud    re-enable logging
  #   /clear   wipe conversation history (tools stay registered)
  #   /exit    leave the REPL
  #   /quit    alias for /exit
  #
  # Step 11 split this class along two seams so something other than a terminal
  # can drive it:
  #
  #   * #on_output  — redirect everything the REPL would print
  #   * #handle_command — command dispatch, extracted from the read loop
  #
  # Tui uses both. Neither changes behaviour when no callback is registered.
  class Repl
    PROMPT = "boukensha> "

    HELP = <<~HELP
      Commands:
        /quiet   suppress logging output
        /loud    re-enable logging output
        /clear   wipe conversation history (tools stay)
        /exit    leave the REPL
        /help    show this message
    HELP

    # Public so a front-end can subscribe to log events and render the status
    # line. Step 10 kept all of these private — nothing outside needed them.
    attr_reader :logger, :context, :model, :version

    def initialize(context:, registry:, builder:, client:, logger:, config_dir: nil, provider: nil, model: nil, version: nil, api_key: nil, task_settings: nil, max_iterations: nil, max_output_tokens: nil)
      @context    = context
      @registry   = registry
      @builder    = builder
      @client     = client
      @logger     = logger
      @task_settings     = task_settings
      @max_iterations    = max_iterations
      @max_output_tokens = max_output_tokens
      @config_dir = config_dir
      @provider   = provider
      @model      = model
      @version    = version
      @api_key    = api_key
      @turn       = 0
      @output_cb  = nil
    end

    # Register a callback that receives every string the REPL would otherwise
    # print to stdout. When set, puts/print are suppressed entirely and all
    # output is routed through the callback instead. Used by Tui.
    def on_output(&block)
      @output_cb = block
    end

    # Public since step 11: Tui prints it into the conversation viewport rather
    # than to stdout.
    def banner
      key_status    = (@api_key.nil? || @api_key.strip.empty?) ? "✗ API key not set" : "✓ API key set"
      provider_line = "#{@provider || "default"} (#{@model || "default"})  #{key_status}"
      config_exists = @config_dir && Dir.exist?(@config_dir)
      config_line   = config_exists ? @config_dir : "#{@config_dir || "(default)"}  ✗ directory not found"
      ver           = @version || "?.?.?"

      <<~BANNER

        ╔══════════════════════════════════════╗
        ║  BOUKENSHA MUD Assistant (v#{ver})#{" " * (9 - ver.length)}║
        ╚══════════════════════════════════════╝
          step:      #{step_line}
          config:    #{config_line}
          provider:  #{provider_line}

          /quiet or /loud   toggle logging
          /clear           reset conversation history
          /exit or /quit    leave the REPL

      BANNER
    end

    # Handle a slash command. Returns :quit, :command, or nil (not a command).
    # Output is routed through the registered on_output callback if present.
    def handle_command(input)
      case input
      when "/exit", "/quit"
        output("Goodbye.")
        :quit
      when "/help"
        output(HELP)
        :command
      when "/quiet"
        Boukensha.quiet!
        output("(logging suppressed — type /loud to re-enable)")
        :command
      when "/loud"
        Boukensha.loud!
        output("(logging enabled)")
        :command
      when "/clear"
        @context.clear_messages!
        @turn = 0
        output("(conversation history cleared)")
        :command
      end
    end

    def run_turn(input)
      @turn += 1
      @logger.turn(n: @turn)

      @context.add_message(:user, input)

      agent  = Agent.new(
        context:  @context,
        registry: @registry,
        builder:  @builder,
        client:   @client,
        logger:   @logger,
        task_settings: @task_settings,
        max_iterations:    @max_iterations,
        max_output_tokens: @max_output_tokens
      )
      result = agent.run

      # Routed through output() rather than puts so the final response is
      # always visible — even when Boukensha.quiet! is active, and even when a
      # front-end has taken over the screen.
      output("")
      output(result)
    rescue LoopError => e
      output("\n[error] #{e.message}")
    rescue ApiError => e
      output("\n[error] API call failed: #{e.message}")
    end

    def start
      output(banner)
      loop do
        # A front-end draws its own prompt; only the bare terminal needs this.
        unless @output_cb
          print PROMPT
          $stdout.flush
        end

        input = $stdin.gets
        break unless input  # EOF / Ctrl-D

        input = input.chomp.strip
        next if input.empty?

        result = handle_command(input)
        break if result == :quit
        next  if result

        run_turn(input)
      end
    end

    private

    # Which copy of the library is actually running.
    #
    # There are a dozen step folders in this repo, each shipping a complete `lib/boukensha`, plus
    # whichever one is installed as a gem. The version string alone does not answer "which code is
    # this?" unless you already know that 0.11.0 means 11_tui — so say it plainly. Derived from
    # this file's own location, which is the only thing that cannot lie about it:
    #
    #   run in-repo      -> 11_tui
    #   installed as gem -> boukensha-0.11.0
    def step_line
      File.basename(File.expand_path("../..", __dir__))
    end

    def output(str)
      if @output_cb
        @output_cb.call(str.to_s)
      else
        puts str
      end
    end
  end
end
