"""Port of `ruby/11_tui/lib/boukensha/config.rb`.

PROMPTS_DIR returns in this step, having been dropped in step 01. The library ships a default
`prompts/system.md` again, so `system_prompt` falls back to it when the task's user override is
absent — which is why `Context.system` is populated here for the first time since step 00.
"""

import os

import yaml

from .env_file import load_env_file


class Config:
    # The .boukensha config directory is resolved in this order:
    #   1. BOUKENSHA_DIR environment variable (set before loading .env)
    #   2. The nearest .boukensha directory at or above the working directory
    #   3. ~/.boukensha  (default)
    DEFAULT_DIR = os.path.join(os.path.expanduser("~"), ".boukensha")

    # Default prompts shipped alongside the library code.
    PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

    def __init__(self):
        self.dir = self._resolve_dir()
        self._load_env()
        self.settings = self._load_settings()

    # ---------- tasks -----------------------------------------------------

    def tasks(self, name=None):
        """With no argument: the full tasks dict. With a name: that task's settings dict."""
        all_tasks = self.dig("tasks")
        if all_tasks is None:
            all_tasks = {}
        if name is None:
            return all_tasks
        return all_tasks.get(str(name))

    @property
    def user_prompts_dir(self):
        """The user's prompts directory for task prompt overrides."""
        return os.path.join(self.dir, "prompts")


    # ---------- MUD connection --------------------------------------------
    #
    # Removed in step 06 and restored here, still with no caller. `settings.yaml` carries a `mud`
    # block, but nothing in either tree reads these (step-07 plan §8).

    @property
    def mud_host(self):
        return self._default(self.dig("mud", "host"), "localhost")

    @property
    def mud_port(self):
        return self._default(self.dig("mud", "port"), 4000)

    @property
    def mud_username(self):
        return self.dig("mud", "username")

    @property
    def mud_password(self):
        return self.dig("mud", "password")

    # ---------- low-level helpers -----------------------------------------

    def dig(self, *keys):
        """Fetch a nested key path from settings, e.g. dig("mud", "host")."""
        node = self.settings
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(str(key))
        return node

    def __str__(self):
        return f"#<Boukensha::Config dir={self.dir} tasks={','.join(self.tasks().keys())}>"

    __repr__ = __str__

    # ---------- private ---------------------------------------------------

    @staticmethod
    def _default(value, fallback):
        # Explicit None check, not `or`. Ruby treats 0 and "" as truthy, Python does not, so
        # `value or fallback` would silently discard a configured port of 0.
        return fallback if value is None else value

    def _resolve_dir(self):
        # 1. Explicit override
        raw = os.environ.get("BOUKENSHA_DIR")
        if raw is not None:
            # abspath (not realpath) matches Ruby's File.expand_path, which normalises without
            # resolving symlinks.
            return os.path.abspath(os.path.expanduser(raw))

        # 2. The nearest .boukensha at or above the working directory. Step 08 checked only
        #    Dir.pwd, which found a project's config from its root and silently fell back to
        #    home from any subdirectory — walking up means `boukensha` works from anywhere
        #    inside a project, which matters once it is a globally installed command.
        project_dir = self._find_project_dir(os.path.abspath(os.getcwd()))
        if project_dir:
            return project_dir

        # 3. ~/.boukensha default
        return os.path.abspath(os.path.expanduser(self.DEFAULT_DIR))

    @staticmethod
    def _find_project_dir(start):
        """Ascend to the filesystem root looking for a .boukensha directory.

        os.path.dirname("/") returns "/", so compare before and after to terminate — an
        unconditional loop here hangs the process rather than merely misconfiguring it.
        """
        current = start
        while True:
            candidate = os.path.join(current, ".boukensha")
            if os.path.isdir(candidate):
                return candidate

            parent = os.path.dirname(current)
            if parent == current:
                return None

            current = parent

    # ---------- MCP servers -------------------------------------------------

    def mcp_servers(self):
        """Declared MCP servers: name, command, args, env, prefix, required.

        This is the seam that makes a new capability a config edit instead of a code change.
        For the Python tree it is the ONLY way to reach the MUD: `Tools::Mud` wraps a Ruby gem
        and has no Python counterpart (plan §5.1).
        """
        raw = self.dig("mcp_servers")
        if not raw:
            return []
        if isinstance(raw, list):
            return [self._normalize_server(entry) for entry in raw]
        if isinstance(raw, dict):
            return [self._normalize_server(v, default_name=k) for k, v in raw.items()]
        return []

    @staticmethod
    def _normalize_server(entry, default_name=None):
        """YAML gives string keys and native types; normalise both.

        env values are coerced to str because YAML happily yields integers for a port, and
        subprocess refuses a non-string environment.
        """
        h = dict(entry or {})
        h["name"] = h.get("name") or default_name or h.get("command")
        h["args"] = [str(a) for a in (h.get("args") or [])]
        h["env"] = {str(k): str(v) for k, v in (h.get("env") or {}).items()}
        return h

    def _load_env(self):
        env_file = os.path.join(self.dir, ".env")
        if os.path.exists(env_file):
            load_env_file(env_file)

    def _load_settings(self):
        settings_file = os.path.join(self.dir, "settings.yaml")
        if not os.path.exists(settings_file):
            return {}
        with open(settings_file, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
        # An empty settings.yaml parses to None; coerce to {} as Ruby's `|| {}` does.
        return {} if loaded is None else loaded
