require_relative "errors"

module Boukensha
  class Registry
    def initialize(context)
      @context = context
    end

    # `required:` defaults to nil, which Tool#required_keys reads as "every
    # parameter" — the behaviour every built-in tool relies on. Pass an explicit
    # list when some parameters are optional, as MCP-discovered tools do.
    def tool(name, description:, parameters: {}, required: nil, &block)
      tool = Tool.new(name.to_s, description, parameters, block, required)
      @context.register_tool(tool)
      tool
    end

    def registered?(name)
      @context.tools.key?(name.to_s)
    end

    def dispatch(name, args = {})
      tool = @context.tools[name.to_s]
      raise UnknownToolError, "No tool registered as '#{name}'" unless tool
      tool.block.call(**args.transform_keys(&:to_sym))
    end
  end
end