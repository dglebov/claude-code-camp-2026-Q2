import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boukensha import Config, Context, Player, Registry, UnknownToolError

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
)

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)


# Notice that we now register the tools through the registry instead of directly on the context
# as in the previous step. They are still attached to the context, which is why we pass it in
# when we initialize the registry.
#
# Ruby passes the implementation as a trailing block (`do |direction:| ... end`). Python has no
# block syntax, so `registry.tool` returns a decorator and the function below is the block.
@registry.tool(
    "move",
    description="Move the player in a direction (north, south, east, west, up, down)",
    parameters={"direction": {"type": "string"}},
)
def move(*, direction):
    return f"You move {direction} into a torch-lit corridor."


@registry.tool(
    "shout",
    description="Shout a message so everyone in the zone can hear it",
    parameters={"message": {"type": "string"}},
)
def shout(*, message):
    return message.upper()


print("=== BOUKENSHA Step 2: Tool Registry ===")
print()
print(f"Config:  {config}")
print(f"Context: {ctx}")
print("Tools:")
for tool in ctx.tools.values():
    print(f"  {tool}")
print()

# Here we are mimicking what the agent would do when it needs to call a tool from the registry.
# We are still missing the actual code that would decide when to call the registry for a tool.
print("Dispatching 'shout' with message='dragon spotted'...")
result = registry.dispatch("shout", {"message": "dragon spotted"})
print(f"Result: {result}")
print()

print("Dispatching 'move' with direction='north'...")
result = registry.dispatch("move", {"direction": "north"})
print(f"Result: {result}")
print()

try:
    registry.dispatch("flee")
except UnknownToolError as e:
    print(f"UnknownToolError caught: {e}")
