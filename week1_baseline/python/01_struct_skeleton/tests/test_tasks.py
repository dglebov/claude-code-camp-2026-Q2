import pytest
from boukensha.tasks import Base, Player

SETTINGS = {
    "provider": "anthropic",
    "model": "claude-sonnet-5",
    "prompt_override": {"system": True},
}


@pytest.fixture
def default_prompts(tmp_path):
    """The library's shipped prompts dir: system.md sits at the top, with no per-task subfolder."""
    path = tmp_path / "default_prompts"
    path.mkdir()
    (path / "system.md").write_text("DEFAULT PROMPT\n", encoding="utf-8")
    return path


@pytest.fixture
def user_prompts(tmp_path):
    """The user's override dir: prompts are nested under <task>/."""
    path = tmp_path / "user_prompts"
    (path / "player").mkdir(parents=True)
    return path


# ---------- task_name --------------------------------------------------------


def test_base_task_name_raises():
    with pytest.raises(NotImplementedError):
        Base.task_name()


def test_player_task_name():
    assert Player.task_name() == "player"


# ---------- provider / model -------------------------------------------------


def test_provider_and_model_are_read():
    assert Player.provider(SETTINGS) == "anthropic"
    assert Player.model(SETTINGS) == "claude-sonnet-5"


def test_missing_provider_raises_with_settings_yaml_message():
    with pytest.raises(ValueError, match=r"tasks\.player\.provider is required in settings\.yaml"):
        Player.provider({"model": "x"})


def test_missing_model_raises_with_settings_yaml_message():
    with pytest.raises(ValueError, match=r"tasks\.player\.model is required in settings\.yaml"):
        Player.model({"provider": "x"})


def test_none_settings_raises_valueerror_not_typeerror():
    """A missing tasks: block yields None. Surface the useful message, not an attribute error."""
    with pytest.raises(ValueError):
        Player.provider(None)


# ---------- prompt_override --------------------------------------------------


def test_prompt_override_true():
    assert Player.prompt_override(SETTINGS, "system") is True


def test_prompt_override_defaults_to_system():
    assert Player.prompt_override(SETTINGS) is True


def test_prompt_override_false_when_flag_absent():
    assert Player.prompt_override({"prompt_override": {}}) is False


def test_prompt_override_false_when_block_absent():
    assert Player.prompt_override({}) is False


def test_prompt_override_false_when_block_is_not_a_dict():
    assert Player.prompt_override({"prompt_override": "yes"}) is False


def test_prompt_override_requires_real_boolean():
    """Ruby compares `== true`, so a truthy string must not enable the override."""
    assert Player.prompt_override({"prompt_override": {"system": "true"}}) is False


# ---------- prompt resolution ------------------------------------------------


def test_default_prompt_has_no_per_task_subfolder(default_prompts):
    result = Player.system_prompt({}, default_prompts_dir=str(default_prompts))

    assert result == "DEFAULT PROMPT"


def test_override_used_when_flag_set_and_file_exists(default_prompts, user_prompts):
    (user_prompts / "player" / "system.md").write_text("OVERRIDE PROMPT\n", encoding="utf-8")

    result = Player.system_prompt(
        SETTINGS,
        user_prompts_dir=str(user_prompts),
        default_prompts_dir=str(default_prompts),
    )

    assert result == "OVERRIDE PROMPT"


def test_override_flag_set_but_file_missing_falls_back_to_default(default_prompts, user_prompts):
    result = Player.system_prompt(
        SETTINGS,
        user_prompts_dir=str(user_prompts),
        default_prompts_dir=str(default_prompts),
    )

    assert result == "DEFAULT PROMPT"


def test_override_file_present_but_flag_off_uses_default(default_prompts, user_prompts):
    (user_prompts / "player" / "system.md").write_text("OVERRIDE PROMPT\n", encoding="utf-8")

    result = Player.system_prompt(
        {"prompt_override": {"system": False}},
        user_prompts_dir=str(user_prompts),
        default_prompts_dir=str(default_prompts),
    )

    assert result == "DEFAULT PROMPT"


def test_prompt_returns_none_when_no_dirs_given():
    assert Player.system_prompt(SETTINGS) is None


def test_prompt_returns_none_when_default_file_missing(tmp_path):
    assert Player.system_prompt({}, default_prompts_dir=str(tmp_path)) is None


def test_prompt_content_is_stripped(default_prompts):
    (default_prompts / "system.md").write_text("\n\n  padded  \n\n", encoding="utf-8")

    assert Player.system_prompt({}, default_prompts_dir=str(default_prompts)) == "padded"


def test_named_prompt_other_than_system(default_prompts):
    (default_prompts / "summary.md").write_text("SUMMARY\n", encoding="utf-8")

    assert Player.prompt({}, "summary", default_prompts_dir=str(default_prompts)) == "SUMMARY"
