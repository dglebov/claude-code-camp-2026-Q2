"""Tests for `boukensha.run` — the top-level entry point.

Ruby step 07 ships no specs — see `docs/plans/python_port/07_the_run_dsl.md` §7.1.

`run` constructs almost the whole object graph, so this file is effectively an integration suite.
A stub `Client` is the only seam needed; everything else is independently tested elsewhere.
"""

import json
from pathlib import Path
from typing import ClassVar

import boukensha
import pytest
import yaml
from boukensha import backends
from boukensha.errors import ApiError

SETTINGS = {
    "tasks": {
        "player": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "max_iterations": 7,
            "max_output_tokens": 512,
        }
    }
}


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    monkeypatch.setattr(boukensha, "_config", None)
    monkeypatch.setattr(boukensha, "_debug", False)
    monkeypatch.setattr(boukensha, "_quiet", False)


@pytest.fixture
def settings(config_dir, monkeypatch):
    (config_dir / "settings.yaml").write_text(yaml.safe_dump(SETTINGS), encoding="utf-8")
    (config_dir / "prompts" / "player").mkdir(parents=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    return config_dir


class StubClient:
    """Replaces boukensha.Client. Records what it was built with and what it was asked to send."""

    instances: ClassVar[list] = []

    def __init__(self, builder):
        self.builder = builder
        self.calls = []
        self.payloads = []
        StubClient.instances.append(self)

    def call(self, **kwargs):
        self.calls.append(kwargs)
        self.payloads.append(self.builder.to_api_payload(**kwargs))
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "done"}]}


@pytest.fixture
def stub_client(monkeypatch):
    StubClient.instances = []
    monkeypatch.setattr(boukensha, "Client", StubClient)
    return StubClient


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "run.jsonl")


def log_lines(path):
    return [json.loads(ln) for ln in Path(path).read_text().splitlines()]


# ---------- defaults resolve from settings -----------------------------------


def test_run_returns_the_agents_result(settings, stub_client, log_path):
    assert boukensha.run(task="hi", log=log_path) == "done"


def test_the_task_becomes_the_user_message(settings, stub_client, log_path):
    boukensha.run(task="summarise the readme", log=log_path)

    messages = stub_client.instances[0].payloads[0]["messages"]
    assert messages[-1] == {"role": "user", "content": "summarise the readme"}


def test_the_backend_and_model_come_from_settings(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    backend = stub_client.instances[0].builder.backend
    assert isinstance(backend, backends.Anthropic)
    assert backend.model == "claude-sonnet-4-6"


def test_the_bounds_come_from_settings(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    start = log_lines(log_path)[0]
    assert start["max_iterations"] == 7
    assert start["max_output_tokens"] == 512


def test_the_api_key_comes_from_the_environment(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    assert stub_client.instances[0].builder.backend.headers()["x-api-key"] == "sk-from-env"


def test_the_system_prompt_comes_from_the_shipped_default(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    assert stub_client.instances[0].payloads[0]["system"].startswith("You are Boukensha")


# ---------- every default is overridable -------------------------------------


def test_system_can_be_overridden(settings, stub_client, log_path):
    boukensha.run(task="hi", system="custom prompt", log=log_path)

    assert stub_client.instances[0].payloads[0]["system"] == "custom prompt"


def test_model_can_be_overridden(settings, stub_client, log_path):
    boukensha.run(task="hi", model="claude-opus-4-8", log=log_path)

    assert stub_client.instances[0].builder.backend.model == "claude-opus-4-8"


def test_max_output_tokens_can_be_overridden(settings, stub_client, log_path):
    boukensha.run(task="hi", max_output_tokens=64, log=log_path)

    assert stub_client.instances[0].calls[0]["max_output_tokens"] == 64


def test_api_key_can_be_overridden(settings, stub_client, log_path):
    boukensha.run(task="hi", api_key="sk-explicit", log=log_path)

    assert stub_client.instances[0].builder.backend.headers()["x-api-key"] == "sk-explicit"


@pytest.mark.parametrize(
    "backend,cls,model",
    [
        ("anthropic", backends.Anthropic, "claude-sonnet-4-6"),
        ("openai", backends.OpenAI, "gpt-5.4"),
        ("gemini", backends.Gemini, "gemini-3.5-flash"),
        ("ollama", backends.Ollama, "gemma4"),
        ("ollama_cloud", backends.OllamaCloud, "gemma4:31b-cloud"),
    ],
)
def test_every_backend_name_builds_its_class(settings, stub_client, log_path, backend, cls, model):
    boukensha.run(task="hi", backend=backend, model=model, api_key="sk-x", log=log_path)

    assert isinstance(stub_client.instances[0].builder.backend, cls)


def test_ollama_needs_no_api_key(settings, stub_client, log_path, monkeypatch):
    """Ruby's api_key case has no `when :ollama` branch, so it stays nil and Ollama never asks
    for one. Asserted on the backend rather than the result: the stub returns an Anthropic-shaped
    reply, which Ollama's parse_response correctly reads as empty."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    boukensha.run(task="hi", backend="ollama", model="gemma4", log=log_path)

    backend = stub_client.instances[0].builder.backend
    assert isinstance(backend, backends.Ollama)
    assert "Authorization" not in backend.headers()


def test_ollama_host_defaults_and_is_overridable(settings, stub_client, log_path):
    boukensha.run(task="hi", backend="ollama", model="gemma4", log=log_path)
    assert stub_client.instances[0].builder.backend.url().startswith("http://localhost:11434")

    StubClient.instances = []
    boukensha.run(
        task="hi", backend="ollama", model="gemma4", ollama_host="http://elsewhere:1234", log=log_path
    )
    assert stub_client.instances[0].builder.backend.url().startswith("http://elsewhere:1234")


def test_an_unknown_backend_raises(settings, stub_client, log_path):
    with pytest.raises(ValueError, match="Unknown backend"):
        boukensha.run(task="hi", backend="not_a_backend", log=log_path)


# ---------- the block --------------------------------------------------------


def test_the_block_receives_a_run_dsl(settings, stub_client, log_path):
    from boukensha.run_dsl import RunDSL

    seen = []
    boukensha.run(task="hi", block=seen.append, log=log_path)

    assert len(seen) == 1
    assert isinstance(seen[0], RunDSL)


def test_tools_registered_in_the_block_reach_the_payload(settings, stub_client, log_path):
    def register(dsl):
        @dsl.tool("look", description="Look around", parameters={})
        def look():
            return "a corridor"

    # working_dir=False: step 10 auto-registers the filesystem and shell tools whenever a
    # working directory is set, and this test is about the block alone.
    boukensha.run(task="hi", block=register, log=log_path, working_dir=False)

    tools = stub_client.instances[0].payloads[0]["tools"]
    assert [t["name"] for t in tools] == ["look"]


def test_omitting_the_block_is_legal(settings, stub_client, log_path):
    """Ruby guards with `if block`."""
    boukensha.run(task="hi", log=log_path, working_dir=False)

    assert stub_client.instances[0].payloads[0]["tools"] == []


def test_both_the_tools_and_the_user_message_reach_the_first_payload(settings, stub_client, log_path):
    """Ruby registers tools before appending the user message, but the *relative order is not
    observable*: nothing reads the context in between, and the payload is not built until
    `client.call()`. So this pins the outcome — both present on the first request — rather than
    claiming to test an ordering that no behaviour depends on."""

    def register(dsl):
        @dsl.tool("look", description="Look around", parameters={})
        def look():
            return "x"

    boukensha.run(task="hi", block=register, log=log_path)

    payload = stub_client.instances[0].payloads[0]
    assert payload["tools"] != []
    assert payload["messages"][-1]["content"] == "hi"


# ---------- the logger -------------------------------------------------------


def test_the_session_start_snapshot_records_the_effective_config(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    start = log_lines(log_path)[0]
    assert start["phase"] == "session_start"
    assert start["task"] == "player"
    assert start["model"] == "claude-sonnet-4-6"
    assert start["provider"] == "anthropic"
    assert start["max_iterations"] == 7
    assert start["max_output_tokens"] == 512


def test_the_log_path_is_overridable(settings, stub_client, tmp_path):
    target = tmp_path / "custom" / "run.jsonl"

    boukensha.run(task="hi", log=str(target))

    assert target.exists()


def test_the_logger_is_closed_on_the_happy_path(settings, stub_client, log_path):
    boukensha.run(task="hi", log=log_path)

    # A closed handle refuses further writes; reading the file back proves it was flushed.
    assert log_lines(log_path)[-1]["phase"] == "turn_end"


def test_the_logger_is_closed_when_the_agent_raises(settings, monkeypatch, log_path):
    class Exploding(StubClient):
        def call(self, **kwargs):
            raise ApiError("boom")

    StubClient.instances = []
    monkeypatch.setattr(boukensha, "Client", Exploding)

    with pytest.raises(ApiError, match="boom"):
        boukensha.run(task="hi", log=log_path)

    # The session_start line survived, so the handle was flushed and closed on the way out.
    assert log_lines(log_path)[0]["phase"] == "session_start"


def test_a_failure_before_the_logger_exists_propagates_as_itself(settings, stub_client, log_path):
    """The §5.2 regression detector. Ruby defines locals from parse time, so `logger&.close` in
    `ensure` is a no-op when the logger was never built. Python would raise UnboundLocalError in
    `finally` and MASK this error — which only ever happens on the failure path."""
    with pytest.raises(ValueError, match="Unknown backend"):
        boukensha.run(task="hi", backend="not_a_backend", log=log_path)
