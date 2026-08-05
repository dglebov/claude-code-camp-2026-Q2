"""Tests for `boukensha/logger.py`.

Ruby step 06 ships no specs — see `docs/plans/python_port/06_the_logger.md` §7.1.

Every test writes into `tmp_path`. Nothing here may touch the real `.boukensha/sessions/`.
"""

import json
import re
from pathlib import Path

import boukensha
import pytest
from boukensha.logger import Logger


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    """`boukensha` memoizes config and holds debug/quiet flags at module level. Left alone they
    leak between tests (plan §5.1)."""
    monkeypatch.setattr(boukensha, "_config", None)
    monkeypatch.setattr(boukensha, "_debug", False)
    monkeypatch.setattr(boukensha, "_quiet", False)


@pytest.fixture
def logger(tmp_path):
    return Logger(session_id="test-session", dir=str(tmp_path / "sessions"))


def lines(logger):
    return [json.loads(ln) for ln in Path(logger.path).read_text().splitlines()]


class FakeBackend:
    def __init__(self, *, usage_unit="tokens", usage_level=None, cost=0.5):
        self.model = "claude-sonnet-4-6"
        self.usage_unit = usage_unit
        self.usage_level = usage_level
        self._cost = cost

    def estimate_cost(self, *, input_tokens, output_tokens):
        return self._cost


class FakeTask:
    @classmethod
    def task_name(cls):
        return "player"


# ---------- construction -----------------------------------------------------


def test_the_constructor_creates_the_directory_and_writes_session_start(tmp_path):
    log = Logger(session_id="s1", dir=str(tmp_path / "deep" / "sessions"))

    assert (tmp_path / "deep" / "sessions").is_dir()
    assert lines(log)[0]["phase"] == "session_start"


def test_a_snapshot_is_merged_into_the_session_start_line(tmp_path):
    log = Logger(session_id="s1", dir=str(tmp_path), snapshot={"provider": "anthropic", "model": "x"})

    first = lines(log)[0]
    assert first["phase"] == "session_start"
    assert first["provider"] == "anthropic"
    assert first["model"] == "x"


def test_an_explicit_session_id_is_used_verbatim(logger):
    assert logger.session_id == "test-session"


def test_a_generated_session_id_matches_rubys_format(tmp_path):
    log = Logger(dir=str(tmp_path))

    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", log.session_id)


def test_the_log_argument_overrides_the_whole_path(tmp_path):
    target = tmp_path / "custom" / "run.jsonl"

    assert Logger(session_id="s1", log=str(target)).path == str(target)
    assert target.exists()


def test_the_path_defaults_to_session_id_dot_jsonl_inside_dir(tmp_path):
    assert Logger(session_id="s1", dir=str(tmp_path)).path == str(tmp_path / "s1.jsonl")


# ---------- every line's envelope --------------------------------------------


def test_every_line_carries_the_session_id_and_a_timestamp(logger):
    logger.iteration(n=1, max=25)
    logger.turn_end(reason="completed", iterations=1)

    for line in lines(logger):
        assert line["session_id"] == "test-session"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", line["at"])


def test_every_line_is_valid_json(logger):
    logger.tool_call(name="look", args={"a": 1})

    for raw in Path(logger.path).read_text().splitlines():
        json.loads(raw)


# ---------- one test per event kind ------------------------------------------


def test_iteration(logger):
    logger.iteration(n=2, max=25)

    last = lines(logger)[-1]
    assert (last["phase"], last["n"], last["max"]) == ("iteration", 2, 25)


def test_limit_reached(logger):
    logger.limit_reached(kind="max_iterations", n=25, max=25)

    last = lines(logger)[-1]
    assert (last["phase"], last["kind"], last["n"], last["max"]) == ("limit_reached", "max_iterations", 25, 25)


def test_turn_end(logger):
    logger.turn_end(reason="completed", iterations=3, tokens=100)

    last = lines(logger)[-1]
    assert (last["phase"], last["reason"], last["iterations"], last["tokens"]) == ("turn_end", "completed", 3, 100)


def test_tool_call(logger):
    logger.tool_call(name="read_file", args={"path": "README.md"})

    last = lines(logger)[-1]
    assert (last["phase"], last["name"], last["args"]) == ("tool_call", "read_file", {"path": "README.md"})


def test_tool_result_stringifies_and_defaults_to_ok(logger):
    logger.tool_result(name="look", result=123)

    last = lines(logger)[-1]
    assert (last["phase"], last["name"], last["result"], last["ok"], last["error"]) == (
        "tool_result",
        "look",
        "123",
        True,
        None,
    )


def test_tool_result_records_a_failure(logger):
    logger.tool_result(name="look", result="ERROR: ValueError: boom", ok=False, error="boom")

    last = lines(logger)[-1]
    assert last["ok"] is False
    assert last["error"] == "boom"


def test_prompt_records_counts_and_tool_names_not_tool_objects(logger):
    class Msg:
        def __init__(self, role, content):
            self.role, self.content = role, content

    logger.prompt(
        messages=[Msg("user", "hi"), Msg("assistant", [{"type": "text", "text": "yo"}])],
        tools={"look": object(), "move": object()},
    )

    last = lines(logger)[-1]
    assert last["phase"] == "prompt"
    assert last["message_count"] == 2
    assert last["tool_count"] == 2
    assert last["tools"] == ["look", "move"]
    assert last["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [{"type": "text", "text": "yo"}]},
    ]


# ---------- raw is debug-gated -----------------------------------------------


def test_raw_writes_nothing_unless_debug_is_on(logger):
    before = len(lines(logger))
    logger.raw(data={"a": 1})

    assert len(lines(logger)) == before


def test_raw_writes_when_debug_is_on(logger, monkeypatch):
    monkeypatch.setattr(boukensha, "_debug", True)
    logger.raw(data={"a": 1})

    last = lines(logger)[-1]
    assert (last["phase"], last["data"]) == ("raw", {"a": 1})


# ---------- response: usage, cost, metadata ----------------------------------


def test_response_records_text_and_stop_reason(logger):
    logger.response(text="  hello  ", stop_reason="end_turn")

    last = lines(logger)[-1]
    assert (last["phase"], last["text"], last["stop_reason"]) == ("response", "hello", "end_turn")


@pytest.mark.parametrize(
    "usage,expected",
    [
        ({"input_tokens": 10, "output_tokens": 20}, (10, 20)),  # Anthropic
        ({"prompt_tokens": 10, "completion_tokens": 20}, (10, 20)),  # OpenAI
        ({"promptTokenCount": 10, "candidatesTokenCount": 20}, (10, 20)),  # Gemini
        ({"prompt_eval_count": 10, "eval_count": 20}, (10, 20)),  # Ollama
    ],
)
def test_response_extracts_usage_across_provider_vocabularies(logger, usage, expected):
    logger.response(text="x", usage=usage, backend=FakeBackend())

    last = lines(logger)[-1]
    assert (last["input_tokens"], last["output_tokens"]) == expected


def test_response_computes_cost_from_the_backend(logger):
    logger.response(text="x", usage={"input_tokens": 10, "output_tokens": 20}, backend=FakeBackend(cost=0.25))

    assert lines(logger)[-1]["cost_usd"] == 0.25


def test_response_keeps_a_zero_cost_rather_than_dropping_it(logger):
    """Hash#compact removes nil only. A truthiness filter would drop every local Ollama model,
    which prices at 0.0 (plan §5.6)."""
    logger.response(text="x", usage={"input_tokens": 0, "output_tokens": 0}, backend=FakeBackend(cost=0.0))

    last = lines(logger)[-1]
    assert last["cost_usd"] == 0.0
    assert last["input_tokens"] == 0
    assert last["output_tokens"] == 0


def test_response_omits_none_valued_metadata_keys(logger):
    logger.response(text="x", usage={"input_tokens": 1, "output_tokens": 2}, backend=FakeBackend(usage_level=None))

    assert "usage_level" not in lines(logger)[-1]


def test_response_records_task_and_provider_names(logger):
    logger.response(text="x", usage={"input_tokens": 1, "output_tokens": 2}, task=FakeTask, backend=FakeBackend())

    last = lines(logger)[-1]
    assert last["task"] == "player"
    assert last["model"] == "claude-sonnet-4-6"
    assert last["usage_unit"] == "tokens"


def test_a_non_numeric_usage_value_yields_none_for_the_whole_lookup(logger):
    """Ruby's rescue is on the method, not per key, so a bad value aborts the entire lookup
    rather than falling through to the next candidate (plan §5.7)."""
    logger.response(text="x", usage={"input_tokens": "abc", "prompt_tokens": 5}, backend=FakeBackend())

    assert "input_tokens" not in lines(logger)[-1]


def test_response_without_task_backend_or_usage_adds_no_metadata(logger):
    logger.response(text="x")

    last = lines(logger)[-1]
    assert "model" not in last
    assert "cost_usd" not in last


# ---------- provider name derivation -----------------------------------------


@pytest.mark.parametrize(
    "cls_name,expected",
    [("Anthropic", "anthropic"), ("OpenAI", "open_ai"), ("Gemini", "gemini"), ("OllamaCloud", "ollama_cloud")],
)
def test_provider_name_snake_cases_the_backend_class(logger, cls_name, expected):
    backend = type(cls_name, (FakeBackend,), {})()

    logger.response(text="x", usage={"input_tokens": 1, "output_tokens": 2}, backend=backend)

    assert lines(logger)[-1]["provider"] == expected


# ---------- close ------------------------------------------------------------


def test_close_closes_the_handle(logger):
    logger.close()

    with pytest.raises(ValueError):
        logger.iteration(n=1, max=1)


# ---------- step 07: turn and subscribe --------------------------------------


def test_turn_writes_its_phase(logger):
    logger.turn(n=3)

    last = lines(logger)[-1]
    assert (last["phase"], last["n"]) == ("turn", 3)


def test_a_subscriber_receives_every_subsequent_event(logger):
    seen = []
    logger.subscribe(seen.append)

    logger.iteration(n=1, max=25)
    logger.turn_end(reason="completed", iterations=1)

    assert [e["phase"] for e in seen] == ["iteration", "turn_end"]


def test_subscribers_see_the_event_without_the_envelope(logger):
    """Ruby passes `event`, not the merged hash — `Hash#merge` returns a new object, so the
    session_id/at envelope never reaches the subscriber (plan §5.4)."""
    seen = []
    logger.subscribe(seen.append)

    logger.iteration(n=1, max=25)

    assert seen[0] == {"phase": "iteration", "n": 1, "max": 25}
    assert "session_id" not in seen[0]
    assert "at" not in seen[0]


def test_a_subscriber_fires_after_the_line_is_written(logger):
    """Ruby writes and flushes before fanning out, so a subscriber can already read its own
    event back off disk."""
    seen = []
    logger.subscribe(lambda event: seen.append(len(lines(logger))))

    logger.iteration(n=1, max=25)

    assert seen == [2]  # session_start + iteration, both already on disk


def test_every_subscriber_fires_in_registration_order(logger):
    order = []
    logger.subscribe(lambda e: order.append("first"))
    logger.subscribe(lambda e: order.append("second"))

    logger.turn(n=1)

    assert order == ["first", "second"]


def test_writing_works_with_no_subscribers(logger):
    """The lazy-nil case: Ruby guards with `@subscribers&.each`, so nothing iterates until
    someone subscribes."""
    logger.turn(n=1)

    assert lines(logger)[-1]["phase"] == "turn"
