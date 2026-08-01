import json
import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boukensha import Config, Context, Player, PromptBuilder, Registry, backends

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
# PROMPTS_DIR is back in this step, so the system prompt falls back to the shipped
# prompts/system.md when the task has no user override on disk.
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)


@registry.tool("look", description="Look around the current room for details", parameters={})
def look():
    return "A damp stone corridor stretches north. Torches flicker on the walls."


@registry.tool(
    "move",
    description="Move the player in a direction (north, south, east, west, up, down)",
    parameters={"direction": {"type": "string", "description": "The direction to move"}},
)
def move(*, direction):
    return f"You move {direction} into a torch-lit corridor."


ctx.add_message("user", "I just arrived in the dungeon. What's around me, and can you move north?")
ctx.add_message("assistant", "Let me take a look around first.")
ctx.add_message(
    "tool_result",
    "A damp stone corridor stretches north. Torches flicker on the walls.",
    tool_use_id="toolu_01X",
)

print("=== BOUKENSHA Step 3: Prompt Builder ===")
provider = Player.provider(player_settings)
model = Player.model(player_settings)

if provider == "anthropic":
    backend = backends.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], model=model)
elif provider == "ollama":
    backend = backends.Ollama(model=model)
elif provider == "ollama_cloud":
    backend = backends.OllamaCloud(api_key=os.environ["OLLAMA_API_KEY"], model=model)
elif provider == "openai":
    backend = backends.OpenAI(api_key=os.environ["OPENAI_API_KEY"], model=model)
elif provider == "gemini":
    backend = backends.Gemini(api_key=os.environ["GEMINI_API_KEY"], model=model)
else:
    raise ValueError(f"Unsupported provider for player task: {provider}")

builder = PromptBuilder(ctx, backend)

print()
print(f"Config: {config}")
print(f"Provider: {provider}")
print(f"Model: {model}")
# Ruby's JSON.pretty_generate. ensure_ascii=False matters: Ruby emits UTF-8 literally while
# Python would otherwise escape non-ASCII to \uXXXX.
print(json.dumps(builder.to_api_payload(), indent=2, ensure_ascii=False))
