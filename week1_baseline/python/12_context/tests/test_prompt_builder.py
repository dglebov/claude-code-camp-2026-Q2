import json

import pytest
from boukensha.backends import Anthropic, Gemini, Ollama, OllamaCloud
from boukensha.prompt_builder import PromptBuilder


@pytest.fixture
def builder(context):
    return PromptBuilder(context, Anthropic(api_key="sk-test", model="claude-sonnet-4-6"))


# ---------- delegation -------------------------------------------------------


def test_to_tools_delegates_to_the_backend(builder, context):
    backend = Anthropic(api_key="sk-test", model="claude-sonnet-4-6")

    assert builder.to_tools() == backend.to_tools(context.tools)


def test_to_api_payload_delegates_to_the_backend(builder, context):
    backend = Anthropic(api_key="sk-test", model="claude-sonnet-4-6")

    assert builder.to_api_payload() == backend.to_payload(context)


def test_to_api_payload_honours_max_output_tokens(builder):
    assert builder.to_api_payload(max_output_tokens=64)["max_tokens"] == 64


def test_headers_and_url_delegate(builder):
    assert builder.headers()["anthropic-version"] == "2023-06-01"
    assert builder.url() == "https://api.anthropic.com/v1/messages"


def test_the_same_context_serializes_differently_per_backend(context):
    anthropic = PromptBuilder(context, Anthropic(api_key="sk-test", model="claude-sonnet-4-6")).to_api_payload()
    gemini = PromptBuilder(context, Gemini(api_key="sk-test", model="gemini-2.5-flash")).to_api_payload()

    assert "system" in anthropic
    assert "systemInstruction" in gemini
    assert anthropic["messages"][1]["role"] == "assistant"
    assert gemini["contents"][1]["role"] == "model"


def test_payload_is_json_serializable(builder):
    """Nothing in a payload may be a Python-only object — it is about to be POSTed."""
    assert json.loads(json.dumps(builder.to_api_payload())) == builder.to_api_payload()


# ---------- the arity bug carried over from Ruby -----------------------------


@pytest.mark.parametrize(
    "backend",
    [
        Anthropic(api_key="sk-test", model="claude-sonnet-4-6"),
        Gemini(api_key="sk-test", model="gemini-2.5-flash"),
    ],
)
def test_to_messages_works_for_single_argument_backends(context, backend):
    assert PromptBuilder(context, backend).to_messages() == backend.to_messages(context.messages)


@pytest.mark.parametrize(
    "backend",
    [
        Ollama(model="qwen3:8b"),
        OllamaCloud(api_key="sk-test", model="kimi-k2.5:cloud"),
    ],
)
def test_to_messages_raises_for_two_argument_backends(context, backend):
    """PromptBuilder passes one argument; these three declare `to_messages(system, messages)`.

    Broken identically in the Ruby original, where it raises ArgumentError. Nothing reaches it —
    `to_api_payload` goes through `to_payload` — so the defect never surfaces in normal use. Pinned
    here so that fixing it in a later step is a deliberate change rather than a silent divergence.
    """
    with pytest.raises(TypeError):
        PromptBuilder(context, backend).to_messages()
