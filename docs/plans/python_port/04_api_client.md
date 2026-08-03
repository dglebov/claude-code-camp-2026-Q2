# Python Port Plan — Step 04 · The API Client

Port `week1_baseline/ruby/04_api_client` to `week1_baseline/python/04_api_client`.

**Scope:** week1 only, step 04 only. Builds on the completed step-03 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** none outstanding. The Ruby reference was broken by a `PROMPTS_DIR` regression;
it was fixed on 2026-08-03 and the tree now produces a valid baseline — see §9.

This is the **smallest step so far**. Ruby 03 → 04 adds exactly one new file (`client.rb`, 78
lines) and four small edits. Step 03 already ported all five backends and their tests, and
`PromptBuilder` already exposes the three methods `Client` consumes. The work is one module, its
test suite, and an example.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| HTTP library | **`urllib.request` (stdlib).** Ruby uses `net/http` from its stdlib; the Python tree matches. `pyproject.toml` states PyYAML is "the one unavoidable runtime dependency" and the `.env` loader was hand-rolled to avoid `python-dotenv` — adding `httpx`/`requests` would break that rule for one call site. |
| Retry-loop shape | **Normalize, then mirror.** A private `_Response(status, body)` converts `HTTPError` back into a value, so `call()` reads line-for-line like `client.rb`. See §5.1. |
| Test seam | **Patch `boukensha.client.urlopen` and `boukensha.client.time.sleep`.** Keeps `Client.__init__(builder)` identical to Ruby's — no constructor parameter that exists only for tests. Patching `sleep` also lets the suite assert the exact backoff schedule without waiting 3.5s. |
| Timeout | **Explicit `timeout=60`.** Ruby's `Net::HTTP` defaults to 60s open / 60s read; `urlopen` defaults to *no timeout* and blocks forever. Not passing it would make the Python strictly worse than the Ruby. See §5.3. |
| Transient-error set | **Enumerate explicitly**, do not catch bare `OSError`. Every Ruby entry maps to an `OSError` subclass, so a blanket catch would silently retry conditions Ruby does not. See §5.4. |
| Structure | Mirror Ruby 1:1, as in steps 00–03. |
| Environment | Shared `week1_baseline/python/.venv`. `urllib`, `json`, `ssl`, `socket`, `http.client` are all stdlib. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/04_api_client/`.

### New in this step — the actual work

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/client.rb` | POST the built payload, retry transient failures with exponential backoff, raise `ApiError` on non-success, parse JSON | `boukensha/client.py` |
| `examples/example.rb` | Smoke test: build a `Context`, register two tools, select a backend by provider, call once, pretty-print the raw response | `examples/example.py` |
| `prompts/system.md` | **Rewritten in this step** — 182 bytes, "You are Boukensha, an autonomous player exploring a CircleMUD world." Step 03's is a different, shorter prompt. Copy from `ruby/04_api_client/`, *not* forward from `python/03_prompt_builder/`. | `04_api_client/prompts/system.md` |
| `README.md` | Step README | `04_api_client/README.md` (adapted) |

Ruby step 04 ships **no tests**. `tests/test_client.py` is net-new design work, not a port — §7.

### Changed vs step 03 — small, targeted edits

| File | Delta |
|---|---|
| `boukensha/errors.py` | **Add `ApiError`.** One line in Ruby: `class ApiError < StandardError; end`. |
| `boukensha/__init__.py` | **Extend** — add `Client` to the imports and `__all__`. |
| `boukensha/tasks/base.py` | **Add the `settings.is_a?(Hash)` guard** to `_fetch` (`return None if not isinstance(settings, dict)`). Ruby added it in this step. The `settings.yml` → `settings.yaml` message fix in the same diff is a no-op for Python — the Python tree has said `settings.yaml` since step 00 (03's §8). |

### Carried forward from step 03 — unchanged

`boukensha/{config,context,env_file,message,prompt_builder,registry,tool}.py`, all of
`boukensha/backends/`, `boukensha/tasks/{__init__,player}.py`, `conftest.py`, and every existing
`tests/test_*.py`.

**`prompts/system.md` is NOT in this list** — see the table above. Run `diff -rq` across the
*whole* tree, not just `*.rb`: a `find`-based file-list comparison plus a `*.rb`-only content diff
misses it, because the two trees have the same *filenames*. Getting this wrong is silent — both
trees run fine, produce structurally identical responses, and differ only in the input-token
count (682 vs 670), which is easy to dismiss as prompt-cache noise.

### Context only — do not port

- `week1_baseline/ITERATIONS.md` §4 — design intent. Note that **response normalization is step
  05**: `Client.call` deliberately returns the raw provider dict, not a `Message`.
- `docs/plans/python_port/{00_config,01_struct_skeleton,02_the_registry,03_prompt_builder}.md` —
  §5 of each still applies in full.

---

## 3. What step 04 actually adds

Steps 00–03 built a payload and stopped. Step 04 puts it on the wire.

```
Context → PromptBuilder → backend payload → Client.call → HTTP POST → raw JSON dict
```

`Client` is deliberately thin and owns exactly four responsibilities:

1. **Transport.** POST `builder.to_api_payload()` to `builder.url()` with `builder.headers()`.
2. **Retry.** Up to 4 total attempts on transient connection failures *and* on the retryable
   status set `{408, 409, 429, 500, 502, 503, 504}`, with exponential backoff.
3. **Error boundary.** Any non-2xx that survives retries becomes an `ApiError` carrying the
   status and body.
4. **Decode.** `json.loads` on the response body.

It knows nothing about providers — that is the backend's job, reached through the builder. This is
why `Client` needs no per-provider branching despite five backends existing.

**Retry schedule** (`MAX_RETRIES = 3`, `BASE_RETRY_DELAY = 0.5`, delay = `0.5 * 2**(attempt-1)`):

| Attempt | On failure |
|---|---|
| 1 | sleep 0.5s, retry |
| 2 | sleep 1.0s, retry |
| 3 | sleep 2.0s, retry |
| 4 | raise `ApiError` |

Four requests, three sleeps, 3.5s total worst case. Both failure modes converge on four attempts,
though by different routes: the transient path raises when `attempts > MAX_RETRIES`, the status
path stops retrying when `attempts <= MAX_RETRIES` goes false and falls through to the non-success
raise. Verified against the live tree: a 400 is not retryable, so it reports `after 1 attempt`.

---

## 4. Target layout

```
week1_baseline/python/04_api_client/
  README.md
  conftest.py                    # copy-forward
  prompts/
    system.md                    # copy-forward
  boukensha/
    __init__.py                  # extended: + Client
    client.py                    # NEW — the whole step
    config.py                    # copy-forward
    context.py                   # copy-forward
    env_file.py                  # copy-forward
    errors.py                    # + ApiError
    message.py                   # copy-forward
    prompt_builder.py            # copy-forward
    registry.py                  # copy-forward
    tool.py                      # copy-forward
    backends/                    # all six files copy-forward
    tasks/
      __init__.py                # copy-forward
      base.py                    # + isinstance(settings, dict) guard
      player.py                  # copy-forward
  examples/
    example.py                   # NEW — ported from example.rb
  tests/
    test_client.py               # NEW — no Ruby counterpart
    …                            # 12 existing files copy-forward
```

Plus `week1_baseline/bin/python/04_api_client` (the Ruby launcher already exists).

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 `urlopen` raises on 4xx/5xx; `Net::HTTP` returns

The central gap. Ruby's `http.request` returns a response object for *every* status, so the retry
loop inspects `response.code` as data. Python's `urlopen` raises `HTTPError` on any non-2xx, so
status arrives as control flow.

Bridge it in one helper so the loop itself stays Ruby-shaped:

```python
class _Response:
    """Not in the Ruby. Exists to undo urllib's exception-for-status behaviour so that
    `call` can inspect a status the way `client.rb` does."""

    def __init__(self, status, body):
        self.status = status
        self.body = body


def _perform(request):
    try:
        with urlopen(request, timeout=TIMEOUT) as raw:
            return _Response(raw.status, raw.read().decode("utf-8"))
    except HTTPError as error:
        # A status code, not a transport failure. HTTPError is itself readable.
        return _Response(error.code, error.read().decode("utf-8"))
```

### 5.2 `HTTPError` subclasses `URLError` — except-ordering is load-bearing

`urllib.error.HTTPError` is a subclass of `URLError`. An `except URLError` placed first swallows
every 4xx/5xx and routes it into the transient path, turning a 400 into four attempts. `HTTPError`
must be caught first. Pin this with a test asserting a 400 makes exactly **one** request.

### 5.3 Timeouts: Ruby defaults to 60s, urllib defaults to forever

`Net::HTTP` ships `open_timeout = 60` and `read_timeout = 60`. `urlopen`'s `timeout` parameter
defaults to `socket._GLOBAL_DEFAULT_TIMEOUT`, which is `None` — no timeout at all. A hung
connection would block the process indefinitely with no retry, because no exception is ever
raised. Pass `timeout=60` explicitly and name the constant `TIMEOUT` so it is greppable.

### 5.4 Transient-error mapping

Ruby's six-entry `TRANSIENT_ERRORS` has no one-to-one Python equivalent:

| Ruby | Python |
|---|---|
| `EOFError` | `http.client.RemoteDisconnected` (subclasses `ConnectionResetError`), `http.client.IncompleteRead` |
| `Errno::ECONNRESET` | `ConnectionResetError` |
| `Errno::ECONNREFUSED` | `ConnectionRefusedError` |
| `Net::OpenTimeout`, `Net::ReadTimeout`, `Timeout::Error` | `TimeoutError` (`socket.timeout` is an alias since 3.10) |
| `OpenSSL::SSL::SSLError` | `ssl.SSLError` |
| `SocketError` | `socket.gaierror` (DNS resolution failure) |

Every one of these subclasses `OSError`, which makes `except OSError` tempting — **don't**. It
would also retry `PermissionError`, `IsADirectoryError`, and every other unrelated `OSError`,
which Ruby's explicit list does not. Enumerate:

```python
TRANSIENT_ERRORS = (
    ConnectionResetError,
    ConnectionRefusedError,
    TimeoutError,
    ssl.SSLError,
    socket.gaierror,
    http.client.IncompleteRead,
)
```

### 5.5 `URLError` buries the real exception in `.reason`

urllib wraps most socket-level failures: a refused connection surfaces as
`URLError(reason=ConnectionRefusedError(...))`, not as the bare error. Matching on the wrapper
alone is both too broad and too narrow. Unwrap first:

```python
def _is_transient(error):
    if isinstance(error, HTTPError):     # a status, handled as a value (§5.1)
        return False
    if isinstance(error, URLError):
        error = error.reason
    return isinstance(error, TRANSIENT_ERRORS)
```

A read that fails *after* headers arrive raises the bare error rather than a `URLError`, so both
shapes must be handled — hence the unwrap rather than a `URLError`-only branch.

### 5.6 `time.sleep` must be reachable as a module attribute

Tests patch the backoff to keep the suite fast. `from time import sleep` binds the function into
`boukensha.client` under a name that is awkward to patch cleanly; `import time` then `time.sleep(…)`
makes `boukensha.client.time.sleep` the natural patch target. Use the latter.

### 5.7 Response bodies are bytes

`Net::HTTPResponse#body` is a `String`. `HTTPResponse.read()` and `HTTPError.read()` both return
`bytes`. Decode as UTF-8 at the boundary so `ApiError` messages interpolate cleanly and
`json.loads` receives text.

### 5.8 Error-message parity

Two messages, one of which cannot achieve parity:

- **Non-success** — reproducible exactly. Ruby's `"attempt#{'s' unless attempts == 1}"` becomes
  `f"attempt{'' if attempts == 1 else 's'}"`. Target string:
  `API request failed after 1 attempt (400): {"type":"error",…}`
- **Transient** — Ruby interpolates `e.class`, e.g. `Errno::ECONNREFUSED`. Python's equivalent
  reads `ConnectionRefusedError`. The class names are not the same and cannot be made so without
  a translation table, which is not worth it. Match the *format*, accept the class-name drift, and
  record it in §8.

### 5.9 No connection reuse

Ruby constructs `Net::HTTP.new(host, port)` once and reuses it across retries. Each `urlopen`
opens a fresh connection. Functionally invisible here — retries are seconds apart and the Ruby
sets no keep-alive — but worth a comment so it is not read as an oversight.

### 5.10 TLS verification is already the default

Ruby sets `verify_mode = OpenSSL::SSL::VERIFY_PEER` explicitly, and carries a comment about a
`ca_file` line removed for Linux/WSL2 compatibility. `urlopen` verifies certificates by default
via `ssl.create_default_context()`, which also finds system certs on every platform. No Python
code is needed; note in the docstring that the omission is deliberate, not a downgrade.

---

## 6. Implementation steps

1. **Capture the Ruby baseline.** Run `./week1_baseline/bin/ruby/04_api_client` and save the
   output. §9 is already applied, so this should succeed.
2. **Copy forward** the step-03 Python package into `04_api_client/`, repointing every
   `"""Port of ruby/…"""` docstring at `ruby/04_api_client`. Then **overwrite
   `prompts/system.md`** from `ruby/04_api_client/prompts/` — it was rewritten this step (§2).
3. **`boukensha/errors.py`** — add `ApiError`.
4. **`boukensha/tasks/base.py`** — add the `isinstance(settings, dict)` guard to `_fetch`.
5. **`boukensha/client.py`** — the module: constants, `_Response`, `_is_transient`, `_perform`,
   and `Client.call`. Keep `call`'s structure aligned with `client.rb` line for line.
6. **`boukensha/__init__.py`** — add `Client` to imports and `__all__`.
7. **`examples/example.py`** — port line-for-line from `example.rb`: `BOUKENSHA_DIR` default via
   `parents[4]`, build the context, register `read_file` and `list_directory`, add the user
   message, select the backend by provider (five-branch `if`/`elif` mirroring Ruby's `case`,
   including the `else` that raises), print the four header lines, call, and pretty-print with
   `json.dumps(response, indent=2, ensure_ascii=False)`.
8. **Launcher** — `week1_baseline/bin/python/04_api_client`, copying the 03 launcher and bumping
   the path.
9. **Tests** — §7.
10. **READMEs** — the step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite (primary, runs in CI)

```bash
cd week1_baseline/python && ./run-tests 04_api_client
```

Carry the step-03 suite forward unchanged, and add `tests/test_client.py`. A fake builder
returning fixed `url` / `headers` / `to_api_payload` keeps these tests independent of the backends.

*Happy path*
- a 200 returns the parsed dict, and `urlopen` is called exactly once
- the request carries the builder's URL, headers, and `method="POST"`
- the request body is the builder's payload, JSON-encoded and UTF-8 bytes
- `max_output_tokens` is forwarded to `to_api_payload`; the default is 1024
- `timeout=60` is passed to `urlopen` (§5.3) — a regression here is invisible in every other test

*Retry on status*
- each of `408, 409, 429, 500, 502, 503, 504` retries
- two 503s then a 200 → returns the dict, 3 calls, `sleep` called with exactly `[0.5, 1.0]`
- four 503s → raises `ApiError`, 4 calls, `sleep` called with exactly `[0.5, 1.0, 2.0]`
- the message reads `API request failed after 4 attempts (503): …`

*No retry on non-retryable status*
- **a 400 makes exactly one request** and raises `API request failed after 1 attempt (400): …` —
  singular, per §5.8. This is the test that catches an except-ordering mistake (§5.2)
- 401, 403, 404 behave the same way

*Retry on transient errors*
- each member of `TRANSIENT_ERRORS` retries, both bare and wrapped in `URLError(reason=…)` (§5.5)
- four transient failures → `ApiError` matching `API request failed after 4 attempts: `
- a non-transient `URLError` reason (e.g. `PermissionError`) propagates un-retried and is **not**
  wrapped in `ApiError` — pins §5.4's decision against a blanket `except OSError`

*Decode*
- a 200 with a non-UTF-8 or malformed-JSON body raises `json.JSONDecodeError`, not `ApiError` —
  Ruby's `JSON.parse` is outside its `rescue`, so this mirrors it

Then the full suite and the linter:

```bash
./run-tests && uv run ruff check .
```

### 7.2 Payload parity (offline, free — run this first)

Do this **before** spending anything on §7.3. Both examples build a payload before they POST it,
so replacing the `client.call()` line with a `print` of `builder.to_api_payload()` gives a
byte-for-byte comparison at zero cost:

```bash
export BOUKENSHA_DIR="$PWD/.boukensha" ANTHROPIC_API_KEY=sk-dummy   # never sent

sed 's|^response = client\.call$|puts JSON.pretty_generate(builder.to_api_payload); exit 0|' \
  week1_baseline/ruby/04_api_client/examples/example.rb \
  > week1_baseline/ruby/04_api_client/examples/_payload.rb
(cd week1_baseline/ruby/04_api_client && bundle exec ruby examples/_payload.rb) | sed -n '/^{/,$p' > /tmp/rb.json
rm week1_baseline/ruby/04_api_client/examples/_payload.rb

sed 's|^response = client\.call()$|import sys; print(json.dumps(builder.to_api_payload(), indent=2, ensure_ascii=False)); sys.exit(0)|' \
  week1_baseline/python/04_api_client/examples/example.py \
  > week1_baseline/python/04_api_client/examples/_payload.py
(cd week1_baseline/python && uv run python 04_api_client/examples/_payload.py) | sed -n '/^{/,$p' > /tmp/py.json
rm week1_baseline/python/04_api_client/examples/_payload.py

diff /tmp/rb.json /tmp/py.json   # silence means parity
```

Two traps, both of which produce an empty file rather than an error: the Ruby line is
`client.call` and the Python line is `client.call()`, so the two `sed` patterns are not
interchangeable; and the temporary script must be written **inside** `examples/` or its
`sys.path` / `require_relative` anchor breaks.

This is a stronger check than §7.3 — it compares every byte rather than a set of JSON paths, and
it is what actually caught the `prompts/system.md` divergence (§2).

### 7.3 Live parity run (both trees)

Offline checks prove the retry logic and the payload; they cannot prove the request is one
Anthropic accepts. Run both examples against the real API and compare **shape, not content** —
the model's output varies between calls, so a plain `diff` will always differ.

```bash
./week1_baseline/bin/ruby/04_api_client   > /tmp/rb.json
./week1_baseline/bin/python/04_api_client > /tmp/py.json

# Strip the four header lines, then compare the JSON structure
for f in /tmp/rb.json /tmp/py.json; do sed -n '/^{/,$p' "$f" > "$f.body"; done
diff <(jq -S 'paths | join(".")' /tmp/rb.json.body) \
     <(jq -S 'paths | join(".")' /tmp/py.json.body)
```

Silence means the two trees produce structurally identical responses. Also check by hand that both
report the same `Provider`, `Model`, and `Config` header lines, and that both `stop_reason` values
are plausible for the same prompt.

Cost is roughly 700 input + 50 output tokens per run — about $0.01 for the pair at
`claude-sonnet-4-6` pricing.

---

## 8. Known drift in the Ruby step-04 reference

Port the **code**, not the docs. Recorded so they are not mistaken for port bugs:

- **No tests.** Steps 00–03 all ship Ruby specs; step 04 ships none. `tests/test_client.py` is
  therefore new design work with no Ruby counterpart to match (§7.1).
- **`Retry-After` is ignored.** A 429 or 503 carrying a `retry-after` header is retried on the
  fixed exponential schedule regardless. Mirror the behaviour; do not improve it here.
- **Transient-path message always reads "attempts".** It can only fire when `attempts > 3`, so the
  plural is never wrong — but the pluralization guard present on the non-success message is absent
  here. Mirror it.
- **`e.class` interpolation cannot reach parity** — §5.8.
- **The example makes a single call with no tool-use loop.** Claude replies `stop_reason:
  "tool_use"` and nothing dispatches the tool. That is intentional: response normalization and the
  agent loop are step 05.
- **`config.rb`'s comment drifted** from step 03 ("shipped alongside the gem/library code" →
  "shipped alongside this step") with no behavioural change.
- **`tasks/base.rb`'s new `settings.is_a?(Hash)` guard is a no-op for the port.** The Python tree
  added the same guard back in step 00, deliberately diverging from Ruby's `NoMethodError`. Ruby
  has now caught up, so the trees agree and there is nothing to port — only a stale comment in
  `tasks/base.py` to correct.

---

## 9. Ruby-side changes required before porting

**9.1 — `PROMPTS_DIR` off-by-one (was blocking; fixed 2026-08-03).**

`ruby/04_api_client/lib/boukensha/config.rb:13` resolved three levels up from `lib/boukensha/` to
`week1_baseline/ruby/prompts`, which does not exist. `Tasks::Player.system_prompt` returned `None`,
the payload sent `system: nil`, and the API rejected it:

```
400 invalid_request_error: "system: Input should be a valid array"
```

Step 03's `config.rb` had the path right, so this was a step-04 regression, not the recurring
`BOUKENSHA_DIR` bug from steps 01–03.

```diff
- PROMPTS_DIR = File.expand_path("../../../prompts", __dir__).freeze
+ PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze
```

Applied; `bin/ruby/04_api_client` now returns a valid response. **The Python port must not carry
the bug forward** — copy `config.py` from `python/03_prompt_builder`, which was always correct.

**9.2 — Nothing else outstanding.** `examples/example.rb:1` already resolves `BOUKENSHA_DIR` four
levels up to the repo root, so steps 01–03's recurring path bug is absent here.

**9.3 — Worth checking separately (not blocking this port).** Steps 00–03 should be audited for
the same `PROMPTS_DIR` regression before the next step; it appeared once and may recur.

---

## 10. Notes

- `Client.call` returns the **raw provider dict**, not a `Message`. Resisting the urge to normalize
  it here is the point — that is step 05, per `ITERATIONS.md` §4.
- The `_Response` shim (§5.1) is the only structure in the Python tree with no Ruby counterpart.
  It earns its place by keeping `call` diffable against `client.rb`; if a future step adds
  streaming, revisit whether it should become a real type.
- With `Client` in place, the five backends stop being dead code for the first time. Any
  transcription error from step 03 will now surface as a live 4xx rather than a silent payload
  difference — a useful reason to run the §7.2 parity check against more than just Anthropic if a
  second provider key is ever available.
