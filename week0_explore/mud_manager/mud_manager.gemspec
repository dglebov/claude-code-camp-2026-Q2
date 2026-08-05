Gem::Specification.new do |spec|
  spec.name        = "mud_manager"
  spec.version     = "0.1.0"
  spec.summary     = "MudManager — CircleMUD session management and command primitives"
  spec.description = "Provides MudManager::Session (a long-lived telnet connection with " \
                     "background buffering and IAC stripping), MudManager::Primitives " \
                     "(a stateless library of typed CircleMUD command builders), and a " \
                     "session-owning daemon exposed over MCP (stdio) and a CLI, so agent " \
                     "harnesses in any language can drive a MUD without reimplementing telnet."
  spec.authors     = ["Andrew Brown"]
  spec.email       = ["andrew@exampro.co"]
  spec.license     = "MIT"

  spec.required_ruby_version = ">= 3.0"

  spec.files = Dir["lib/**/*.rb"] + ["bin/mud-manager", "README.md"]

  spec.bindir      = "bin"
  spec.executables = ["mud-manager"]

  # No external dependencies — socket, json and thread are stdlib.
end
