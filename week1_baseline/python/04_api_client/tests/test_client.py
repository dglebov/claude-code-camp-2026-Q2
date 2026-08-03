"""Tests for `boukensha/client.py`.

Ruby step 04 ships no specs, so these have no counterpart to mirror — see
`docs/plans/python_port/04_api_client.md` §7.1.

Every test drives a fake builder, so nothing here depends on the backends. The network is
stubbed by patching `boukensha.client.urlopen`; `boukensha.client.time.sleep` is patched
alongside it so the suite asserts the backoff schedule without waiting for it.
"""

import http.client
import io
import json
import socket
import ssl
from urllib.error import HTTPError, URLError

import pytest
from boukensha.client import Client
from boukensha.errors import ApiError

PAYLOAD = {"model": "claude-sonnet-4-6", "max_tokens": 1024, "messages": []}
URL = "https://api.anthropic.com/v1/messages"
HEADERS = {"content-type": "application/json", "x-api-key": "sk-test"}
BODY = {"id": "msg_1", "stop_reason": "end_turn"}


class FakeBuilder:
    """Stands in for PromptBuilder — Client only ever calls these three."""

    def __init__(self):
        self.max_output_tokens = None

    def url(self):
        return URL

    def headers(self):
        return dict(HEADERS)

    def to_api_payload(self, max_output_tokens=1024):
        self.max_output_tokens = max_output_tokens
        return dict(PAYLOAD)


def ok(body=None, status=200):
    """Script entry: a successful response. Returns a factory so each attempt gets a fresh
    stream — a BytesIO can only be read once."""

    def make():
        raw = io.BytesIO(json.dumps(BODY if body is None else body).encode())
        raw.status = status
        return raw

    return make


def http_error(status, body='{"type":"error"}'):
    """Script entry: urlopen raising HTTPError, which is how urllib reports any non-2xx."""

    def make():
        raise HTTPError(URL, status, "error", {}, io.BytesIO(body.encode()))

    return make


def raises(exc):
    """Script entry: a transport-level failure."""

    def make():
        raise exc

    return make


class FakeUrlopen:
    """Replays a script of outcomes, recording every call. When the script runs out the last
    entry repeats, so `FakeUrlopen(http_error(503))` fails every attempt."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append((request, timeout))
        entry = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return entry()

    @property
    def count(self):
        return len(self.calls)

    @property
    def request(self):
        return self.calls[0][0]


@pytest.fixture
def builder():
    return FakeBuilder()


@pytest.fixture
def sleeps(monkeypatch):
    """Captures the backoff schedule instead of waiting 3.5s for it."""
    recorded = []
    monkeypatch.setattr("boukensha.client.time.sleep", recorded.append)
    return recorded


@pytest.fixture
def net(monkeypatch):
    def install(*script):
        fake = FakeUrlopen(*script)
        monkeypatch.setattr("boukensha.client.urlopen", fake)
        return fake

    return install


# ---------- happy path -------------------------------------------------------


def test_a_200_returns_the_parsed_body(builder, net):
    fake = net(ok())

    assert Client(builder).call() == BODY
    assert fake.count == 1


def test_the_request_carries_the_builders_url_headers_and_method(builder, net):
    fake = net(ok())

    Client(builder).call()

    assert fake.request.full_url == URL
    assert fake.request.method == "POST"
    # urllib capitalizes header names on the way in.
    assert fake.request.headers == {"Content-type": "application/json", "X-api-key": "sk-test"}


def test_the_request_body_is_the_payload_as_utf8_json(builder, net):
    fake = net(ok())

    Client(builder).call()

    assert isinstance(fake.request.data, bytes)
    assert json.loads(fake.request.data.decode("utf-8")) == PAYLOAD


def test_max_output_tokens_defaults_to_1024_and_is_forwarded(builder, net):
    net(ok())

    Client(builder).call()
    assert builder.max_output_tokens == 1024

    Client(builder).call(max_output_tokens=64)
    assert builder.max_output_tokens == 64


def test_a_timeout_is_always_passed_to_urlopen(builder, net):
    """urlopen defaults to no timeout at all, so omitting this would hang forever on a dead
    connection. Ruby's Net::HTTP defaults to 60s; the port matches it (plan §5.3)."""
    fake = net(ok())

    Client(builder).call()

    assert fake.calls[0][1] == 60


# ---------- non-retryable statuses -------------------------------------------


def test_a_400_is_not_retried_and_reports_a_singular_attempt(builder, net, sleeps):
    """HTTPError subclasses URLError. Catch them in the wrong order and every 400 burns four
    attempts on the transient path (plan §5.2)."""
    fake = net(http_error(400, '{"type":"error","error":{"message":"bad"}}'))

    with pytest.raises(ApiError) as excinfo:
        Client(builder).call()

    assert fake.count == 1
    assert sleeps == []
    assert str(excinfo.value) == (
        'API request failed after 1 attempt (400): {"type":"error","error":{"message":"bad"}}'
    )


@pytest.mark.parametrize("status", [401, 403, 404, 422])
def test_other_client_errors_are_not_retried(builder, net, sleeps, status):
    fake = net(http_error(status))

    with pytest.raises(ApiError):
        Client(builder).call()

    assert fake.count == 1


# ---------- retry on status --------------------------------------------------


def test_two_503s_then_a_200_succeeds_with_exponential_backoff(builder, net, sleeps):
    fake = net(http_error(503), http_error(503), ok())

    assert Client(builder).call() == BODY
    assert fake.count == 3
    assert sleeps == [0.5, 1.0]


def test_a_persistent_503_gives_up_after_four_attempts(builder, net, sleeps):
    fake = net(http_error(503, "overloaded"))

    with pytest.raises(ApiError) as excinfo:
        Client(builder).call()

    assert fake.count == 4
    assert sleeps == [0.5, 1.0, 2.0]
    assert str(excinfo.value) == "API request failed after 4 attempts (503): overloaded"


@pytest.mark.parametrize("status", [408, 409, 429, 500, 502, 503, 504])
def test_every_retryable_status_is_retried(builder, net, sleeps, status):
    fake = net(http_error(status), ok())

    assert Client(builder).call() == BODY
    assert fake.count == 2


# ---------- retry on transport failures --------------------------------------

TRANSIENT = [
    ConnectionResetError("reset"),
    ConnectionRefusedError("refused"),
    TimeoutError("timed out"),
    ssl.SSLError("handshake"),
    socket.gaierror("name resolution"),
    http.client.IncompleteRead(b"partial"),
    http.client.RemoteDisconnected("closed"),
]


@pytest.mark.parametrize("error", TRANSIENT, ids=lambda e: type(e).__name__)
def test_bare_transport_failures_are_retried(builder, net, sleeps, error):
    """A read that fails after the headers arrived is not wrapped in URLError."""
    fake = net(raises(error), ok())

    assert Client(builder).call() == BODY
    assert fake.count == 2


@pytest.mark.parametrize("error", TRANSIENT, ids=lambda e: type(e).__name__)
def test_urlerror_wrapped_transport_failures_are_retried(builder, net, sleeps, error):
    """urllib buries the real exception in .reason — matching on the wrapper alone would be
    both too broad and too narrow (plan §5.5)."""
    fake = net(raises(URLError(error)), ok())

    assert Client(builder).call() == BODY
    assert fake.count == 2


def test_persistent_transport_failure_gives_up_after_four_attempts(builder, net, sleeps):
    fake = net(raises(ConnectionRefusedError("refused")))

    with pytest.raises(ApiError) as excinfo:
        Client(builder).call()

    assert fake.count == 4
    assert sleeps == [0.5, 1.0, 2.0]
    assert str(excinfo.value) == "API request failed after 4 attempts: ConnectionRefusedError: refused"


def test_a_non_transient_urlerror_reason_propagates_unretried(builder, net, sleeps):
    """Pins the decision against a blanket `except OSError`: PermissionError is an OSError but
    is absent from Ruby's TRANSIENT_ERRORS, so it must not be retried or wrapped (plan §5.4)."""
    fake = net(raises(URLError(PermissionError("denied"))))

    with pytest.raises(URLError):
        Client(builder).call()

    assert fake.count == 1
    assert sleeps == []


# ---------- decoding ---------------------------------------------------------


def test_a_malformed_body_raises_a_decode_error_not_an_api_error(builder, net):
    """Ruby's JSON.parse sits outside the rescue, so a 200 carrying junk is a decode failure,
    not an API failure."""

    def junk():
        raw = io.BytesIO(b"not json")
        raw.status = 200
        return raw

    net(junk)

    with pytest.raises(json.JSONDecodeError):
        Client(builder).call()
