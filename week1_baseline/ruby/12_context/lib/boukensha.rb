require_relative "boukensha/version"
require_relative "boukensha/config"

module Boukensha
  @debug  = false
  @quiet  = false
  @config = nil

  def self.config
    @config ||= Config.new
  end

  def self.quiet!
    @quiet = true
  end

  def self.loud!
    @quiet = false
  end

  def self.quiet?
    @quiet
  end

  def self.debug!
    @debug = true
  end

  def self.debug?
    @debug
  end

  # One-shot run: send a single task, get a response, return.
  #
  # working_dir:      roots all tool calls to this directory (default: Dir.pwd).
  #                   Registers Boukensha::Tools::FileSystem (pwd, list_directory,
  #                   read_file, write_file, delete_file, search_files) and
  #                   Boukensha::Tools::Shell (run_command) automatically.
  #                   Pass working_dir: false to opt out entirely.
  #
  # allowed_commands: Array of shell-executable names the agent is allowed to
  #                   run via run_command (e.g. ["ruby", "git"]).
  #                   nil (default) permits everything — useful for demos.
  #                   Pass an empty Array [] to disable run_command entirely.
  #
  # shell_timeout:    Seconds before a run_command is killed (default 30).
  #
  # MUD gameplay tools are not built in. They arrive from the `mud-manager --mcp` server declared
  # under mcp_servers: in settings.yaml, which keeps one session alive across every tool call.
  def self.run(
    task:,
    system:           nil,
    model:            nil,
    backend:          nil,
    api_key:          nil,
    ollama_host:      "http://localhost:11434",
    log:              nil,
    context_window:   nil,
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    &block
  )
    cfg     = config                           # loads .env; populates ENV

    # Step 12 gives provider/model/limits defaults, so an unconfigured run no longer raises — it
    # quietly starts a session with a default model, no MCP servers and no credentials, which is
    # more confusing than a failure. Say so instead. Explicit condition, not a rescue, so nothing
    # else is swallowed.
    if cfg.settings.nil? || cfg.settings.empty?
      warn missing_config_message(cfg.dir)
      return
    end
    system  ||= cfg.system_prompt
    model   ||= cfg.model
    context_window ||= Models.context_window(model)
    backend ||= cfg.provider_type.to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(system: system, context_window: context_window, working_dir: working_dir, compaction_threshold: cfg.agent_compaction_threshold)
    registry = Registry.new(ctx)

    if working_dir
      Tools::FileSystem.register(registry, working_dir: working_dir)
      Tools::Shell.register(registry, working_dir: working_dir,
                            timeout: shell_timeout, allowed_commands: allowed_commands)
    end

    RunDSL.new(registry).instance_eval(&block) if block

    # Tools declared in settings.yaml under mcp_servers:. Started after the DSL block so a
    # collision with a block-registered tool is reported, not hidden. This is the only path to
    # MUD gameplay tools since step 10.
    mcp_clients = Tools::Mcp.register_all(registry, cfg.mcp_servers)

    be = case backend
         when :anthropic    then Backends::Anthropic.new(api_key: api_key, model: model)
         when :openai       then Backends::OpenAI.new(api_key: api_key, model: model)
         when :gemini       then Backends::Gemini.new(api_key: api_key, model: model)
         when :ollama       then Backends::Ollama.new(host: ollama_host, model: model)
         when :ollama_cloud then Backends::OllamaCloud.new(api_key: api_key, model: model)
         else raise ArgumentError, "Unknown backend #{backend.inspect}. Use :anthropic, :openai, :gemini, :ollama, or :ollama_cloud."
         end

    builder = PromptBuilder.new(ctx, be)
    client  = Client.new(builder)
    logger  = Logger.new(log: log, snapshot: {
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      context_window:    context_window,
      model:             model,
      provider:          backend
    })
    agent   = Agent.new(context: ctx, registry: registry, builder: builder, client: client, logger: logger,
                        max_iterations: cfg.agent_max_iterations,
                        max_turn_tokens: cfg.agent_max_turn_tokens,
                        max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens))

    ctx.add_message(:user, task)
    agent.run
  ensure
    logger&.close
    mcp_clients&.each { |c| c&.close }
  end

  # Interactive REPL — see Boukensha.run for full option documentation.
  #
  # tui: true (default) wraps the REPL in a charm-ruby TUI.  Pass tui: false or
  # use the --no-tui CLI flag to fall back to the plain terminal REPL.
  def self.repl(
    system:           nil,
    model:            nil,
    backend:          nil,
    api_key:          nil,
    ollama_host:      "http://localhost:11434",
    log:              nil,
    context_window:   nil,
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    tui:              true,
    &block
  )
    cfg     = config                           # loads .env; populates ENV

    # Step 12 gives provider/model/limits defaults, so an unconfigured run no longer raises — it
    # quietly starts a session with a default model, no MCP servers and no credentials, which is
    # more confusing than a failure. Say so instead. Explicit condition, not a rescue, so nothing
    # else is swallowed.
    if cfg.settings.nil? || cfg.settings.empty?
      warn missing_config_message(cfg.dir)
      return
    end
    system  ||= cfg.system_prompt
    model   ||= cfg.model
    context_window ||= Models.context_window(model)
    backend ||= cfg.provider_type.to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(system: system, context_window: context_window, working_dir: working_dir, compaction_threshold: cfg.agent_compaction_threshold)
    registry = Registry.new(ctx)

    if working_dir
      Tools::FileSystem.register(registry, working_dir: working_dir)
      Tools::Shell.register(registry, working_dir: working_dir,
                            timeout: shell_timeout, allowed_commands: allowed_commands)
    end

    RunDSL.new(registry).instance_eval(&block) if block

    # Tools declared in settings.yaml under mcp_servers:. Started after the DSL block so a
    # collision with a block-registered tool is reported, not hidden. This is the only path to
    # MUD gameplay tools since step 10.
    mcp_clients = Tools::Mcp.register_all(registry, cfg.mcp_servers)

    be = case backend
         when :anthropic    then Backends::Anthropic.new(api_key: api_key, model: model)
         when :openai       then Backends::OpenAI.new(api_key: api_key, model: model)
         when :gemini       then Backends::Gemini.new(api_key: api_key, model: model)
         when :ollama       then Backends::Ollama.new(host: ollama_host, model: model)
         when :ollama_cloud then Backends::OllamaCloud.new(api_key: api_key, model: model)
         else raise ArgumentError, "Unknown backend #{backend.inspect}. Use :anthropic, :openai, :gemini, :ollama, or :ollama_cloud."
         end

    builder = PromptBuilder.new(ctx, be)
    client  = Client.new(builder)
    logger  = Logger.new(log: log, snapshot: {
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      context_window:    context_window,
      model:             model,
      provider:          backend
    })

    repl = Repl.new(
      context:    ctx,
      registry:   registry,
      builder:    builder,
      client:     client,
      logger:     logger,
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      config_dir: cfg.dir,
      provider:   backend,
      model:      model,
      version:    VERSION,
      api_key:    api_key,
    )

    if tui && defined?(Tui)
      Tui.new(repl).start
    else
      repl.start
    end
  rescue Interrupt
    puts "\nInterrupted."
  ensure
    logger&.close
    mcp_clients&.each { |c| c&.close }
  end

  # Says where it looked and how to fix it. Config resolution has three tiers and none of them are
  # visible from a stack trace, so spell all three out.
  def self.missing_config_message(dir)
    <<~MSG
      boukensha: no settings.yaml found.

        looked in: #{dir}/settings.yaml

      Config is resolved in this order:
        1. $BOUKENSHA_DIR, if set
        2. the nearest .boukensha at or above the current directory
        3. ~/.boukensha

      You are most likely running from outside a project. Either cd into one, or:
        BOUKENSHA_DIR=/path/to/.boukensha boukensha
    MSG
  end
  private_class_method :missing_config_message

end

require_relative "boukensha/tool"
require_relative "boukensha/message"
require_relative "boukensha/models"
require_relative "boukensha/context"
require_relative "boukensha/errors"
require_relative "boukensha/registry"
require_relative "boukensha/prompt_builder"
require_relative "boukensha/logger"
require_relative "boukensha/backends/base"
require_relative "boukensha/backends/anthropic"
require_relative "boukensha/backends/gemini"
require_relative "boukensha/backends/ollama"
require_relative "boukensha/backends/ollama_cloud"
require_relative "boukensha/backends/openai"
require_relative "boukensha/client"
require_relative "boukensha/agent"
require_relative "boukensha/run_dsl"
require_relative "boukensha/repl"
require_relative "boukensha/tools/file_system"
require_relative "boukensha/tools/shell"
require_relative "boukensha/mcp/client"
require_relative "boukensha/tools/mcp"

# The TUI is optional. tui.rb requires bubbletea/lipgloss/bubbles at load time, so a tree without
# the charm gems installed would otherwise fail to load boukensha at all — including for the plain
# REPL, which needs none of them. Swallowing LoadError here leaves Tui undefined, and the
# `defined?(Tui)` check in .repl falls back to the terminal REPL.
begin
  require_relative "boukensha/tui"
rescue LoadError => e
  warn "[boukensha] TUI unavailable (#{e.message}); use --no-tui or run `bundle install`." if ENV["BOUKENSHA_DEBUG"]
end