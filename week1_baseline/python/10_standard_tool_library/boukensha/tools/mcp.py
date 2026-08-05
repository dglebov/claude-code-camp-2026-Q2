"""Port of `ruby/10_standard_tool_library/lib/boukensha/tools/mcp.rb`.

Bridges an MCP server's tools into the Registry — the seam that makes adding a capability a
config edit rather than a code change.

For the Python tree this is not merely convenient, it is the *only* route to the MUD:
`Tools::Mud` wraps a Ruby gem and has no Python counterpart (plan §5.1). Everything the Ruby
tree gets from a built-in module, this tree gets from a server.
"""

import sys

from ..mcp.client import Client


def register(registry, *, name, command, args=None, env=None, prefix=None, required=True):
    """Register every tool a server advertises. Returns the started client, or None.

    prefix:   namespace tool names client-side (mud_look vs look). Purely a local rename; the
              server is still called by its own name.
    required: False downgrades a failed start to a warning instead of killing the run — useful
              when the MUD is down but the filesystem tools would still be worth having.
    """
    client = Client(name=name, command=command, args=args, env=env)
    try:
        client.start()
        for descriptor in client.tools():
            _register_one(registry, client, descriptor, prefix)
        return client
    except Exception as error:
        if required is not False:
            raise
        # stderr, not the warnings module: this is operator output, and warnings deduplicates by
        # default, which would hide a second failing server.
        print(
            f"[boukensha] MCP server {name!r} unavailable, continuing without it: {error}",
            file=sys.stderr,
        )
        client.close()
        return None


def register_all(registry, servers):
    """Start every server named in config. Returns the clients, so the caller can close them."""
    clients = []
    for cfg in servers or []:
        cfg = dict(cfg or {})
        command = cfg.get("command")
        if not command:
            continue

        client = register(
            registry,
            name=cfg.get("name") or command,
            command=command,
            args=cfg.get("args") or [],
            env=cfg.get("env") or {},
            prefix=cfg.get("prefix"),
            required=cfg.get("required", True),
        )
        if client is not None:
            clients.append(client)

    return clients


def _register_one(registry, client, descriptor, prefix):
    remote_name = descriptor.get("name")
    local_name = f"{prefix}_{remote_name}" if prefix else remote_name

    if registry.registered(local_name):
        # Silently clobbering would make one server's tool shadow another's with no signal — the
        # failure surfaces as the wrong thing happening, which is nearly impossible to trace back
        # to here.
        raise ValueError(
            f"MCP tool name collision: {local_name!r} is already registered. "
            "Set a `prefix:` on one of the servers in settings.yaml."
        )

    schema = descriptor.get("inputSchema") or {}
    properties = schema.get("properties") or {}
    required = schema.get("required") or []

    def handler(**args):
        return client.call_tool(remote_name, {str(k): v for k, v in args.items()})

    # Call form, not decorator form: a discovered tool has no `def` to decorate (plan §5.3).
    registry.tool(
        local_name,
        description=str(descriptor.get("description") or ""),
        parameters=dict(properties),
        required=list(required),
    )(handler)
