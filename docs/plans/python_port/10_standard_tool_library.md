# Python Port Plan — Step 10 · A Standard Tool Library (MCP Host)

Port `week1_baseline/ruby/10_standard_tool_library` to
`week1_baseline/python/10_standard_tool_library`.

**Scope:** week1 only, step 10 only. Builds on the completed step-08 port; reuses
the shared environment at `week1_baseline/python/` (no new venv, no new
dependencies).

**Prerequisites:** the Ruby reference was fixed on 2026-08-03/05 and runs end to
end; `mud_manager` 0.2.0 is installed with `mud-manager` on `PATH`.

**Status:** plan only. Nothing written. Awaiting review.

This is the first step where the Python tree comes out **cleaner than the Ruby
one**, and the first where a Ruby file is deliberately *not* ported. Both for the
same reason, and it is the reason the MCP layer exists.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Step 09 | **Skipped**, per `ITERATIONS.md` §09. So this port folds the 08→09 *and* 09→10 deltas at once (§2). |
| `Tools::Mud` (480 lines, 27 tools) | **Not ported.** It is `require "mud_manager"` — a Ruby gem with no Python equivalent. Python reaches the MUD through `mcp_servers:` instead. §5.1. |
| Gem, `bin/boukensha`, `boukensha_loader.rb`, gemspec | **Skipped**, they belong to step 09. Python keeps the launcher-plus-example shape it has used since step 00. |
| `Tools::FileSystem`, `Tools::Shell` | **Ported.** Pure stdlib on both sides. |
| `Mcp::Client`, `Tools::Mcp` | **Ported.** The point of the step. |
| Directory name | `10_standard_tool_library` — matches Ruby, leaves the 09 gap visible rather than renumbering. |
| `dotenv` | **Keep `env_file.py`.** Ruby switched to the `dotenv` gem in step 09; adding a Python dependency to mirror a skipped step is not worth it. |
| 401 error message | **Open — §9.** Ruby 08 had it, Ruby 09 deleted it, Python 08 has it. Needs a ruling. |
| Structure | Mirror Ruby 1:1 **except** `tools/mud.py`, which does not exist. |
| Environment | Shared `.venv`. No new dependencies. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/10_standard_tool_library/`. Because step
09 was skipped, the delta is against **Python step 08**, and some changes
originate in the step the Python tree never saw.

### New in this step

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/tools/file_system.rb` | 148 lines, 6 tools, path containment | `boukensha/tools/file_system.py` |
| `lib/boukensha/tools/shell.rb` | 71 lines, 1 tool, timeout + allow-list | `boukensha/tools/shell.py` |
| `lib/boukensha/mcp/client.rb` | 156 lines. Spawn, handshake, `tools/list`, `tools/call` | `boukensha/mcp/client.py` |
| `lib/boukensha/tools/mcp.rb` | 100 lines. Registry bridge, prefixes, collisions | `boukensha/tools/mcp.py` |
| `lib/boukensha.rb` → `working_dir:` / `mcp_servers` wiring | Registration order in `run`/`repl` | `boukensha/__init__.py` |

### Changed vs Python step 08 — **originating in step 09** (skipped)

| File | Delta |
|---|---|
| `config.py` | `PROMPTS_DIR` unchanged, but `_resolve_dir` gains the **cwd walk-up tier** (env var → nearest `.boukensha` at or above cwd → `~/.boukensha`). Python 08 has a cwd-only middle tier; this replaces it with the walk-up. |
| `repl.py` | Banner reworked: drops the `✓/✗ API key` and config-dir-exists indicators, adds aligned `config:` / `provider:` / `model:` lines. |
| `client.py` | Ruby dropped the 401 branch here. **Do not port that removal without a ruling** — §9. |
| `version.py` | `0.8.0` → `0.10.0` (0.9.0 never exists in this tree). |

### Changed vs Python step 08 — **originating in step 10**

| File | Delta |
|---|---|
| `context.py` | `working_dir` constructor arg, carried as metadata. |
| `tool.py` | `Tool` gains `required`; `required_keys` returns `required or parameters.keys()`. |
| `registry.py` | `tool(..., required=None)`; new `registered?` → `registered()`. |
| `backends/*.py` (×5) | `required` in the schema comes from `tool.required_keys`, not every key. |
| `config.py` | `mcp_servers` reader with normalisation (string keys, str-coerced env). |
| `repl.py` | Banner gains a `mud:` line with a TCP reachability probe. |
| `__init__.py` | `working_dir`, `allowed_commands`, `shell_timeout`, `mcp_servers` wiring; clients closed in `finally`. |

### Carried forward unchanged

Everything else: `agent.py`, `prompt_builder.py`, `logger.py`, `message.py`,
`errors.py`, `run_dsl.py`, `env_file.py`, `tasks/`.

---

## 3. What step 10 actually adds

Two things, and for Python they pull in opposite directions.

**A standard library of tools.** The agent stops needing tools hand-registered
per run: filesystem and shell arrive automatically when `working_dir` is set.

**An MCP host.** Any capability can be declared in `settings.yaml` and appears as
tools, with no code change. `Mcp::Client` and `Tools::Mcp` contain no knowledge
of what any server does.

The Ruby step has a third thing the Python one cannot have: `Tools::Mud`, wiring
the `mud_manager` gem straight into the registry. **Python has no way to load a
Ruby gem.** That is exactly the constraint `docs/plans/mud_manager/generic_interfacing.md`
was written about, and MCP is the answer already built and verified.

So the Python tree ends up where `ITERATIONS.md` §10 says the Ruby tree is
*heading* — no built-in MUD module, gameplay purely over MCP — not by discipline
but because the shortcut is unavailable. Worth stating plainly in the step README:
the Python port is the proof the MCP layer works.

---

## 4. Target layout

```
week1_baseline/python/10_standard_tool_library/
  boukensha/
    mcp/
      __init__.py
      client.py            # NEW — stdio JSON-RPC client
    tools/
      __init__.py
      file_system.py       # NEW — 6 tools
      shell.py             # NEW — 1 tool
      mcp.py               # NEW — registry bridge
      (no mud.py — see §5.1)
    __init__.py            # + working_dir / mcp_servers wiring
    config.py              # + walk-up tier, + mcp_servers
    context.py             # + working_dir
    tool.py                # + required / required_keys
    registry.py            # + required=, registered()
    repl.py                # + banner rework, mud: line
    backends/*.py          # required_keys in the schema
    version.py             # 0.10.0
    …                      # rest copy-forward
  examples/example.py      # MCP-driven MUD demo
  tests/
    test_tools_file_system.py   # NEW
    test_tools_shell.py         # NEW
    test_mcp_client.py          # NEW
    test_tools_mcp.py           # NEW
    test_config.py              # + walk-up, + mcp_servers
    test_tool.py                # + required_keys
    test_registry.py            # + registered(), required=
    test_repl.py                # + banner
    …
```

Plus `week1_baseline/bin/python/10_standard_tool_library`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 `Tools::Mud` cannot be ported — the defining constraint

`tools/mud.rb` line 1 is `require "mud_manager"`. There is no Python equivalent
and writing one means reimplementing a stateful telnet client, an IAC stripper
and a CircleMUD login state machine — rejected in the exploration doc §4 Option 1.

Python gets the same 27-plus tools by declaring the MCP server:

```yaml
mcp_servers:
  - name: mud
    command: mud-manager
    args: ["--mcp"]
    env: { MUD_HOST: localhost, MUD_PORT: "4000", … }
```

Consequences to handle rather than discover:

- **No prefix is needed.** The Ruby tree needs `prefix: mud` to avoid colliding
  with its built-in `look`/`move`/`attack`. Python has no built-ins to collide
  with, so its tools are the bare names — meaning **Ruby and Python tool names
  differ by design**, and any parity check comparing tool *names* must account
  for it.
- **No `mud:` keyword** on `run`/`repl`, no `mud_*` Config readers, no
  `mud_opts_from_config`. Do not port them; they exist only to serve `Tools::Mud`.
- **The banner's `mud:` line** has no `@mud` hash to read. Either drop the line
  (diverging from Ruby's banner) or derive host/port from the MCP server's `env`
  block. §7.3 treats this as a known, documented parity difference.

### 5.2 `Open3.popen3` → `subprocess.Popen`, and the deadlock

Ruby's `popen3` hands back three pipes and a wait thread. Python's equivalent is
`subprocess.Popen(..., stdin=PIPE, stdout=PIPE, text=True, bufsize=1)`.

Two traps that do not exist on the Ruby side:

1. **`bufsize=1` needs `text=True`** to mean line buffering. Without it the
   handshake can sit in a buffer and the host waits forever on a response the
   server already wrote.
2. **Never `proc.stderr.read()` on a live process.** It blocks until the pipe
   closes, i.e. until the server exits — which it will not, because it is waiting
   for the request that the blocked host has not sent. Ruby's `read_nonblock`
   with a rescue has no direct Python analogue that is portable; drain stderr on
   a thread, or leave it inherited so server errors land on the terminal. **Pick
   one and document it** — this is the single most likely way this port hangs.

`Client.close` must `terminate()` then `wait(timeout=…)` then `kill()`. Ruby's
`@wait.join(1)` followed by `Process.kill("TERM", …)` is the same intent.

### 5.3 Dynamic registration — the Registry's decorator does not fit

`Registry.tool` in Python is a **decorator**; every existing tool is registered
with `@registry.tool("name", …)` over a `def`. MCP tools are discovered at
runtime and their handler is a closure, so there is no `def` to decorate.

The decorator already returns a decorator, so the call form works:

```python
registry.tool(local_name, description=…, parameters=…, required=…)(handler)
```

That is legal but reads oddly. Decide once and apply consistently: either use the
call form as above, or add a small `register_callable(...)` alias on `Registry`.
The Ruby side has no such split because `registry.tool(...) { |**args| }` is one
form.

### 5.4 Path containment: `File.expand_path` vs `Path.resolve`

`Tools::FileSystem` rejects absolute paths and `..` escapes by expanding and
comparing against the root. **`File.expand_path` does not resolve symlinks;
`Path.resolve()` does.**

So a symlink inside the working directory pointing outside it is *allowed* by
Ruby and *rejected* by a naive Python port — or, if `os.path.abspath` is used
instead, allowed by both while `Path.resolve` would have caught it. The two
trees will disagree on this case whichever way it goes.

Mirror Ruby with `os.path.abspath` + `os.path.normpath` (no symlink resolution),
document the divergence, and **write the symlink test in both directions** so
the behaviour is pinned rather than incidental. Note that the stricter choice is
arguably the better security posture; matching Ruby is the diffability choice.
This is a real trade-off, not an oversight.

### 5.5 `Open3.capture2e` with a timeout → `subprocess.run`

`Tools::Shell` runs a command with a timeout and an optional allow-list.
`subprocess.run(..., capture_output=True, text=True, timeout=…, cwd=…)` covers
it, raising `TimeoutExpired` where Ruby raises its own error. Return the same
shaped string on timeout so the model sees the same thing.

**Correction, found during execution: `shell=True` IS required.** This plan
originally said to avoid it. That was wrong on the facts — Ruby passes
`capture2e` a *string*, and Ruby hands a string containing shell metacharacters
to the shell. Verified against the reference: `echo A; echo B` runs both and
`echo hi | tr a-z A-Z` pipes. Splitting the string in Python would silently break
every pipeline and redirection the Ruby tree accepts.

The consequence stands, and belongs in both trees' documentation rather than
being quietly inherited: **`allowed_commands` is advisory, not a security
boundary.** It checks only the first token, so with `allowed_commands=["git"]`
the command `git; rm -rf ~` passes and the shell runs both halves. Pre-existing
in Ruby step 10, not introduced by the port — but a list named "allowed commands"
reads like a sandbox and is not one.

### 5.6 `Struct` member → dataclass field

`Tool` gains a fifth member with a default. If Python's `Tool` is a dataclass,
`required: list | None = None` must come after every non-default field. Check the
current definition before assuming a position is free.

### 5.7 Ruby `warn` → Python `warnings` or stderr

`Tools::Mcp` calls `warn` when a `required: false` server fails to start. Use
`print(..., file=sys.stderr)` rather than the `warnings` module — this is
operator output, not a deprecation, and `warnings` deduplicates by default, which
would hide a second failing server.

---

## 6. Implementation steps

1. **Verify the Ruby baseline** — `./week1_baseline/bin/ruby/check-paths`, then
   `./week1_baseline/mcp/verify` (35 checks). Confirm `mud-manager tools` lists 34.
2. **Copy forward** step 08 into `10_standard_tool_library/`, repointing docstrings
   at `ruby/10_standard_tool_library`. Confirm green before changing anything.
3. **Fold the step-09 changes** (§2): `config.py` walk-up tier, `repl.py` banner,
   `version.py` → `0.10.0`. Leave `client.py` pending the §9 ruling.
4. **`tool.py` / `registry.py`** — `required`, `required_keys`, `registered()`.
5. **`backends/*.py`** — five identical edits to use `required_keys`.
6. **`context.py`** — `working_dir`.
7. **`tools/file_system.py`** — 6 tools, containment per §5.4.
8. **`tools/shell.py`** — 1 tool, timeout and allow-list per §5.5.
9. **`mcp/client.py`** — the stdio client, per §5.2.
10. **`tools/mcp.py`** — the registry bridge, per §5.3 and §5.7.
11. **`config.py`** — `mcp_servers` reader and normalisation.
12. **`__init__.py`** — wire `working_dir` / `allowed_commands` / `shell_timeout` /
    `mcp_servers` into `run` and `repl`; close clients in `finally`.
13. **`examples/example.py`** — the MCP-driven MUD demo.
14. **Launcher** — `week1_baseline/bin/python/10_standard_tool_library`.
15. **Tests** — §7.
16. **READMEs** — step README (state §3's point explicitly), plus a row in
    `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite

*`Tools::FileSystem`* — 6 tools; relative paths resolve under the root; absolute
paths rejected; `..` escapes rejected; **the §5.4 symlink case, asserted
explicitly**; `search_files` returns `path:line:content`; missing files give an
error string rather than raising.

*`Tools::Shell`* — runs in `working_dir`; timeout produces the documented string;
allow-list permits and rejects; `allowed_commands=None` permits all; **no shell
interpretation** — assert `echo a; echo b` does not run two commands.

*`Mcp::Client`* — handshake sends `initialize` then the `notifications/initialized`
notification; `tools/list` parses; `tools/call` joins text blocks; `isError`
becomes an `ERROR:` string; a JSON-RPC `error` raises; **a notification from the
server mid-stream does not desynchronise request/response**; `close()` reaps the
process. Drive it against a scripted fake server on pipes — no subprocess needed
for most of these.

*`Tools::Mcp`* — registers discovered tools; `prefix` renames; **a collision
raises**; `required: false` downgrades a failed start to a warning and returns
`None`; optional/required parameters survive into `Tool.required_keys`; enums
survive into `parameters`.

*`Config`* — the three tiers incl. walk-up from a deep subdirectory; a `.boukensha`
*file* is not mistaken for a directory; `mcp_servers` normalises both the list and
mapping forms, coerces env values to strings.

*`Tool` / `Registry`* — `required_keys` defaults to all keys; an explicit list
wins; `registered()` is true only after registration.

```bash
cd week1_baseline/python && ./run-tests && uv run ruff check .
```

### 7.2 Cross-tree MCP proof — the one that matters

The Python host driving **the same `mud-manager --mcp` server** the Ruby host
uses, against `week1_baseline/mcp/fake_mud_server.rb`. Offline, no API call.

This is the step's thesis made testable: two harnesses in two languages, one
server, one telnet session. `week1_baseline/mcp/python_client_demo.py` already
proves raw MCP works from Python; this proves it works *through Boukensha's
host*. Worth adding as a section in `week1_baseline/mcp/verify`, or a sibling
`verify-python`.

### 7.3 Parity with Ruby

Payload parity as in earlier steps. Two **expected** differences to record rather
than chase:

- **Tool names.** Ruby prefixes MUD tools (`mud_look`) to avoid colliding with its
  built-in `Tools::Mud`; Python has no built-ins and uses bare names (`look`).
- **The banner's `mud:` line.** Ruby reads its `@mud` hash; Python has no such
  hash (§5.1).

Everything else — the banner box, command list, `/help` output, `Goodbye.` — should
diff clean, as steps 08's did.

---

## 8. Known drift in the Ruby step-10 reference

- **`Tools::Mud` still ships** though `ITERATIONS.md` §10 says built-in tool
  modules are deleted and everything arrives over MCP. The Python port skips it
  by necessity, so the trees diverge here permanently until Ruby catches up.
- **Built-in tools over-declare required parameters.** `Tools::Mud`'s `look`
  reports `required_keys == ["target", "preposition"]` though both are optional.
  `required_keys` makes this fixable; it is not fixed. Do not replicate the wart
  in the Python built-ins — declare their optional parameters honestly.
- **`mcp_servers:` is not configured** in `.boukensha/settings.yaml`. Both trees
  read it; neither currently loads a server by default.
- **`.boukensha/settings.yaml` holds a plaintext MUD password and is not
  gitignored** — only `.env` and `.boukensha/sessions/` are.

---

## 9. Ruby-side decisions required before porting

**One ruling needed, on the 401 message.**

| Tree | State |
|---|---|
| Ruby 08 | has `authentication failed (401) — check your API key` |
| Ruby 09 | **deleted it** — flagged in `ruby_step_09_runnable.md` §3.1, never ruled on |
| Ruby 10 | still absent |
| Python 08 | **has it** |

So the Python port must either delete a working error message to match Ruby, or
keep it and accept a permanent divergence. My recommendation is **restore it in
Ruby 09/10** rather than remove it from Python: it reads as an accidental revert
in a copy-forward, and a globally installed binary is *more* likely to be run
without a key, not less.

No other Ruby-side change is required. `check-paths` is green and step 10 runs.

---

## 10. Notes

- §5.1 is the first time a Ruby file is deliberately not ported. That is worth
  saying in the step README rather than leaving a reader to notice the absence:
  the Python tree reaches `ITERATIONS.md` §10's target shape because the shortcut
  does not exist for it.
- §5.2's stderr trap is the highest-risk line in this port. Wrong, it hangs the
  handshake with no error — and it will look like the server is broken.
- §5.4 is the only place the two trees will *behave* differently on the same
  input. Pin it with a test in both trees rather than letting it be incidental.
- The Python tree skips step 09 entirely, so `10_standard_tool_library` sits next
  to `08_the_repl_loop`. Leave the numbering gap; renumbering would break the
  correspondence with Ruby that every earlier plan relies on.
- Once this lands, `week1_baseline/mcp/` gains a second consumer. Its README's
  "what each language writes" table stops being a claim and becomes a
  demonstration.
