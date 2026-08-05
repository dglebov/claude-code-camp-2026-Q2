"""Port of `ruby/10_standard_tool_library/lib/boukensha/agent.rb`.

The loop that turns a single API call into a conversation that runs itself:

    call → parse → is it a tool call?
                     yes → dispatch, append the result, go again
                     no  → return the text

`Agent` is provider-agnostic. It only ever sees the normalized shape `parse_response` returns,
which is why nothing here branches on which backend is in play.
"""

from .errors import ApiError
from .logger import Logger


class Agent:
    # Default iteration ceiling. The *enforced* value comes from the max_iterations constructor
    # argument (sourced from Config at the run/repl path), which falls back to this constant.
    # 0 (or None) disables the ceiling.
    #
    # Deliberately a second constant despite Tasks::Base.DEFAULT_MAX_ITERATIONS holding the same
    # number — Ruby declares both independently, so both are transcribed (plan §8).
    MAX_ITERATIONS = 25

    # The wind-down call is deliberately short and cheap.
    WRAP_UP_OUTPUT_TOKENS = 400
    WRAP_UP_DIRECTIVE = (
        "You have reached your action limit for this turn. Do not call any more tools.\n"
        "Briefly summarize what you accomplished, what is still unfinished, and the\n"
        "single next action you would take."
    )

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger=None,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
    ):
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        # Ruby's `logger: Logger.new` builds a fresh logger per Agent. A Python default of
        # `logger=Logger()` would build ONE at import time — shared by every Agent, and opening a
        # log file as a side effect of importing this module (plan §5.10).
        self._logger = logger if logger is not None else Logger()
        self._max_iterations = self._resolve_max_iterations(task_settings, max_iterations)
        self._max_output_tokens = self._resolve_max_output_tokens(task_settings, max_output_tokens)
        self._iteration = 0

    def run(self):
        while True:
            # Limits are *trigger thresholds*, not hard caps: once we reach one we stop starting
            # new work iterations and make exactly one terminal wind-down call instead of raising.
            if self._iteration_limit_reached():
                self._logger.limit_reached(kind="max_iterations", n=self._iteration, max=self._max_iterations)
                return self._wrap_up("max_iterations")

            self._iteration += 1
            self._logger.iteration(n=self._iteration, max=self._max_iterations)
            self._logger.prompt(messages=self._context.messages, tools=self._context.tools)

            response = self._client.call(**self._call_opts())
            self._logger.raw(data=response)
            parsed = self._builder.parse_response(response)

            if parsed["stop_reason"] == "tool_use":
                self._handle_tool_calls(parsed["content"], response)
            else:
                text = self._extract_text(parsed["content"])
                self._log_response(text=text, response=response)
                self._logger.turn_end(reason="completed", iterations=self._iteration)
                # New in step 08: the REPL replays this context on every turn, so the final
                # reply has to live in it. One-shot runs discard the context, which is why
                # steps 05-07 could get away with returning the text without recording it.
                self._context.add_message("assistant", text)
                return text

    # ---------- private ---------------------------------------------------

    def _resolve_max_iterations(self, task_settings, explicit):
        if explicit is not None:
            return int(explicit)
        if task_settings and hasattr(self._context.task, "max_iterations"):
            return self._context.task.max_iterations(task_settings)

        return self.MAX_ITERATIONS

    def _resolve_max_output_tokens(self, task_settings, explicit):
        if explicit is not None:
            return explicit
        if task_settings and hasattr(self._context.task, "max_output_tokens"):
            return self._context.task.max_output_tokens(task_settings)

        # Ruby falls back to nil here, not to a constant — unlike its iteration counterpart.
        return None

    def _iteration_limit_reached(self):
        # 0 disables the ceiling; spelled `> 0` rather than as a truthiness test to keep that
        # legible (plan §5.5).
        return self._max_iterations > 0 and self._iteration >= self._max_iterations

    def _call_opts(self):
        """Per-call options shared by every model round-trip of the turn."""
        return {"max_output_tokens": self._max_output_tokens} if self._max_output_tokens else {}

    def _wrap_up(self, reason):
        """One final, tools-disabled model call so the agent ends the turn in character rather
        than aborting. Runs *outside* the counted loop: it never re-checks the limits (so it
        cannot re-trigger) and does not increment the iteration counter. Falls back to a
        deterministic message if the call fails.
        """
        self._context.add_message("user", self.WRAP_UP_DIRECTIVE)
        try:
            # tools=[] — an empty list, never None. The backends branch on `is None`, so this is
            # what actually disables tools for this call (plan §5.9).
            response = self._client.call(tools=[], max_output_tokens=self.WRAP_UP_OUTPUT_TOKENS)
            text = self._extract_text(self._builder.parse_response(response)["content"])
        except ApiError:
            # Ruby's `rescue` sits on the whole method body, so parse_response and extract_text
            # are inside the guarded span too (plan §5.11).
            msg = self._fallback_message(reason)
            self._logger.turn_end(reason=reason, iterations=self._iteration)
            self._context.add_message("assistant", msg)
            return msg

        if not text.strip():
            text = self._fallback_message(reason)
        self._log_response(text=text, response=response)
        self._logger.turn_end(reason=reason, iterations=self._iteration)
        self._context.add_message("assistant", text)
        return text

    def _fallback_message(self, reason):
        return (
            f"I reached my {self._max_iterations}-action limit for this turn before finishing "
            f"({reason}). Ask me to continue and I'll pick up from here."
        )

    def _extract_text(self, content):
        # Ruby's bare `join` uses "" as the separator, not ", " (plan §5.7).
        return "".join(b["text"] for b in content if b["type"] == "text")

    def _handle_tool_calls(self, content, response):
        tool_calls = [b for b in content if b["type"] == "tool_use"]

        reasoning = self._extract_text(content)
        if not reasoning.strip():
            reasoning = f"(tool use — {len(tool_calls)} call{'s' if len(tool_calls) != 1 else ''})"
        self._log_response(text=reasoning, response=response)

        self._context.add_message("assistant", content)

        for block in tool_calls:
            name = block["name"]
            args = block["input"]
            use_id = block["id"]

            self._logger.tool_call(name=name, args=args)
            # New in step 06: a raised tool no longer propagates out of run(). It becomes an
            # ERROR string as the tool result, is logged with ok=False, and the loop continues.
            try:
                result = self._registry.dispatch(name, args)
                self._logger.tool_result(name=name, result=result, ok=True)
            except Exception as error:  # noqa: BLE001 — mirrors Ruby's `rescue StandardError`
                result = f"ERROR: {type(error).__name__}: {error}"
                self._logger.tool_result(name=name, result=result, ok=False, error=str(error))

            self._context.add_message("tool_result", str(result), tool_use_id=use_id)

    def _log_response(self, *, text, response):
        self._logger.response(
            text=text,
            usage=self._normalized_usage(response),
            stop_reason=response.get("stop_reason"),
            task=self._context.task,
            backend=self._builder.backend,
        )

    def _normalized_usage(self, response):
        if response.get("usage"):
            return response["usage"]
        if response.get("usageMetadata"):
            return response["usageMetadata"]

        usage = {k: response[k] for k in ("prompt_eval_count", "eval_count") if k in response}
        return usage or None
