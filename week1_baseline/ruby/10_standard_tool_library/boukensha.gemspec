require_relative "lib/boukensha/version"

Gem::Specification.new do |spec|
  spec.name        = "boukensha"
  spec.version     = Boukensha::VERSION
  spec.summary     = "BOUKENSHA — a tiny teaching framework for coding harnesses"
  spec.description = "Step-by-step coding harness framework. " \
                     "Set BOUKENSHA_PATH to load a specific lesson step, " \
                     "or run with defaults to use the bundled release."
  spec.authors     = ["Andrew Brown"]
  spec.email       = ["andrew@exampro.co"]
  spec.license     = "MIT"

  spec.required_ruby_version = ">= 3.0"

  # The library, the executable, and the default prompts. prompts/ has to ship: Config::PROMPTS_DIR
  # resolves inside the gem, so without it an installed gem has no system prompt at all.
  spec.files = Dir["lib/**/*.rb"] + Dir["prompts/**/*"] + ["bin/boukensha", "README.md"]

  spec.bindir      = "bin"
  spec.executables = ["boukensha"]

  # MUD session management and CircleMUD command primitives.
  spec.add_dependency "mud_manager", "~> 0.1"

  # net/http and json are stdlib. Users supply their own ANTHROPIC_API_KEY.
end
