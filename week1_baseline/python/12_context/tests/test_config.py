import os

import yaml
from boukensha import Config

SETTINGS = {
    "tasks": {"player": {"provider": "anthropic", "model": "claude-sonnet-5"}},
    "mud": {"host": "mud.example", "port": 5000, "username": "hero", "password": "s3cret"},
}


def write_settings(config_dir, data):
    (config_dir / "settings.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


# ---------- directory resolution --------------------------------------------


def test_boukensha_dir_env_var_is_honoured(config_dir):
    assert Config().dir == os.path.abspath(str(config_dir))


def test_falls_back_to_default_dir_when_env_unset(tmp_path, monkeypatch):
    fallback = tmp_path / "home" / ".boukensha"
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    monkeypatch.setattr(Config, "DEFAULT_DIR", str(fallback))
    # chdir somewhere with no .boukensha above it. Without this the walk-up tier added in this
    # step finds the repo's own .boukensha and tier 3 is never reached — which is correct
    # behaviour, and exactly why this test has to isolate itself.
    monkeypatch.chdir(tmp_path)

    assert Config().dir == os.path.abspath(str(fallback))


def test_dir_expands_user_and_normalises(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path / "a" / ".." / "b"))

    assert Config().dir == os.path.abspath(str(tmp_path / "b"))


# ---------- settings loading -------------------------------------------------


def test_missing_settings_file_yields_empty_dict(config_dir):
    assert Config().settings == {}


def test_empty_settings_file_yields_empty_dict(config_dir):
    (config_dir / "settings.yaml").write_text("", encoding="utf-8")

    assert Config().settings == {}


def test_settings_yml_extension_is_ignored(config_dir):
    """The contract is settings.yaml. A .yml file must not be picked up."""
    (config_dir / "settings.yml").write_text(yaml.safe_dump(SETTINGS), encoding="utf-8")

    assert Config().settings == {}


def test_settings_yaml_is_parsed(config_dir):
    write_settings(config_dir, SETTINGS)

    assert Config().settings == SETTINGS


# ---------- .env loading -----------------------------------------------------


def test_env_file_is_loaded(config_dir, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (config_dir / ".env").write_text('ANTHROPIC_API_KEY="from-env-file"\n', encoding="utf-8")

    Config()

    assert os.environ["ANTHROPIC_API_KEY"] == "from-env-file"


def test_env_file_does_not_override_existing_var(config_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "already-set")
    (config_dir / ".env").write_text('ANTHROPIC_API_KEY="from-env-file"\n', encoding="utf-8")

    Config()

    assert os.environ["ANTHROPIC_API_KEY"] == "already-set"


def test_env_file_handles_comments_blanks_and_export(config_dir, monkeypatch):
    for key in ("PLAIN", "QUOTED", "EXPORTED"):
        monkeypatch.delenv(key, raising=False)
    (config_dir / ".env").write_text(
        "# a comment\n\nPLAIN=bare\nQUOTED='single'\nexport EXPORTED=yes\n",
        encoding="utf-8",
    )

    Config()

    assert os.environ["PLAIN"] == "bare"
    assert os.environ["QUOTED"] == "single"
    assert os.environ["EXPORTED"] == "yes"


def test_missing_env_file_is_not_an_error(config_dir):
    assert Config().settings == {}


# ---------- dig --------------------------------------------------------------


def test_dig_walks_nested_keys(config_dir):
    write_settings(config_dir, SETTINGS)

    assert Config().dig("mud", "host") == "mud.example"


def test_dig_returns_none_for_missing_key(config_dir):
    write_settings(config_dir, SETTINGS)

    assert Config().dig("mud", "nope") is None


def test_dig_returns_none_through_non_dict_node(config_dir):
    write_settings(config_dir, SETTINGS)

    # "host" is a string, so digging past it must yield None rather than raising.
    assert Config().dig("mud", "host", "deeper") is None


# ---------- tasks ------------------------------------------------------------


def test_user_prompts_dir_is_under_config_dir(config_dir):
    assert Config().user_prompts_dir == os.path.join(os.path.abspath(str(config_dir)), "prompts")


def test_prompts_dir_constant_points_at_shipped_prompts():
    """PROMPTS_DIR returns in step 03, after being dropped in step 01."""
    assert os.path.isfile(os.path.join(Config.PROMPTS_DIR, "system.md"))


def test_provider_and_model_read_from_tasks_player(config_dir):
    """The task CLASSES are gone in step 12; the settings KEYS are unchanged."""
    (config_dir / "settings.yaml").write_text(
        "tasks:\n  player:\n    provider: openai\n    model: gpt-5.4-mini\n"
    )
    cfg = Config()
    assert cfg.provider_type() == "openai"
    assert cfg.model() == "gpt-5.4-mini"


def test_provider_and_model_fall_back_to_defaults(config_dir):
    (config_dir / "settings.yaml").write_text("mud:\n  host: localhost\n")
    cfg = Config()
    assert cfg.provider_type() == "anthropic"
    assert cfg.model() == "claude-haiku-4-5"


def test_agent_limits_have_documented_defaults(config_dir):
    (config_dir / "settings.yaml").write_text("mud:\n  host: localhost\n")
    cfg = Config()
    assert cfg.agent_max_iterations() == 25
    assert cfg.agent_max_output_tokens() == 1024
    assert cfg.agent_max_turn_tokens() == 60_000
    assert cfg.agent_compaction_threshold() == 0.85


def test_agent_limits_read_from_the_agent_block(config_dir):
    (config_dir / "settings.yaml").write_text(
        "agent:\n  max_iterations: 3\n  max_turn_tokens: 500\n  compaction_threshold: 0.5\n"
    )
    cfg = Config()
    assert cfg.agent_max_iterations() == 3
    assert cfg.agent_max_turn_tokens() == 500
    assert cfg.agent_compaction_threshold() == 0.5


def test_str_matches_ruby_format(config_dir):
    write_settings(config_dir, SETTINGS)
    config = Config()

    assert str(config) == (
        f"#<Boukensha::Config dir={config.dir} "
        f"provider={config.provider_type()} model={config.model()}>"
    )
    assert repr(config) == str(config)


# ---------- MUD accessors ----------------------------------------------------


def test_mud_accessors_read_settings(config_dir):
    write_settings(config_dir, SETTINGS)
    config = Config()

    assert config.mud_host == "mud.example"
    assert config.mud_port == 5000
    assert config.mud_username == "hero"
    assert config.mud_password == "s3cret"


def test_mud_defaults_when_absent(config_dir):
    config = Config()

    assert config.mud_host == "localhost"
    assert config.mud_port == 4000
    assert config.mud_username is None
    assert config.mud_password is None


def test_explicit_zero_port_survives(config_dir):
    """Regression guard for the Ruby-vs-Python truthiness gap: 0 must not fall back to 4000."""
    write_settings(config_dir, {"mud": {"port": 0}})

    assert Config().mud_port == 0


def test_explicit_empty_host_survives(config_dir):
    write_settings(config_dir, {"mud": {"host": ""}})

    assert Config().mud_host == ""


# ---------- three-tier directory resolution (new in step 08) -----------------


def test_an_explicit_boukensha_dir_beats_a_cwd_boukensha(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (tmp_path / ".boukensha").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOUKENSHA_DIR", str(explicit))

    assert Config().dir == str(explicit)


def test_a_cwd_boukensha_is_used_when_the_env_var_is_unset(tmp_path, monkeypatch):
    cwd_dir = tmp_path / ".boukensha"
    cwd_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)

    assert Config().dir == str(cwd_dir)


def test_a_cwd_file_named_boukensha_is_not_mistaken_for_a_directory(tmp_path, monkeypatch):
    (tmp_path / ".boukensha").write_text("not a directory", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)

    assert Config().dir == os.path.abspath(os.path.expanduser(Config.DEFAULT_DIR))


def test_the_home_default_is_used_when_there_is_no_cwd_boukensha(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)

    assert Config().dir == os.path.abspath(os.path.expanduser(Config.DEFAULT_DIR))


# ---------- walk-up tier and mcp_servers (new in step 10) --------------------


def test_walk_up_finds_a_boukensha_from_a_deep_subdirectory(tmp_path, monkeypatch):
    """Step 08 checked only the cwd, so a project's config was invisible from any subdirectory."""
    (tmp_path / ".boukensha").mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)

    assert Config().dir == str(tmp_path / ".boukensha")


def test_the_env_var_still_beats_the_walk_up(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (tmp_path / ".boukensha").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOUKENSHA_DIR", str(explicit))

    assert Config().dir == str(explicit)


def test_a_file_named_boukensha_is_not_mistaken_for_a_directory(tmp_path, monkeypatch):
    (tmp_path / ".boukensha").write_text("not a dir", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    monkeypatch.setattr(Config, "DEFAULT_DIR", str(tmp_path / "home" / ".boukensha"))

    assert Config().dir == os.path.abspath(str(tmp_path / "home" / ".boukensha"))


def test_mcp_servers_defaults_to_empty(config_dir):
    write_settings(config_dir, {"tasks": {}})

    assert Config().mcp_servers() == []


def test_mcp_servers_reads_the_list_form(config_dir):
    write_settings(config_dir, {"mcp_servers": [
        {"name": "mud", "command": "mud-manager", "args": ["--mcp"], "env": {"MUD_PORT": 4000}},
    ]})

    servers = Config().mcp_servers()
    assert servers[0]["name"] == "mud"
    assert servers[0]["args"] == ["--mcp"]
    # YAML yields an int for the port; subprocess refuses a non-string environment.
    assert servers[0]["env"] == {"MUD_PORT": "4000"}


def test_mcp_servers_reads_the_mapping_form_and_names_from_the_key(config_dir):
    write_settings(config_dir, {"mcp_servers": {"mud": {"command": "mud-manager"}}})

    assert Config().mcp_servers()[0]["name"] == "mud"


def test_mcp_servers_falls_back_to_the_command_as_a_name(config_dir):
    write_settings(config_dir, {"mcp_servers": [{"command": "mud-manager"}]})

    assert Config().mcp_servers()[0]["name"] == "mud-manager"
