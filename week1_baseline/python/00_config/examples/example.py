import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boukensha import Config
from boukensha.tasks import Player

# Override the config directory so the example works from the repo root.
# In real usage a user's ~/.boukensha is picked up automatically.
os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))


def rb_bool(value):
    """Ruby prints true/false; Python prints True/False. Keep output parity with the Ruby run."""
    return "true" if value else "false"


config = Config()
player_settings = config.tasks("player")

system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)
# Ruby's `&.slice(0, 60)` yields nil for a missing prompt, and nil interpolates as "".
prompt_snippet = "" if system_prompt is None else system_prompt[:60]

print("=== Boukensha Step 0: Configuration ===")
print()
print(f"Config dir:     {config.dir}")
print(f"Tasks:          {', '.join(config.tasks().keys())}")
print()
print("-- player task --")
print(f"Provider:       {Player.provider(player_settings)}")
print(f"Model:          {Player.model(player_settings)}")
print(f"Prompt override?{rb_bool(Player.prompt_override(player_settings, 'system'))}")
print(f"System prompt:  {prompt_snippet}...")
print()
print(f"MUD host:       {config.mud_host}:{config.mud_port}")
print(f"MUD user:       {config.mud_username}")
print()
print(f"API key set?    {rb_bool(os.environ.get('ANTHROPIC_API_KEY') is not None)}")
print()
print(config)
