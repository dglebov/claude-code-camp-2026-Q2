require_relative "../mcp/client"

module Boukensha
  module Tools
    # Bridges an MCP server's tools into the Registry.
    #
    # This is what makes "add a capability" a config edit rather than a code
    # change: declare a server in settings.yaml and its tools appear to the
    # agent alongside the built-ins.
    module Mcp
      # Registers every tool a server advertises.
      #
      # prefix:   namespace tool names client-side (mud_look vs look). Purely a
      #           local rename; the server is still called by its own name.
      # required: false — a server that fails to start becomes a warning rather
      #           than killing the run. Useful when the MUD is down but the
      #           filesystem tools would still be worth having.
      #
      # Returns the started client so the caller can close it.
      def self.register(registry, name:, command:, args: [], env: {}, prefix: nil, required: true)
        client = Boukensha::Mcp::Client.new(name: name, command: command, args: args, env: env)
        client.start

        client.tools.each do |descriptor|
          register_one(registry, client, descriptor, prefix)
        end

        client
      rescue StandardError => e
        raise unless required == false

        warn "[boukensha] MCP server #{name.inspect} unavailable, continuing without it: #{e.message}"
        client&.close
        nil
      end

      # Start every server named in config. Returns the clients, so the caller
      # can close them when the run ends.
      def self.register_all(registry, servers)
        Array(servers).filter_map do |cfg|
          cfg = symbolize(cfg)
          next if cfg[:command].nil? || cfg[:command].to_s.empty?

          register(
            registry,
            name:     cfg[:name] || cfg[:command],
            command:  cfg[:command],
            args:     cfg[:args] || [],
            env:      cfg[:env] || {},
            prefix:   cfg[:prefix],
            required: cfg.fetch(:required, true)
          )
        end
      end

      def self.register_one(registry, client, descriptor, prefix)
        remote_name = descriptor["name"]
        local_name  = prefix ? "#{prefix}_#{remote_name}" : remote_name

        if registry.registered?(local_name)
          # Silently clobbering would make one server's tool shadow another's
          # with no signal — the failure would surface as the wrong thing
          # happening in-game, which is nearly impossible to trace back here.
          raise ArgumentError,
                "MCP tool name collision: #{local_name.inspect} is already registered. " \
                "Set a `prefix:` on one of the servers in settings.yaml."
        end

        schema     = descriptor["inputSchema"] || {}
        properties = schema["properties"] || {}
        required   = schema["required"] || []

        registry.tool(
          local_name,
          description: descriptor["description"].to_s,
          parameters:  symbolize_properties(properties),
          required:    required
        ) do |**args|
          client.call_tool(remote_name, stringify(args))
        end
      end

      def self.symbolize_properties(properties)
        properties.each_with_object({}) do |(pname, spec), out|
          out[pname.to_sym] = (spec || {}).transform_keys(&:to_sym)
        end
      end

      def self.stringify(args)
        args.each_with_object({}) { |(k, v), out| out[k.to_s] = v }
      end

      def self.symbolize(hash)
        (hash || {}).each_with_object({}) { |(k, v), out| out[k.to_sym] = v }
      end

      private_class_method :register_one, :symbolize_properties, :stringify, :symbolize
    end
  end
end
