"""Port of `ruby/11_tui/lib/boukensha/tui.rb`.

Tui wraps a `Repl` and replaces its line-oriented stdout with a four-zone display. The Repl keeps
owning session logic — turn counting, /commands, Agent dispatch — and this class only renders and
routes input:

    ┌──────────────────────────────────────────────┐
    │  conversation log (scrollable)               │
    ├──────────────────────────────────────────────┤
    │  ⟳ live progress line (idle text when calm)  │
    ├──────────────────────────────────────────────┤
    │  boukensha> input box                        │
    ├──────────────────────────────────────────────┤
    │  status line (always on)                     │
    └──────────────────────────────────────────────┘

**Why this is a substitution, not a translation.** Ruby drives bubbletea + lipgloss + bubbles —
Ruby bindings over Go's Charm libraries. Nothing binds those from Python, so the framework is
Textual. The mapping, for reading the two files side by side:

    Bubbletea (Ruby)                     Textual (Python)
    --------------------------------     ---------------------------------------
    Bubbletea::Runner#run                App.run()
    init -> Bubbletea.tick(0.06)         set_interval(0.06, self._tick)
    update(msg) case on message class    on_key / on_resize / interval callback
    view -> join four rendered strings   compose() yields four widgets, updated in place
    Bubbles::Viewport                    RichLog (scrollback, wrapping, auto_scroll)
    Bubbles::TextArea                    Input
    Lipgloss::Style                      Textual CSS (see CSS below)
    Bubbletea.quit                       self.exit()
    @dirty + sync_viewport               (not needed — Textual redraws on mutation)

Two Ruby mechanics disappear here and that is deliberate, not an omission: the `@dirty` flag and
the explicit `view` string join are Bubbletea's redraw model, and emulating them inside a
framework that redraws on mutation would add code that does nothing.

**Threading.** Ruby runs a turn in `Thread.new` and pushes events onto a `Queue` the tick drains.
That shape is kept exactly — `queue.Queue` plus a drain on each tick — because Textual is
asyncio-based and *not* thread-safe for widget mutation. The turn runs in a Textual thread worker;
both `Repl.on_output` and `Logger.subscribe` fire on that worker thread, so both do nothing but
put an item on the queue. Every widget touch happens on the UI thread inside `_tick`.

**ESC / cancellation.** See `agent.py`. Ruby aborts the turn with `Thread#raise(Interrupt)`;
Python cannot do that safely, so ESC sets a `threading.Event` the agent loop checks between
iterations. The turn therefore stops at the next iteration boundary rather than mid-request.
"""

import queue
import threading
import time
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, RichLog, Static

from .agent import Agent
from .errors import Interrupted
from .repl import PROMPT

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
TICK_SECONDS = 0.06

# Thresholds for context-usage colour coding, as percentages of the window.
CTX_WARN_PCT = 70
CTX_ALERT_PCT = 85


def fmt_tokens(n):
    """1500 -> '1.5k'. Ruby's `fmt_tokens`, including the sub-1000 passthrough."""
    n = int(n or 0)
    return f"{round(n / 1000.0, 1)}k" if n >= 1000 else str(n)


class Tui(App):
    # Lipgloss styles are set inline per-render in Ruby; Textual wants them declared once. The
    # colours are the same four: cyan for live progress, bright black for idle, white on bright
    # black for the status bar.
    CSS = """
    Screen { layout: vertical; }
    #conversation { height: 1fr; border: none; background: $surface; }
    #progress { height: 1; padding: 0 1; }
    #progress.-active { color: #00ffff; }
    #progress.-idle { color: #808080; }
    /* Context-pressure colours. Ruby picks a lipgloss colour per render; Textual wants classes,
       so the threshold decides which class is set rather than which hex is inlined. */
    #progress.-warn { color: #ffcc00; }
    #progress.-alert { color: #ff5555; }
    #inputrow { height: 3; }
    #prompt { width: auto; padding: 1 0 0 1; color: #00ff00; text-style: bold; }
    #status { height: 1; padding: 0 1; color: #ffffff; background: #808080; }
    """

    BINDINGS: ClassVar = [
        Binding("ctrl+c", "quit_app", "Quit", priority=True),
        Binding("ctrl+d", "quit_app", "Quit", priority=True),
        Binding("escape", "interrupt", "Interrupt", priority=True),
        Binding("ctrl+l", "clear_history", "Clear", priority=True),
        Binding("pageup", "scroll_up", "Scroll up", priority=True),
        Binding("pagedown", "scroll_down", "Scroll down", priority=True),
    ]

    def __init__(self, repl):
        super().__init__()
        self._repl = repl
        # NOT self._context: Textual's App already owns that name (App._context is an internal
        # context-manager factory), and shadowing it makes run() fail with
        # "'Context' object is not callable" before a single frame is drawn.
        self._repl_context = repl.context
        self._events = queue.Queue()

        self._turn_count = 0
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._cancel = None
        self._turn_running = False

        self._live = self._idle_live()

    @staticmethod
    def _idle_live():
        return {
            "active": False,
            "spinner_idx": 0,
            "start_time": None,
            "elapsed": 0,
            "current_action": "idle",
            "iteration": 0,
            "tool_call_count": 0,
            "turn_input_tokens": 0,
            "turn_output_tokens": 0,
        }

    # ---------- layout -----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield RichLog(id="conversation", wrap=True, markup=False, auto_scroll=True)
        yield Static("", id="progress", classes="-idle")
        # Ruby draws `Repl::PROMPT` in bold green immediately left of its textarea; the same
        # constant is reused here so the two front-ends show the same prompt string.
        with Horizontal(id="inputrow"):
            yield Static(PROMPT, id="prompt")
            yield Input(placeholder="Type a message…", id="entry")
        yield Static("", id="status")

    def on_mount(self):
        # Both callbacks fire on the worker thread — see the module docstring. They must not
        # touch widgets, only enqueue.
        self._repl.on_output(lambda text: self._events.put({"phase": "output", "text": text}))
        self._repl.logger.subscribe(lambda event: self._events.put(event))

        self._write(self._repl.banner())
        self.query_one("#entry", Input).focus()
        self.set_interval(TICK_SECONDS, self._tick)

    # ---------- the tick: drain, animate, repaint --------------------------

    def _tick(self):
        self._drain_events()

        if self._live["active"]:
            self._live["spinner_idx"] = (self._live["spinner_idx"] + 1) % len(SPINNER_FRAMES)
            if self._live["start_time"]:
                self._live["elapsed"] = time.monotonic() - self._live["start_time"]

        self._render_progress()
        self._render_status()

    def _drain_events(self):
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                return
            self._handle_event(event)

    def _handle_event(self, event):
        # Ruby writes `event[:phase] || event["phase"]` because its log events carry symbol keys
        # while a JSON round-trip yields strings. Python's logger emits string keys throughout,
        # so the double lookup would be noise.
        phase = str(event.get("phase") or "")

        if phase == "output":
            self._write(event["text"])
        elif phase == "iteration":
            self._live["iteration"] = int(event.get("n") or 0)
            self._live["current_action"] = "Thinking…"
        elif phase == "tool_call":
            self._live["current_action"] = f"Calling tool: {event.get('name')}"
            self._live["tool_call_count"] += 1
        elif phase == "tool_result":
            self._live["current_action"] = "Awaiting result…"
        elif phase == "response":
            usage = event.get("usage")
            if usage:
                itu = int(usage.get("input_tokens") or 0)
                otu = int(usage.get("output_tokens") or 0)
                self._live["turn_input_tokens"] += itu
                self._live["turn_output_tokens"] += otu
                self._session_input_tokens += itu
                self._session_output_tokens += otu
        elif phase == "turn_complete":
            self._live["active"] = False
            self._turn_running = False
            self._turn_count += 1
        elif phase == "turn_interrupted":
            self._live["active"] = False
            self._turn_running = False
            self._write("[interrupted]")
        elif phase == "turn_error":
            self._live["active"] = False
            self._turn_running = False
            self._write(f"[error] {event.get('error')}")

    # ---------- rendering --------------------------------------------------

    def _write(self, text):
        self.query_one("#conversation", RichLog).write(str(text))

    def _render_progress(self):
        widget = self.query_one("#progress", Static)
        if self._live["active"]:
            frame = SPINNER_FRAMES[self._live["spinner_idx"]]
            itok = fmt_tokens(self._live["turn_input_tokens"])
            otok = fmt_tokens(self._live["turn_output_tokens"])
            widget.set_classes("-active")
            widget.update(
                f"{frame} {self._live['current_action']}  "
                f"(iter {self._live['iteration']}/{Agent.MAX_ITERATIONS} · "
                f"{int(self._live['elapsed'])}s · ↑ {itok} · ↓ {otok} · "
                f"{self._live['tool_call_count']} calls)"
            )
        else:
            pct = self._repl_context.usage_pct()
            used = fmt_tokens(self._repl_context.current_tokens)
            window = fmt_tokens(self._repl_context.context_window)
            widget.set_classes(self._ctx_class(pct))
            widget.update(
                f"  [ready]   ctx {used} / {window} ({pct}%)   {self._turn_count} turns"
            )

    def _render_status(self):
        ver = self._repl.version or "?.?.?"
        model = self._repl.model or "(model)"
        pct = self._repl_context.usage_pct()
        used = fmt_tokens(self._repl_context.current_tokens)
        window = fmt_tokens(self._repl_context.context_window)
        tools = self._repl_context.tool_count
        # Local wall clock, matching Ruby's Time.now.strftime.
        clock = time.strftime("%H:%M:%S")
        # A bare space when calm, so the bar does not change width as the marker appears.
        indicator = " ⚠ " if pct >= CTX_ALERT_PCT else " "
        self.query_one("#status", Static).update(
            f" boukensha v{ver} · {model}  ·  ctx {used}/{window} ({pct}%){indicator}·  "
            f"{tools} tools  ·  {clock} "
        )

    @staticmethod
    def _ctx_class(pct):
        """Which colour class the progress line wears. Ruby's ctx_color, as a Textual class."""
        if pct >= CTX_ALERT_PCT:
            return "-alert"
        if pct >= CTX_WARN_PCT:
            return "-warn"
        return "-idle"

    # ---------- input ------------------------------------------------------

    def on_input_submitted(self, message: Input.Submitted):
        entry = message.value.strip()
        message.input.value = ""
        if not entry:
            return

        if entry.startswith("/"):
            result = self._repl.handle_command(entry)
            if result == "quit":
                self.exit()
                return
            if entry == "/clear":
                self._turn_count = 0
            if result:
                return
            # Not a recognised command: fall through and let the agent see it, exactly as the
            # plain REPL does.

        self._write(f"> {entry}")
        self._launch_turn(entry)

    # ---------- the agent turn ---------------------------------------------

    def _launch_turn(self, entry):
        if self._turn_running:
            # Ruby has the same guard implicitly — its textarea is the only input and a turn
            # blocks it. Textual keeps the Input live, so say so rather than interleaving turns.
            self._write("[busy — press ESC to interrupt the current turn]")
            return

        self._live = self._idle_live()
        self._live.update(
            {"active": True, "start_time": time.monotonic(), "current_action": "Thinking…"}
        )
        self._turn_running = True
        self._cancel = threading.Event()
        self._run_turn_worker(entry, self._cancel)

    def _run_turn_worker(self, entry, cancel):
        # thread=True because run_turn is blocking, synchronous code (HTTP, subprocess I/O).
        # Running it on the event loop would freeze the UI, spinner included.
        def work():
            try:
                self._repl.run_turn(entry, cancel=cancel)
            except Interrupted:
                self._events.put({"phase": "turn_interrupted"})
            except Exception as error:  # noqa: BLE001 — Ruby's bare `rescue => e`
                self._events.put({"phase": "turn_error", "error": str(error)})
            finally:
                self._events.put({"phase": "turn_complete"})

        self.run_worker(work, thread=True, exclusive=False)

    # ---------- key actions ------------------------------------------------

    def action_quit_app(self):
        self.exit()

    def action_interrupt(self):
        if self._cancel is not None and self._turn_running:
            self._cancel.set()

    def action_clear_history(self):
        self._repl.handle_command("/clear")
        self._turn_count = 0

    def action_scroll_up(self):
        self.query_one("#conversation", RichLog).scroll_up(animate=False)

    def action_scroll_down(self):
        self.query_one("#conversation", RichLog).scroll_down(animate=False)
