Our MudManager is written in Ruby.
In our Bootcamp, Bootcampers want to ouse their own langauge eg. Java, Python, Rust, Go.
What is the solution?
- We have to create wrapper per lang
- We make MudManager a command line tool, and other langs execute shell commands in their langs
- We implement a communication protcol
- We implement MCP as a layer


Consider that the MUD manager is managing the session for the MUD. 

## Technical Exploration

> **Implemented.** The recommendation in §5 was built and verified — see
> [`implementation.md`](implementation.md) for the architecture, protocol
> reference, and known gaps. Run `./week1_baseline/mcp/verify` (35 checks,
> offline) and `./week1_baseline/mcp/python_client_demo.py` (Python driving the
> MUD with no MUD code).
>
> Answers given to §7: session lifetime **(b)**, multiple sessions, local-only
> credentials. Reconnection and command surface were delegated and are decided
> in implementation.md §6.2 and §6.3.

### 1. One constraint decides most of this

The last line of the problem statement is the whole problem: **MudManager manages the session.**

A MUD connection is not a request/response API. It is a long-lived, stateful telnet socket carrying:

- **login state** — `Session#login` (`session.rb:169–192`) is a 7-step dance: wait for the name prompt, send name, wait for password prompt, send password, branch on `Welcome` / `Reconnecting` / `Wrong password`, send a blank line for the menu, send `1` to enter the world.
- **in-world state** — position, room, combat, inventory. All server-side, all tied to that socket.
- **asynchronous chatter** — other players talking, mobs attacking. It arrives between your commands, which is why `Session` runs a background reader thread draining into a buffer (`session.rb:198–225`).

**Therefore: any solution where a command runs in a fresh process is disqualified.** Not "slower" — wrong. Each command would re-login (7 round trips), the character would visibly disconnect and reconnect in-game between every action, and everything said while the process was dead is lost forever.

This immediately splits the four options into two that can work and one that cannot as stated.

### 2. The four options against that constraint

#### Option 1 — A wrapper per language

Ruby cannot be meaningfully embedded in Java/Python/Rust/Go, so "wrapper" here does not mean binding to our code. It means **reimplementing MudManager in each language**: the telnet client, the IAC stripper (`session.rb:233–262`), the condvar-guarded buffer, the login state machine. That is ~270 lines of genuinely tricky concurrent code, four more times.

- **Cost:** N implementations, N × maintenance, and the divergence is silent — an IAC edge case handled in Ruby but not in Go shows up as garbled text weeks later.
- **The killer:** a fix to the login dance must land in five places. In a bootcamp, four of those are maintained by students.
- **Verdict: reject.** The one honest argument for it — students learn socket programming — is not what this course teaches. They are here to build agent harnesses.

#### Option 2 — CLI tool, other languages shell out

As literally stated (`mud-manager say hello` per command), this violates §1 and cannot work.

But there is a variant that does: **a detached daemon holding the session, plus a thin CLI that talks to it.**

```
mud-manager daemon --session alice     # starts once, holds the socket
mud-manager send --session alice "look"  # thin client, exits immediately
```

Now the per-command process is fine, because it is not the thing holding the connection.

- **Biggest advantage, and it is a real one:** the barrier for the student is *zero*. Every language on the list can shell out from its standard library — `subprocess` / `exec.Command` / `std::process::Command` / `ProcessBuilder`. No dependency, no protocol client, no MCP library. For a bootcamp with mixed skill levels this matters more than it looks.
- **Costs:** process spawn per command (~10–50ms, irrelevant next to MUD latency); output is text that every student must parse; errors arrive as exit codes and stderr; and **the daemon lifecycle becomes the student's problem** — starting it, noticing it died, cleaning it up.

#### Option 3 — A communication protocol

A daemon holding the session, speaking a protocol we define over a socket.

This is the right *shape* — §1 forces a daemon, and this is the honest version of it. The question is what the protocol is. If we design a bespoke one we own: framing, request/response correlation, error semantics, versioning, and a client per language. That is a lot of work whose only output is a thing that already exists.

If instead it is **JSON over HTTP**, every language on the list has a client in its standard library or one obvious dependency, and it is debuggable with `curl`. That is a serious contender.

- **Verdict: right shape, but do not invent a new protocol.** Either use HTTP+JSON, or use Option 4 — which is this option with the protocol already chosen.

#### Option 4 — MCP as a layer

MCP is JSON-RPC 2.0 over stdio or HTTP. **It is Option 3 with the design decisions already made** — and with three properties the others lack:

1. **The tool schemas are the point.** The consumer is an LLM. Whatever we build, the agent eventually needs each MUD command as a named tool with typed parameters. MCP's `tools/list` *is* that, natively. With Options 1–3, every student writes a translation layer from our surface into their harness's tool format.
2. **Students need an MCP client anyway.** Filesystem access, shell, and every other capability arrive the same way. MUD support becomes one more `mcp_servers:` entry, not a special case.
3. **Zero MUD code in the student's language.** Not "a small client" — none. They declare a server in config.

- **Costs:** MCP is a larger spec than a line protocol; a bad stdio framing bug is unpleasant to debug; and the transport choice has a consequence we have to face (§3).
- **Status check:** `Boukensha::Mcp::Client` and `mcp_servers:` are described in `ITERATIONS.md` §10 but **do not exist in this tree** — step 10 still ships `Tools::Mud` / `FileSystem` / `Shell`, and `.boukensha/settings.yaml` has no `mcp_servers:` block. Likewise `mud-manager --mcp`: `mud_manager.gemspec:14` ships `Dir["lib/**/*.rb"]` with no `executables` and there is no `bin/`. **This is a design decision, not an integration of something already built.**

### 3. The problem nobody lists: session lifetime

MCP's stdio transport spawns the server as a **child process of the host**. Session lifetime therefore equals agent-process lifetime.

For most MCP servers that is fine — a filesystem server has nothing to lose on restart. **A MUD session has everything to lose.** A student iterating on their agent restarts it constantly; each restart means a fresh 7-step login and a visible disconnect/reconnect in-game.

Three ways out:

| | Mechanism | Cost |
|---|---|---|
| **a** | Accept it — re-login per run | Simple, but painful exactly when students iterate fastest |
| **b** | Detached daemon + thin stdio shim that proxies to it | Session survives restarts; two processes to reason about |
| **c** | MCP over HTTP against a long-lived server | Session survives; needs the host to speak HTTP transport |

**This question should be settled before any code is written**, because (b) and (c) change what gets built, and (a) is a decision to live with a daily annoyance.

### 4. What the options converge on

Strip the labels and Options 2, 3, and 4 are the same architecture:

```
        one daemon, owns the telnet session
                      │
        ┌─────────────┼─────────────┐
     CLI front-end  HTTP      MCP stdio/HTTP
     (Option 2)   (Option 3)    (Option 4)
```

They differ only in the front-end. **The daemon and session-ownership work is common to all three and is the bulk of the effort.** That reframes the decision: this is not "which of four options", it is "build the daemon, then choose front-ends" — and front-ends are cheap enough that more than one is affordable.

### 5. Recommendation

**MCP as the primary interface (Option 4), with a thin CLI front-end (Option 2's daemon variant) over the same core.**

Reasoning:

- **MCP is primary** because the product is an agent harness. The tool-schema requirement is not optional, and MCP is the only option that satisfies it without a per-language translation layer. It is also already the stated direction in `ITERATIONS.md`.
- **The CLI comes nearly free** once the daemon exists, and it earns its place twice: as a debugging tool for us (`mud-manager send "look"` beats driving JSON-RPC by hand), and as an on-ramp for a student whose language has no comfortable MCP library yet.
- **Reject Option 1** outright — N stateful telnet clients is the worst outcome available.
- **Option 3 is not rejected so much as absorbed:** it is the correct shape, and Option 4 is it with the protocol chosen and the tool-schema problem solved.

Deliberately *not* recommending we design a bespoke protocol. The only thing it buys over MCP is a smaller spec, and it costs a client per language plus the schema translation MCP gives free.

### 6. What each bootcamper actually writes

The test of any option is what lands on the student. Under the recommendation:

| Language | What they write for MUD access |
|---|---|
| Ruby | nothing — config entry |
| Python | nothing — config entry |
| Go / Rust / Java | nothing — config entry, *if* their harness has an MCP client |
| any, fallback | `exec("mud-manager", "send", "...")` — no dependency at all |

The honest caveat: "nothing" assumes their harness already speaks MCP. For students building a harness from scratch in Go or Rust, **writing that MCP client is real work** — and it is work the course arguably wants them to do anyway, since it is how they will get filesystem and shell tools too. The CLI fallback exists so that MUD access is never *blocked* on it.

### 7. Open questions to settle before designing

1. **Session lifetime** (§3) — (a), (b), or (c)? Changes what gets built.
  - b, we don't have dedicated host 
2. **Session identity.** One daemon per student, or one shared daemon with named sessions? Two bootcampers on one machine, or one student with two characters, both need an answer.
  - we should be able to hold multiple sessions 
3. **Credentials.** `login(username, password)` takes plaintext from `settings.yaml` (`mud: password: helloworld`). Note **`.boukensha/settings.yaml` is not gitignored** — only `.env` and `.boukensha/sessions/` are. Under a daemon, where do credentials live and who passes them?
  - crediantial are local, no need for extra security 
4. **Reconnection.** `Session#login` has a `Reconnecting` branch (`session.rb:183`) but nothing calls it after a drop. Does the daemon reconnect transparently, or surface a tool error?
  - up to you
5. **Which commands.** 58 primitives exist; step 10's `Tools::Mud` exposes 27. The MCP tool list is a third hand-written transcription of the same surface — worth generating all three from one table rather than maintaining three copies that can drift silently.
  - decide it yourself, pick a right option 
6. **Is there an existing implementation?** `ITERATIONS.md` refers to `mud-manager --mcp` in the past tense and points at "the omenking repo". If it exists there, this becomes a port and most of the above is moot — worth five minutes to check before spending a day designing.
 - ignore this, this is mcp is part of bootcamp and have to be implemented. 

### 8. Verification

A live CircleMUD is reachable on `localhost:4000` (confirmed by TCP connect), but the tests that matter run without it:

- **Golden transcript** — record a real login byte stream, replay against `Session` with a stub socket, assert identical commands in identical order. `mud_manager` currently ships **no tests at all**, only `examples/` requiring a live server and a real character. This is the first thing to build, because everything else leans on it.
- **Daemon** — start, attach, send, detach, reattach; assert the session survives a client disconnect. This is the §3 decision, made testable.
- **MCP** — drive the server over stdio with a scripted client (`initialize`, `tools/list`, `tools/call`) with telnet stubbed. No MUD required.
- **Cross-language proof** — one non-Ruby harness calling one MUD tool. Until that exists, "language-neutral" is a claim, not a fact.

