"""Port of `ruby/08_the_repl_loop/lib/boukensha/client.rb`.

Puts the built payload on the wire. Everything up to step 03 assembled a request; this is what
sends it.

It knows nothing about providers — url, headers and payload all come from the builder, which
delegates to its backend. That is why five backends need no branching here. It also does not
interpret the reply: `call` returns the raw provider dict, exactly as Ruby does. Normalizing
that into a Message is step 05.

Ruby uses `net/http` from its stdlib; this uses `urllib.request` from Python's, keeping the
dependency budget at zero. The two libraries disagree in ways documented inline below and in
`docs/plans/python_port/04_api_client.md` §5.
"""

import http.client
import json
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ApiError

RETRYABLE_STATUS_CODES = (408, 409, 429, 500, 502, 503, 504)

# Ruby's TRANSIENT_ERRORS, translated. Every entry below subclasses OSError, which makes a bare
# `except OSError` tempting — but that would also retry PermissionError, IsADirectoryError and
# every other unrelated OSError, which Ruby's explicit list does not. Enumerated deliberately.
#
#   EOFError                                  -> RemoteDisconnected (a ConnectionResetError), IncompleteRead
#   Errno::ECONNRESET                         -> ConnectionResetError
#   Errno::ECONNREFUSED                       -> ConnectionRefusedError
#   Net::OpenTimeout/ReadTimeout/Timeout      -> TimeoutError (socket.timeout is an alias since 3.10)
#   OpenSSL::SSL::SSLError                    -> ssl.SSLError
#   SocketError                               -> socket.gaierror (DNS failure)
TRANSIENT_ERRORS = (
    ConnectionResetError,
    ConnectionRefusedError,
    TimeoutError,
    ssl.SSLError,
    socket.gaierror,
    http.client.IncompleteRead,
)

MAX_RETRIES = 3
BASE_RETRY_DELAY = 0.5

# Ruby's Net::HTTP defaults to 60s open / 60s read. urlopen's default is no timeout at all, so
# omitting this would let a hung connection block forever without ever raising — and therefore
# without ever retrying.
TIMEOUT = 60

# HTTPError subclasses URLError, and _perform already converts it to a value. Listing URLError
# here catches the wrapper urllib puts around socket-level failures; the bare classes catch a
# read that fails after the headers arrived, which is not wrapped.
_RETRY_CATCH = (URLError, *TRANSIENT_ERRORS)


class _Response:
    """No counterpart in the Ruby.

    Net::HTTP returns a response object for every status, so `client.rb` inspects `response.code`
    as data. urlopen raises HTTPError on any non-2xx, making status control flow instead. This
    exists to undo that, so `call` below can stay shaped like the Ruby.
    """

    def __init__(self, status, body):
        self.status = status
        self.body = body


def _perform(request):
    try:
        with urlopen(request, timeout=TIMEOUT) as raw:
            return _Response(raw.status, raw.read().decode("utf-8"))
    except HTTPError as error:
        # A status code, not a transport failure. HTTPError is itself readable. This `except`
        # MUST precede any URLError handling — HTTPError is a subclass, so the wrong order sends
        # every 400 down the retry path.
        return _Response(error.code, error.read().decode("utf-8"))


def _is_transient(error):
    if isinstance(error, HTTPError):
        return False

    if isinstance(error, URLError):
        # urllib buries the real exception here: a refused connection arrives as
        # URLError(reason=ConnectionRefusedError(...)), not as the bare error. `reason` is
        # occasionally a plain string, which isinstance below correctly rejects.
        error = error.reason

    return isinstance(error, TRANSIENT_ERRORS)


def _retry_delay(attempt):
    return BASE_RETRY_DELAY * (2 ** (attempt - 1))


class Client:
    def __init__(self, builder):
        self._builder = builder

    def call(self, max_output_tokens=1024, tools=None):
        payload = self._builder.to_api_payload(max_output_tokens=max_output_tokens, tools=tools)
        request = Request(
            self._builder.url(),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._builder.headers(),
            method="POST",
        )

        attempts = 0
        response = None

        # Ruby reuses one Net::HTTP object across retries; each urlopen opens a fresh connection.
        # Invisible here — the retries are seconds apart and the Ruby sets no keep-alive.
        while True:
            attempts += 1

            try:
                response = _perform(request)
            except _RETRY_CATCH as error:
                if not _is_transient(error):
                    raise

                if attempts > MAX_RETRIES:
                    # Ruby interpolates `e.class`, e.g. Errno::ECONNREFUSED. Python's equivalent
                    # reads ConnectionRefusedError. The format matches; the class names cannot.
                    raise ApiError(
                        f"API request failed after {attempts} attempts: {type(error).__name__}: {error}"
                    ) from error

                time.sleep(_retry_delay(attempts))
                continue

            if response.status in RETRYABLE_STATUS_CODES and attempts <= MAX_RETRIES:
                time.sleep(_retry_delay(attempts))
                continue

            break

        if response.status == 401:
            # New in step 08. A REPL survives its errors, so the one error a user can actually
            # fix gets a message that names the fix instead of dumping the provider's body.
            raise ApiError("authentication failed (401) — check your API key")

        if not 200 <= response.status < 300:
            raise ApiError(
                f"API request failed after {attempts} attempt{'' if attempts == 1 else 's'} "
                f"({response.status}): {response.body}"
            )

        # Outside the retry path, mirroring Ruby: a malformed body raises JSONDecodeError rather
        # than being dressed up as an ApiError.
        return json.loads(response.body)
