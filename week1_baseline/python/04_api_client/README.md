# 04 · The API Client (Python)

Python port of `week1_baseline/ruby/04_api_client`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

Steps 00–03 assembled a request and stopped. This step puts it on the wire.

```
Context → PromptBuilder → payload → Client.call → HTTP POST → raw JSON dict
```

`Client` knows nothing about providers. URL, headers and payload all come from the builder, which
delegates to its backend — which is why five backends need no branching here.

It does **not** interpret the reply. `call()` returns the raw provider dict, exactly as Ruby does;
normalizing that into a `Message` and running the tool loop is step 05.

## `Client`

| Member | Description |
|---|---|
| `Client(builder)` | Takes a `PromptBuilder`. Nothing else. |
| `call(max_output_tokens=1024)` | POSTs, retries, raises `ApiError` on failure, returns the parsed body |
| `RETRYABLE_STATUS_CODES` | `408, 409, 429, 500, 502, 503, 504` |
| `TRANSIENT_ERRORS` | Connection-level failures worth retrying — see below |
| `MAX_RETRIES` / `BASE_RETRY_DELAY` | `3` and `0.5` seconds |
| `TIMEOUT` | `60` seconds |

### Retry schedule

Delay is `BASE_RETRY_DELAY * 2**(attempt-1)`:

| Attempt | On failure |
|---|---|
| 1 | sleep 0.5s, retry |
| 2 | sleep 1.0s, retry |
| 3 | sleep 2.0s, retry |
| 4 | raise `ApiError` |

Four requests, three sleeps, 3.5s worst case. Both failure modes converge on four attempts by
different routes: the transient path raises once `attempts > MAX_RETRIES`, while the status path
stops retrying when `attempts <= MAX_RETRIES` goes false and falls through to the non-success
raise. A non-retryable status such as 400 makes exactly one request and reports
`after 1 attempt` — singular.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/client.py` | `Client`, `_Response`, retry and backoff | `lib/boukensha/client.rb` |
| `boukensha/errors.py` | carried forward, plus `ApiError` | `lib/boukensha/errors.rb` |
| `boukensha/__init__.py` | carried forward, plus `Client` and `ApiError` | `lib/boukensha.rb` |
| `tests/test_client.py` | 36 tests | *(none — Ruby ships no specs for this step)* |
| everything else | carried forward from step 03, unchanged | |

## Differences from the Ruby original

The step-03 table still applies. New in this step, all from `net/http` versus `urllib.request`:

| Ruby | Python | Why |
|------|--------|-----|
| `http.request` returns a response for **every** status | `urlopen` **raises** `HTTPError` on non-2xx | The central gap. `_Response` converts the exception back into a value so the retry loop can inspect `status` as data, the way `client.rb` does. |
| `rescue` order is free | `except HTTPError` **must** precede `URLError` | `HTTPError` is a subclass of `URLError`. Get it backwards and every 400 burns four attempts on the transient path. |
| `Net::HTTP` defaults to 60s open / 60s read | `urlopen(..., timeout=60)` passed explicitly | `urlopen`'s default is *no* timeout. Omitting it would hang forever on a dead connection — and never retry, because nothing is raised. |
| Six-entry `TRANSIENT_ERRORS` | Six-entry tuple, enumerated | Every Ruby entry maps to an `OSError` subclass, making `except OSError` tempting. It would also retry `PermissionError` and friends, which Ruby does not. |
| Exceptions arrive bare | Most arrive as `URLError(reason=...)` | urllib buries the real error in `.reason`; a read that fails *after* headers arrive does not. Both shapes are handled. |
| One `Net::HTTP` reused across retries | A fresh connection per `urlopen` | No keep-alive is set on the Ruby side either, and retries are seconds apart. Functionally invisible. |
| `verify_mode = VERIFY_PEER` set explicitly | nothing | `urlopen` verifies by default via `ssl.create_default_context()`, which also finds system certs on every platform. The omission is deliberate, not a downgrade. |
| `response.body` is a `String` | `.read()` returns `bytes` | Decoded as UTF-8 at the boundary. |
| `e.class` → `Errno::ECONNREFUSED` | `type(e).__name__` → `ConnectionRefusedError` | The message *format* matches; the class names cannot without a translation table. |

## Known defects, carried over from Ruby

- **`Retry-After` is ignored.** A 429 or 503 carrying the header is retried on the fixed
  exponential schedule regardless.
- **The transient-path message always says "attempts".** It can only fire when `attempts > 3`, so
  the plural is never wrong — but the pluralization guard on the non-success message is absent
  here.
- **The example makes a single call with no tool loop.** Claude replies with
  `stop_reason: "tool_use"` and nothing dispatches the tool. That is step 05.

Step 03's `PromptBuilder.to_messages()` defect is still present and still pinned by
`tests/test_prompt_builder.py`.

## Run

```bash
./week1_baseline/bin/python/04_api_client
```

> **This one makes a real, billed API call** — roughly 700 input + 50 output tokens, about half a
> cent at `claude-sonnet-4-6` prices. Every prior step was offline. Needs a working
> `ANTHROPIC_API_KEY` in `.boukensha/.env`.

Expected output:

```
=== BOUKENSHA Step 4: API Client ===

Config: #<Boukensha::Config dir=/Users/you/Sites/Claude-Code-Camp/.boukensha tasks=player>
Provider: anthropic
Model: claude-sonnet-4-6
Sending request to https://api.anthropic.com/v1/messages...

Raw response:
{
  "id": "msg_01...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01...",
      "name": "list_directory",
      "input": { "path": "." }
    }
  ],
  "stop_reason": "tool_use",
  "usage": { "input_tokens": 682, "output_tokens": 53 }
}
```

Parity against Ruby compares **shape, not content** — the model's reply differs between calls, so
a plain `diff` always will too:

```bash
./week1_baseline/bin/ruby/04_api_client   > /tmp/rb.json
./week1_baseline/bin/python/04_api_client > /tmp/py.json
for f in /tmp/rb.json /tmp/py.json; do sed -n '/^{/,$p' "$f" > "$f.body"; done
diff <(jq -S 'paths | join(".")' /tmp/rb.json.body) <(jq -S 'paths | join(".")' /tmp/py.json.body)
```

## Test

```bash
cd week1_baseline/python
uv run pytest 04_api_client
```

203 tests: 167 carried forward from step 03, 36 new for `Client`. All offline — the network is
stubbed by patching `boukensha.client.urlopen`, and `time.sleep` is patched alongside it so the
suite asserts the backoff schedule without waiting 3.5 seconds for it.
