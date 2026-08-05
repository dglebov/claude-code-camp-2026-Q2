# Architecture — Ruby, actual state

Redraw of the Lucidchart *Claude Code Camp Agent Architecture — Baseline* against
what is actually in the tree at step 10 `standard_tool_library`.

**This is the as-built diagram, not the target.** Where it differs from the
Lucidchart version, §7 says which is ahead and why. Companion docs:
[`plans/mud_manager/generic_interfacing.md`](plans/mud_manager/generic_interfacing.md)
(why) and [`plans/mud_manager/implementation.md`](plans/mud_manager/implementation.md)
(what).

---

## 1. Whole system, as built

```mermaid
flowchart LR
    USER(["User"])

    subgraph boot["Loading"]
        BIN["<b>bin/boukensha</b><br/>the installed gem command"]
        LOADER["<b>BoukenshaLoader</b><br/>resolves WHICH step lib to load:<br/>BOUKENSHA_PATH → ~/.boukensharc → bundled"]
        RC["<b>~/.boukensharc</b><br/>a file holding one path —<br/>the permanent step default"]
        LAUNCH["<b>bin/ruby/10_standard_tool_library</b><br/>runs from source, no install"]
    end

    subgraph api["Entry points — boukensha.rb"]
        REPL_M["<b>Boukensha.repl</b><br/>interactive, many turns"]
        RUN_M["<b>Boukensha.run</b><br/>one shot — <b>still in use</b>,<br/>examples/example.rb calls it"]
        DSL["<b>RunDSL</b><br/>block → tool registration"]
        REPL_C["<b>Boukensha::Repl</b><br/>/help /quiet /loud /clear /exit /quit"]
    end

    subgraph core["Agent loop"]
        AGENT["<b>Boukensha::Agent</b> — MAIN<br/>the basic agent loop<br/>• max_iterations (from Config)<br/>• max_output_tokens per turn<br/>• winds down at the ceiling"]
        PB["<b>Boukensha::PromptBuilder</b><br/>builds the API structure per backend"]
        CL["<b>Boukensha::Client</b><br/>API requests + retry/backoff"]
        LOG["<b>Boukensha::Logger</b><br/>JSONL to sessions/; turn(n:)<br/>and subscribe(&block) fan-out"]
    end

    subgraph be["Boukensha::Backends"]
        BASE["<b>Base</b> <i>abstract</i>"]
        ANT["Anthropic"]; OAI["OpenAI"]; GEM["Gemini"]
        OLL["Ollama"]; OLLC["OllamaCloud"]
    end

    subgraph st["State"]
        CTX["<b>Boukensha::Context</b><br/>• messages[]<br/>• tools[]<br/>• working_dir"]
        MSG["<b>Boukensha::Message</b><br/>lightweight data class"]
        TOOL["<b>Boukensha::Tool</b><br/>name, params, block,<br/><b>required_keys</b>"]
        REG["<b>Boukensha::Registry</b><br/>register / dispatch / registered?"]
    end

    subgraph tk["Tasks"]
        TB["<b>Tasks::Base</b> <i>abstract</i>"]
        TP["<b>Tasks::Player</b><br/>model, prompts, ceilings"]
    end

    USER -->|"$ boukensha"| BIN --> LOADER --> RC
    USER -->|"repo launcher"| LAUNCH
    LOADER --> REPL_M
    LAUNCH --> RUN_M
    REPL_M --> REPL_C --> AGENT
    RUN_M --> AGENT
    RUN_M & REPL_M --> DSL --> REG
    AGENT --> PB --> CL --> BASE
    BASE --- ANT & OAI & GEM & OLL & OLLC
    CL -.->|HTTPS| APIX(["provider API"])
    AGENT --> LOG
    AGENT --> REG
    AGENT --> CTX
    CTX --> MSG & TOOL
    REG --> TOOL
    TB --- TP
```

Deliberately unlike the Lucidchart version: **`Boukensha.run` is not "no longer
used"** — step 10's `examples/example.rb` calls it, and the repo launcher runs
that. There is also **no `Boukensha.tui`**; the TUI is step 11.

---

## 2. Tools — what is registered, and by whom

```mermaid
flowchart TB
    REG2["<b>Boukensha::Registry</b>"]

    subgraph builtin["Built-in modules — still present"]
        FS["<b>Tools::FileSystem</b> — 6 tools<br/>pwd, list_directory, read_file,<br/>write_file, delete_file, search_files"]
        SH["<b>Tools::Shell</b> — 1 tool<br/>run_command"]
        MUDT["<b>Tools::Mud</b> — 27 tools<br/>wraps the mud_manager gem directly"]
    end

    subgraph mcp["MCP path — server-agnostic"]
        MCPT["<b>Tools::Mcp</b><br/>register_all → discovers and registers<br/>whatever a server advertises<br/><i>no MUD or filesystem code inside</i>"]
        MCPC["<b>Boukensha::Mcp::Client</b><br/>spawn, initialize, tools/list, tools/call"]
    end

    CFGX["<b>settings.yaml</b> → mcp_servers:<br/>command / args / env / prefix / required"]

    REG2 --- FS & SH & MUDT
    CFGX --> MCPT --> MCPC
    MCPT --> REG2
    MCPC -.->|"stdio JSON-RPC 2.0"| S1(["mud-manager --mcp"])
    MCPC -.->|stdio| S2(["third-party filesystem server"])
    MCPC -.->|stdio| S3(["any other MCP server"])

    classDef legacy fill:#8a5a00,stroke:#5a3c00,color:#fff
    classDef new fill:#1f6feb,stroke:#0b3d91,color:#fff
    class FS,SH,MUDT legacy
    class MCPT,MCPC new
```

**Amber still exists.** The Lucidchart diagram shows no built-in tool modules —
that is the target. Both paths currently ship, so enabling the MUD server needs
`prefix: mud` or `mud: false`, or the names collide (`Tools::Mcp` raises rather
than silently shadowing).

---

## 3. MudManager — including the daemon

The largest structural difference from the Lucidchart version, which shows the
MCP server holding the session directly.

```mermaid
flowchart TB
    subgraph mm["MudManager gem 0.2.0"]
        CLI["<b>CLI</b> — bin/mud-manager<br/>connect / tool / send / sessions / stop<br/><i>zero-dependency shell-out path</i>"]
        MCPS["<b>McpServer</b> — --mcp<br/>JSON-RPC 2.0 over stdio<br/><b>owns nothing; a shim</b>"]
        DC["<b>DaemonClient</b><br/>auto-starts a detached daemon"]
        DAEMON["<b>Daemon</b><br/><b>owns the sessions</b><br/>per-session locks · transparent reconnect"]
        TT["<b>ToolTable</b><br/>ONE source → MCP schema + dispatch<br/>3 session + 31 gameplay = 34 tools"]
        PRIM["<b>Primitives</b><br/>58 typed builders, enum validation"]
        SESS["<b>Session</b> ×N<br/>telnet, IAC stripping, login dance"]
        VER["<b>version.rb</b><br/>gemspec + MCP serverInfo read it"]

        MCPS --> DC --> DAEMON
        CLI --> DC
        MCPS --> TT --> PRIM
        DAEMON --> TT
        DAEMON --> SESS
        MCPS -.-> VER
    end

    HOST(["Boukensha::Mcp::Client"]) -.->|stdio| MCPS
    ANY(["Python / Go / Rust / Java harness"]) -.->|stdio| MCPS
    SH2(["any shell"]) -->|exec| CLI
    SESS -.->|telnet| MUD(["tbaMUD / CircleMUD"])

    classDef own fill:#1a7f37,stroke:#0f5323,color:#fff
    class DAEMON own
```

**Why the daemon exists.** MCP's stdio transport makes the server a child of the
agent process. If the session lived in the server, every agent restart would mean
a fresh 7-step login and a visible disconnect/reconnect in-game — worst exactly
when a student iterates fastest. The daemon (green) outlives every client.

Sessions run in parallel — five concurrent logins complete together, and one
player logging in never stalls another. Commands *within* one session are
serialised, because a telnet socket has no request ids and interleaved sends
would steal each other's output.

---

## 4. Config

```mermaid
flowchart LR
    CFG["<b>Boukensha::Config</b><br/>loads settings + .env"]
    T1["1. BOUKENSHA_DIR env var"]
    T2["2. nearest .boukensha at or above cwd<br/><i>walk-up, like git finding .git</i>"]
    T3["3. ~/.boukensha"]
    DIR["<b>.boukensha/</b>"]
    SET["<b>settings.yaml</b><br/>tasks.player: provider, model,<br/>prompt_override<br/><b>mcp_servers:</b><br/>mud: host/port/username/password"]
    ENVF["<b>.env</b><br/>secret keys — gitignored"]
    PR["<b>prompts/&lt;task&gt;/system.md</b><br/>overrides the task's system prompt"]
    SESSL["<b>sessions/&lt;datetime&gt;-&lt;id&gt;.jsonl</b><br/>the logs — gitignored"]

    CFG --> T1 --> T2 --> T3 --> DIR
    DIR --- SET & ENVF & PR & SESSL
```

Three tiers, not two. The middle one was added so `boukensha` picks up a
project's own `.boukensha` from any depth inside it.

---

## 5. One tool call, end to end

```mermaid
sequenceDiagram
    participant M as LLM
    participant A as Agent
    participant R as Registry
    participant C as Mcp::Client
    participant S as McpServer
    participant D as Daemon
    participant T as Session
    participant MUD as tbaMUD

    M->>A: tool_use: mud_move{direction:"north"}
    A->>R: dispatch("mud_move", …)
    R->>C: call_tool("move", …)
    C->>S: tools/call  (stdio JSON-RPC)
    S->>D: {"op":"send","tool":"move"}  (UNIX socket)
    Note over D: socket dead? reconnect + re-login,<br/>report reconnected:true
    D->>D: ToolTable.build_line → Primitives.move
    Note over D: bad enum raises HERE,<br/>before anything reaches the MUD
    D->>T: send_command("north")
    T->>MUD: north\r\n
    MUD-->>T: "You walk north…> "
    T-->>D: read_until_prompt
    D-->>S: {"ok":true,"output":…}
    S-->>C: content:[{type:"text"}], isError:false
    C-->>R: text
    R-->>A: tool_result
    A->>M: tool_result message
```

Validation happens once, server-side, so every language inherits it.

---

## 6. Cross-language reach

```mermaid
flowchart LR
    RB["Ruby — Boukensha"] -->|MCP stdio| SRV["mud-manager --mcp"]
    PY["Python"] -->|MCP stdio| SRV
    GO["Go / Rust / Java"] -->|MCP stdio| SRV
    SHX["any shell"] -->|exec| CLIX["mud-manager CLI"]
    SRV --> DX["Daemon"]
    CLIX --> DX
    DX -.->|telnet| MUDX(["tbaMUD"])
```

---