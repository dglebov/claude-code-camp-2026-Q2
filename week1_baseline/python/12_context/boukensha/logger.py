"""Port of `ruby/11_tui/lib/boukensha/logger.rb`.

Structured session logging: one JSON object per line, appended to
`.boukensha/sessions/<session-id>.jsonl`.

Step 05's agent narrated to stdout. This replaces that entirely — `Agent` no longer prints
anything, so the console shows only the example's header and the final response while the full
trace goes to disk.

Ten event kinds: session_start, iteration, limit_reached, turn_end, prompt, tool_call,
tool_result, response, raw (debug-only), and close.
"""

import json
import os
import re
import secrets
from datetime import UTC, datetime


class Logger:
    DEFAULT_SESSION_DIR = "sessions"

    def __init__(self, session_id=None, dir=None, log=None, snapshot=None):
        # `dir` shadows the builtin, matching Ruby's keyword name. Deliberate — the call sites in
        # the example and tests read `dir=` in both trees.
        self._session_id = session_id or self._generate_session_id()
        self._path = log or os.path.join(dir or self._default_dir(), f"{self._session_id}.jsonl")

        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        # Ruby opens an append handle in the constructor and holds it for the object's life.
        # `close` exists but the example never calls it; every write is flushed, so nothing is
        # lost and the handle is released at process exit. Deliberately not a context manager —
        # that would change the call shape the example uses.
        self._log_io = open(self._path, "a")  # noqa: SIM115 — see the comment above
        # Lazily created, mirroring Ruby's `@subscribers ||= []` guarded by `&.each`. Not an
        # eager [] — the absence-vs-empty distinction is what the Ruby's safe-navigation tests.
        self._subscribers = None
        self._write_log({"phase": "session_start", **(snapshot or {})})

    @property
    def session_id(self):
        return self._session_id

    @property
    def path(self):
        return self._path

    def iteration(self, *, n, max):
        self._write_log({"phase": "iteration", "n": n, "max": max})

    def turn(self, *, n):
        # New in step 07 and never called — `agent.py` is byte-identical to step 06's, so nothing
        # emits a "turn" phase (step-07 plan §8).
        self._write_log({"phase": "turn", "n": n})

    def limit_reached(self, *, kind, n, max):
        self._write_log({"phase": "limit_reached", "kind": kind, "n": n, "max": max})

    def turn_end(self, *, reason, iterations, tokens=None):
        self._write_log({"phase": "turn_end", "reason": reason, "iterations": iterations, "tokens": tokens})

    def prompt(self, *, messages, tools, context_window=None):
        self._write_log(
            {
                "phase": "prompt",
                "context_window": context_window,
                "message_count": len(messages),
                "messages": [self._serialize_message(m) for m in messages],
                "tool_count": len(tools),
                "tools": list(tools),
            }
        )

    def tool_call(self, *, name, args):
        self._write_log({"phase": "tool_call", "name": name, "args": args})

    def tool_result(self, *, name, result, ok=True, error=None):
        self._write_log({"phase": "tool_result", "name": name, "result": str(result), "ok": ok, "error": error})

    def response(self, *, text, usage=None, stop_reason=None, backend=None):
        self._write_log(
            {
                "phase": "response",
                "text": str(text).strip(),
                "usage": usage,
                "stop_reason": stop_reason,
                **self._execution_metadata(backend=backend, usage=usage),
            }
        )

    def reasoning(self, *, text, redacted=False):
        """One event per reasoning block, so a viewer can show thinking as a first-class step.

        Note `str(text)` without .strip(): Ruby is `text.to_s` here, not `text.to_s.strip` as it
        is for response and plan. Reasoning is rendered verbatim, whitespace included.
        """
        self._write_log({"phase": "reasoning", "text": str(text), "redacted": redacted})

    def plan(self, *, text):
        """Preamble text that accompanied a tool call. Carries no usage — the tool-use
        placeholder owns the turn's usage figure, so billing is not counted twice."""
        self._write_log({"phase": "plan", "text": str(text).strip()})

    def compaction(self, *, before, dropped, context_window):
        self._write_log(
            {"phase": "compaction", "before": before, "dropped": dropped,
             "context_window": context_window}
        )

    def raw(self, *, data):
        # Deferred import: `boukensha/__init__.py` imports this module, so a module-level import
        # of the package would be circular. Ruby has no equivalent problem — it resolves
        # `Boukensha.debug?` at call time. This mirrors that timing.
        from . import is_debug

        if not is_debug():
            return

        self._write_log({"phase": "raw", "data": data})

    def subscribe(self, block):
        # New in step 07 and never called — a pub/sub hook with no subscribers anywhere in the
        # tree. Ruby takes a block; Python takes any callable.
        if self._subscribers is None:
            self._subscribers = []
        self._subscribers.append(block)

    def close(self):
        if self._log_io is not None:
            self._log_io.close()

    # ---------- private ---------------------------------------------------

    def _default_dir(self):
        from . import config

        return os.path.join(config().dir, self.DEFAULT_SESSION_DIR)

    def _write_log(self, event):
        self._log_io.write(json.dumps({**event, "session_id": self._session_id, "at": self._now()}) + "\n")
        self._log_io.flush()
        # After the write and flush, and with the ORIGINAL event — Ruby's `event.merge(...)`
        # returns a new hash, so the session_id/at envelope never reaches a subscriber.
        if self._subscribers is not None:
            for subscriber in self._subscribers:
                subscriber(event)

    def _now(self):
        # Ruby's Time#iso8601 renders whole seconds and a "Z" for UTC. Python's isoformat would
        # give microseconds and "+00:00"; trimmed so the two logs read the same to a human.
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _generate_session_id(self):
        # Ruby uses Time.now.utc here but Time.now (local) in _write_log. The asymmetry is
        # mirrored. SecureRandom.hex(4) -> secrets.token_hex(4): 4 bytes, 8 hex characters.
        return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"

    def _serialize_message(self, msg):
        # `content` may be a list of blocks for assistant turns since step 05; json handles it.
        return {"role": msg.role, "content": msg.content}

    def _execution_metadata(self, *, backend, usage):
        # Ruby step 12 dropped this method wholesale; restored on both sides because log_viz
        # renders cost/model/provider chips from these fields. The `task` field is genuinely gone
        # — step 12 deleted the task classes.
        if not (backend or usage):
            return {}

        tokens = self._usage_tokens(usage)
        metadata = {
            "provider": self._provider_name(backend),
            "model": getattr(backend, "model", None),
            "usage_unit": backend.usage_unit if backend is not None and hasattr(backend, "usage_unit") else None,
            "usage_level": backend.usage_level if backend is not None and hasattr(backend, "usage_level") else None,
            "input_tokens": tokens["input"],
            "output_tokens": tokens["output"],
            "cost_usd": self._estimate_cost(backend, tokens),
        }
        # Ruby's Hash#compact drops nil only. `is not None`, never truthiness — a 0 token count
        # or the 0.0 cost every local Ollama model reports must survive.
        return {k: v for k, v in metadata.items() if v is not None}

    def _provider_name(self, backend):
        if backend is None:
            return None

        # Ruby splits "Boukensha::Backends::OllamaCloud" on "::" first; type(...).__name__ is
        # already the bare class name, so only the snake_case pass is needed.
        return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", type(backend).__name__).lower()

    def _usage_tokens(self, usage):
        usage = usage or {}
        return {
            "input": self._first_integer(usage, "input_tokens", "prompt_tokens", "promptTokenCount", "prompt_eval_count"),
            "output": self._first_integer(usage, "output_tokens", "completion_tokens", "candidatesTokenCount", "eval_count"),
        }

    def _first_integer(self, hash, *keys):
        # Ruby's rescue sits on the whole method, so a bad value aborts the entire lookup rather
        # than falling through to the next key. A per-key try would be more useful and would
        # diverge — mirrored as-is.
        try:
            for key in keys:
                value = hash.get(key)
                if value is not None:
                    return int(value)
            return None
        except (ValueError, TypeError):
            return None

    def _estimate_cost(self, backend, tokens):
        if backend is None or not hasattr(backend, "estimate_cost"):
            return None
        if tokens["input"] is None or tokens["output"] is None:
            return None

        return backend.estimate_cost(input_tokens=tokens["input"], output_tokens=tokens["output"])
