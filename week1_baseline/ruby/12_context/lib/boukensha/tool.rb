module Boukensha
  Tool = Struct.new(:name, :description, :parameters, :block, :required) do
    # Which parameters the model must supply.
    #
    # Every built-in tool declares only required parameters, so the historical
    # behaviour — "all of them" — stays the default and nothing changes for
    # them. Tools discovered over MCP are different: their JSON Schema carries
    # a real `required` list, and optional parameters are common (`look` takes
    # an optional target). Without this, every optional parameter would be
    # advertised to the model as mandatory.
    def required_keys
      (required || parameters.keys).map(&:to_s)
    end

    def to_s
      "#<Tool name=#{name} description=#{description.to_s[0..40]} params=#{parameters.keys}>"
    end
  end
end
