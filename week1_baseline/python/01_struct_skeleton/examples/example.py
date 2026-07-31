import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boukensha import Config, Context, Player, Tool

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
# Step 01 ships no default prompts, so only the user override dir is consulted. With no
# .boukensha/prompts/player/system.md present this resolves to None — same as Ruby.
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
)

ctx = Context(
    task=Player,
    system=system_prompt,
)

ctx.register_tool(
    Tool(
        "move",
        "Move the player in a direction (north, south, east, west, up, down)",
        {"direction": {"type": "string", "description": "The direction to move"}},
        lambda direction: f"You move {direction} into a torch-lit corridor.",
    )
)

ctx.add_message("user", "Explore north and tell me what you find.")
ctx.add_message("assistant", "Sure, let me head north and take a look.")

print("=== Boukensha Step 1: Struct Skeleton ===")
print()
print(f"Config:   {config}")
print(f"Context:  {ctx}")
print(f"Tool:     {ctx.tools['move']}")
print("Messages:")
for message in ctx.messages:
    print(f"  {message}")
