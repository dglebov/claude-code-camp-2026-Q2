require "yaml"
require "dotenv"
require "pathname"

module Boukensha
  class Config
    # The .boukensha config directory is resolved in this order:
    #   1. BOUKENSHA_DIR environment variable (set before loading .env)
    #   2. The nearest .boukensha directory at or above the working directory
    #   3. ~/.boukensha  (default)
    DEFAULT_DIR = File.join(Dir.home, ".boukensha").freeze

    # Default prompts shipped alongside this step. Step 12 loads the system prompt from the
    # CONFIG directory only; without this fallback a project whose .boukensha has no prompts/
    # runs the agent with no system prompt at all, silently.
    PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze

    attr_reader :dir, :settings, :system_prompt

    def initialize
      @dir = resolve_dir
      load_env
      @settings     = load_settings
      @system_prompt = load_system_prompt
    end

    # ---------- provider --------------------------------------------------

    def provider_type
      dig(:tasks, :player, :provider) || "anthropic"
    end

    def model
      dig(:tasks, :player, :model) || "claude-haiku-4-5"
    end

    # ---------- system prompt ---------------------------------------------

    def system_override?
      dig(:system, :override) == true
    end

    # ---------- MCP servers -------------------------------------------------

    # Declared MCP servers, each: name, command, args, env, prefix, required.
    #
    # This is the seam that makes a new capability a config edit instead of a code change —
    # including MUD gameplay, which arrives from the `mud-manager --mcp` server rather than
    # from a built-in tool module.
    def mcp_servers
      raw = dig(:mcp_servers)
      return [] unless raw

      case raw
      when Array then raw.map { |entry| normalize_server(entry) }
      when Hash  then raw.map { |name, entry| normalize_server(entry, default_name: name) }
      else []
      end
    end

    # YAML gives string keys; the rest of the codebase works in symbols. Also coerces env values
    # to strings, since YAML happily yields integers and Process.spawn refuses a non-string
    # environment.
    def normalize_server(entry, default_name: nil)
      h = (entry || {}).each_with_object({}) { |(k, v), out| out[k.to_sym] = v }
      h[:name] ||= default_name || h[:command]
      h[:args] = Array(h[:args]).map(&:to_s)
      h[:env]  = (h[:env] || {}).each_with_object({}) { |(k, v), out| out[k.to_s] = v.to_s }
      h
    end

    # ---------- MUD connection --------------------------------------------

    def mud_host
      dig(:mud, :host) || "localhost"
    end

    def mud_port
      dig(:mud, :port) || 4000
    end

    def mud_username
      dig(:mud, :username)
    end

    def mud_password
      dig(:mud, :password)
    end

    # ---------- agent limits ----------------------------------------------
    # Static per-turn circuit breakers, read where the agent is constructed.
    # A value of 0 or nil means "disabled" (no ceiling) — useful for debugging.

    def agent_max_iterations
      v = dig(:agent, :max_iterations)
      v.nil? ? 25 : Integer(v)
    end

    def agent_max_output_tokens
      v = dig(:agent, :max_output_tokens)
      v.nil? ? 1024 : Integer(v)
    end

    def agent_max_turn_tokens
      v = dig(:agent, :max_turn_tokens)
      v.nil? ? 60_000 : Integer(v)
    end

    def agent_compaction_threshold
      v = dig(:agent, :compaction_threshold)
      v.nil? ? 0.85 : Float(v)
    end

    # ---------- low-level helpers -----------------------------------------

    # Fetch a nested key path from settings, e.g. dig(:provider, :model)
    def dig(*keys)
      keys.reduce(@settings) do |node, key|
        case node
        when Hash then node[key.to_s] || node[key.to_sym]
        else nil
        end
      end
    end

    def to_s
      "#<Boukensha::Config dir=#{@dir} provider=#{provider_type} model=#{model}>"
    end

    def inspect = to_s

    private

    def resolve_dir
      # 1. Explicit override
      return Pathname.new(ENV["BOUKENSHA_DIR"]).expand_path.to_s if ENV["BOUKENSHA_DIR"]

      # 2. The nearest .boukensha at or above the working directory. Walking up rather than
      #    checking only Dir.pwd means `boukensha` works from anywhere inside a project, not
      #    just its root — a global command is usually run from a subdirectory.
      project_dir = find_project_dir(Pathname.new(Dir.pwd).expand_path)
      return project_dir.to_s if project_dir

      # 3. ~/.boukensha default
      Pathname.new(DEFAULT_DIR).expand_path.to_s
    end

    # Ascends to the filesystem root. `Pathname.new("/").parent` returns "/", so compare before
    # and after to terminate — an unconditional loop here hangs the process.
    def find_project_dir(start)
      dir = start
      loop do
        candidate = dir.join(".boukensha")
        return candidate if candidate.directory?

        parent = dir.parent
        return nil if parent == dir

        dir = parent
      end
    end

    def load_env
      env_file = File.join(@dir, ".env")
      if File.exist?(env_file)
        Dotenv.load(env_file)
      end
    end

    def load_settings
      settings_file = File.join(@dir, "settings.yaml")
      if File.exist?(settings_file)
        YAML.safe_load(File.read(settings_file)) || {}
      else
        {}
      end
    end

    # Resolves the system prompt. When the player task opts into a prompt
    # override (tasks.player.prompt_override.system: true), the task-scoped
    # file prompts/player/system.md wins; otherwise (and as a fallback) the
    # flat prompts/system.md is used. Returns nil when neither exists.
    def load_system_prompt
      if dig(:tasks, :player, :prompt_override, :system) == true
        task_file = File.join(@dir, "prompts", "player", "system.md")
        return File.read(task_file).strip if File.exist?(task_file)
      end

      system_file = File.join(@dir, "prompts", "system.md")
      return File.read(system_file).strip if File.exist?(system_file)

      # Fall back to the prompt shipped with this step. Without it a config directory that has no
      # prompts/ leaves system_prompt nil, and the agent runs with no instructions at all — with
      # nothing on screen to say so. Step 11 got this fallback via Tasks::Base; step 12 dropped
      # the task classes, so it belongs here now.
      default_file = File.join(PROMPTS_DIR, "system.md")
      File.exist?(default_file) ? File.read(default_file).strip : nil
    end
  end
end
