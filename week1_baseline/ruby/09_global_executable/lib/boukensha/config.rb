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

    # Default prompts shipped alongside this step.
    PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze

    attr_reader :dir, :settings

    def initialize
      @dir = resolve_dir
      load_env
      @settings = load_settings
    end

    # ---------- tasks -----------------------------------------------------

    # With no argument: returns the full tasks hash from settings.yaml.
    # With a name: returns that task's settings hash, e.g. tasks(:player).
    def tasks(name = nil)
      all = dig(:tasks) || {}
      name ? (all[name.to_s] || all[name.to_sym]) : all
    end

    # The user's prompts directory for task prompt overrides.
    def user_prompts_dir
      File.join(@dir, "prompts")
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

    # ---------- low-level helpers -----------------------------------------

    # Fetch a nested key path from settings, e.g. dig(:mud, :host)
    def dig(*keys)
      keys.reduce(@settings) do |node, key|
        case node
        when Hash then node[key.to_s] || node[key.to_sym]
        else nil
        end
      end
    end

    def to_s
      "#<Boukensha::Config dir=#{@dir} tasks=#{tasks.keys.join(',')}>"
    end

    def inspect = to_s

    private

    def resolve_dir
      # 1. Explicit override
      return Pathname.new(ENV["BOUKENSHA_DIR"]).expand_path.to_s if ENV["BOUKENSHA_DIR"]

      # 2. The nearest .boukensha at or above the working directory. Walking up rather than
      #    checking only Dir.pwd (step 08's form) means `boukensha` works from anywhere inside a
      #    project, not just its root — a global command is usually run from a subdirectory.
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
  end
end
