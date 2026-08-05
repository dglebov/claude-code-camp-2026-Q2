import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boukensha

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

# Step 10 — A Standard Tool Library (MCP host)
#
# The Ruby step reaches the MUD through Boukensha::Tools::Mud, which is `require "mud_manager"`.
# There is no Python equivalent of a Ruby gem, so this tree reaches the MUD the language-neutral
# way: an MCP server declared in settings.yaml under mcp_servers:.
#
#   mcp_servers:
#     - name: mud
#       command: mud-manager
#       args: ["--mcp"]
#       required: false
#       env: { MUD_HOST: localhost, MUD_PORT: "4000", MUD_USERNAME: …, MUD_PASSWORD: … }
#
# That is the whole point of the MCP layer, and this file is the proof: no MUD code below.

cfg = boukensha.config()
print(f"Config: {cfg}")
print(f"API key set? {os.environ.get('ANTHROPIC_API_KEY') is not None}")

servers = cfg.mcp_servers()
if servers:
    print(f"MCP servers: {', '.join(s['name'] for s in servers)}")
else:
    print("MCP servers: none configured — see week1_baseline/mcp/settings.example.yaml")
print()

# working_dir roots the built-in filesystem and shell tools. The MUD tools, if any, arrive from
# the MCP server instead.
result = boukensha.run(
    task=(
        "List the files in the working directory, then read this example and tell me in one "
        "sentence how this step reaches the MUD."
    ),
    working_dir=str(Path(__file__).resolve().parent.parent),
)

print()
print("=== FINAL RESPONSE ===")
print(result)
