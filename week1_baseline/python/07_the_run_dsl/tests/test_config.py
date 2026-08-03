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


def test_tasks_returns_all_tasks(config_dir):
    write_settings(config_dir, SETTINGS)

    assert list(Config().tasks().keys()) == ["player"]


def test_tasks_looks_up_a_single_task(config_dir):
    write_settings(config_dir, SETTINGS)

    assert Config().tasks("player")["provider"] == "anthropic"


def test_tasks_returns_none_for_unknown_task(config_dir):
    write_settings(config_dir, SETTINGS)

    assert Config().tasks("wizard") is None


def test_tasks_is_empty_when_settings_missing(config_dir):
    assert Config().tasks() == {}


# ---------- misc -------------------------------------------------------------


def test_user_prompts_dir_is_under_config_dir(config_dir):
    assert Config().user_prompts_dir == os.path.join(os.path.abspath(str(config_dir)), "prompts")


def test_prompts_dir_constant_points_at_shipped_prompts():
    """PROMPTS_DIR returns in step 03, after being dropped in step 01."""
    assert os.path.isfile(os.path.join(Config.PROMPTS_DIR, "system.md"))


def test_str_matches_ruby_format(config_dir):
    write_settings(config_dir, SETTINGS)
    config = Config()

    assert str(config) == f"#<Boukensha::Config dir={config.dir} tasks=player>"
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
