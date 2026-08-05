# Architecture — Ruby (step 10 + MudManager over MCP)

Everything in the Ruby tree as of step 10 `standard_tool_library`, including the
MCP layer. Companion docs:
[`plans/mud_manager/generic_interfacing.md`](plans/mud_manager/generic_interfacing.md)
(why) and [`plans/mud_manager/implementation.md`](plans/mud_manager/implementation.md)
(what).

---

## 1. Whole system

```mermaid
flowchart TB
    subgraph entry["Entry points"]
        direction LR
        LAUNCH["bin/ruby/10_standard_tool_library"]
        BIN["bin/boukensha<br/><i>the installed gem command</i>"]
        LOADER["boukensha_loader.rb<br/><i>BOUKENSHA_PATH → which step</i>"]
        EX["examples/example.rb"]
        BIN --> LOADER
    end

    subgraph api["Public API — boukensha.rb"]
        RUN["Boukensha.run<br/><i>one shot</i>"]
        REPL_M["Boukensha.repl<br/><i>many turns</i>"]
        DSL["RunDSL<br/><i>block → tool</i>"]
    end

    subgraph state["State"]
        CFG["Config<br/><i>settings.yaml, .env</i><br/>3-tier dir resolution"]
        CTX["Context<br/><i>messages + tools + system</i>"]
        TASK["Tasks::Player &lt; Tasks::Base<br/><i>model, prompts, ceilings</i>"]
        MSG["Message"]
    end

    subgraph tools["Tool registration"]
        REG["Registry<br/><i>register / dispatch</i>"]
        TOOL["Tool<br/><i>name, params, required_keys</i>"]
        FS["Tools::FileSystem"]
        SH["Tools::Shell"]
        MUDT["Tools::Mud<br/><b>legacy — direct MudManager</b>"]
        MCPT["Tools::Mcp<br/><b>generic MCP bridge</b>"]
    end

    subgraph loop["Agent loop"]
        AGENT["Agent<br/><i>iterate, dispatch, wind down</i>"]
        PB["PromptBuilder"]
        CL["Client<br/><i>HTTP + retry/backoff</i>"]
        LOG["Logger<br/><i>JSONL + subscribe</i>"]
        REPL_C["Repl<br/><i>/help /quiet /clear /exit</i>"]
    end

    subgraph be["Backends"]
        BASE["Backends::Base"]
        ANT["Anthropic"]
        OAI["OpenAI"]
        GEM["Gemini"]
        OLL["Ollama"]
        OLLC["OllamaCloud"]
        BASE --- ANT & OAI & GEM & OLL & OLLC
    end

    LAUNCH --> EX --> REPL_M
    LOADER --> REPL_M
    RUN & REPL_M --> CFG & CTX & REG & AGENT
    REPL_M --> REPL_C --> AGENT
    RUN --> DSL --> REG
    CFG --> TASK
    CTX --> MSG & TOOL
    REG --> TOOL
    REG --- FS & SH & MUDT & MCPT
    AGENT --> PB --> CL --> BASE
    AGENT --> LOG
    AGENT --> REG
    CL -.->|HTTPS| LLM(["LLM provider"])
    MCPT --> MCPC["Mcp::Client<br/><i>stdio JSON-RPC</i>"]

    MCPC -.->|"spawn + stdio"| SERVERS(["any MCP server"])

    classDef new fill:#1f6feb,stroke:#0b3d91,color:#fff
    classDef legacy fill:#8a5a00,stroke:#5a3c00,color:#fff
    class MCPT,MCPC new
    class MUDT legacy
```

**Blue is new** (the MCP layer). **Amber is legacy** — `Tools::Mud` wires
MudManager in directly and is what the MCP path replaces.

---

## 2. The MCP layer

The host is server-agnostic: `Mcp::Client` and `Tools::Mcp` contain no MUD code.
A server is a `command` + `args` + `env` in `settings.yaml`.

```mermaid
flowchart LR
    subgraph host["Boukensha — the MCP host"]
        CFG2["settings.yaml<br/>mcp_servers:"]
        MCPT2["Tools::Mcp<br/><i>register_all</i>"]
        MCPC2["Mcp::Client"]
        REG2["Registry"]
        CFG2 --> MCPT2 --> MCPC2
        MCPT2 --> REG2
    end

    subgraph servers["MCP servers — any language, any capability"]
        MUDS["mud-manager --mcp"]
        FSS["filesystem server"]
        OTH["…"]
    end

    subgraph mm["MudManager gem"]
        MCPS["McpServer<br/><i>shim — owns nothing</i>"]
        DC["DaemonClient"]
        CLI2["CLI<br/><i>zero-dep shell-out</i>"]
        DAEMON["Daemon<br/><b>owns the sessions</b>"]
        TT["ToolTable<br/><i>one source → schema + dispatch</i>"]
        PRIM["Primitives<br/><i>58 typed builders, validation</i>"]
        SESS1["Session alice"]
        SESS2["Session bob"]

        MCPS --> DC
        CLI2 --> DC
        DC -->|"UNIX socket<br/>JSON lines"| DAEMON
        MCPS --> TT --> PRIM
        DAEMON --> TT
        DAEMON --> SESS1 & SESS2
    end

    MCPC2 -.->|"stdio JSON-RPC 2.0"| MUDS
    MCPC2 -.->|"stdio JSON-RPC 2.0"| FSS
    MCPC2 -.->|"stdio"| OTH
    MUDS --> MCPS
    SESS1 -.->|telnet| MUD1(["CircleMUD"])
    SESS2 -.->|telnet| MUD1

    classDef own fill:#1a7f37,stroke:#0f5323,color:#fff
    class DAEMON own
```

**Why the shim owns nothing.** MCP's stdio transport makes the server a child of
the agent process. A server holding the telnet session would lose it on every
agent restart — a fresh 7-step login and a visible reconnect in-game. The daemon
(green) outlives every client; the MCP server and CLI are both translation
layers onto it.

---

## 3. One tool call, end to end

```mermaid
sequenceDiagram
    participant M as LLM
    participant A as Agent
    participant R as Registry
    participant C as Mcp::Client
    participant S as McpServer
    participant D as Daemon
    participant T as Session
    participant MUD as CircleMUD

    M->>A: tool_use: move{direction:"north"}
    A->>R: dispatch("mud_move", …)
    R->>C: call_tool("move", …)
    C->>S: tools/call (stdio JSON-RPC)
    S->>D: {"op":"send","tool":"move"}  (UNIX socket)
    Note over D: socket dead? reconnect + re-login,<br/>then set reconnected:true
    D->>D: ToolTable.build_line → Primitives.move
    Note over D: bad enum raises here,<br/>before anything reaches the MUD
    D->>T: send_command("north")
    T->>MUD: north\r\n
    MUD-->>T: "You walk north…> "
    T-->>D: read_until_prompt
    D-->>S: {"ok":true,"output":…,"reconnected":false}
    S-->>C: content:[{type:"text"}], isError:false
    C-->>R: text
    R-->>A: tool_result
    A->>M: tool_result message
```

Validation happens **once**, in `Primitives`, on the server side — so every
language inherits it. A caller sending `direction: "sideways"` gets
`invalid direction: "sideways" (expected one of north, east, …)` rather than a
mangled line reaching the game.

---

## 4. Cross-language reach

```mermaid
flowchart TB
    RB["Ruby harness<br/><i>Boukensha</i>"]
    PY["Python harness"]
    GO["Go / Rust / Java"]
    SH2["any shell"]

    MCPSRV["mud-manager --mcp"]
    CLI3["mud-manager CLI"]
    D2["Daemon"]

    RB -->|MCP stdio| MCPSRV
    PY -->|MCP stdio| MCPSRV
    GO -->|MCP stdio| MCPSRV
    SH2 -->|exec| CLI3
    MCPSRV --> D2
    CLI3 --> D2
    D2 -.->|telnet| MUD2(["CircleMUD"])
```

| Consumer | What it writes for MUD access |
|---|---|
| Ruby | nothing — a config entry |
| Python | nothing — a config entry once its harness speaks MCP |
| Go / Rust / Java | ~60 lines of MCP client, which the harness needs anyway for filesystem and shell tools |
| any shell | `mud-manager tool look` — zero dependencies |

---

## 5. Session lifetime

The reason the daemon exists, in one picture:

```mermaid
flowchart LR
    subgraph T1["agent run #1"]
        S1["McpServer"]
    end
    subgraph T2["agent run #2 — after restart"]
        S2["McpServer"]
    end
    subgraph T3["a shell command"]
        S3["CLI"]
    end

    D3["Daemon<br/><i>started once</i>"]
    SESS["Session<br/><i>logged in, in-world</i>"]

    S1 -.->|attach| D3
    S2 -.->|attach| D3
    S3 -.->|attach| D3
    D3 --> SESS
    SESS -.->|telnet| MUD3(["CircleMUD"])
```

Restart the agent as often as you like — the character stays in the world.

---

## 6. Where the coupling still is

The MCP path is generic. The MUD-specific code in Boukensha is the **old** path,
and it predates the MCP work:

```mermaid
flowchart LR
    subgraph generic["Generic — knows nothing about MUDs"]
        G1["Mcp::Client"]
        G2["Tools::Mcp"]
        G3["mcp_servers: config"]
    end

    subgraph coupled["MUD-coupled — deletable"]
        C1["Tools::Mud<br/>480 lines, 27 tools"]
        C2["Boukensha.run/repl<br/><code>mud:</code> kwarg"]
        C3["Config#mud_host/port/<br/>username/password"]
        C4["mud_opts_from_config"]
    end

    classDef gen fill:#1a7f37,stroke:#0f5323,color:#fff
    classDef cpl fill:#8a5a00,stroke:#5a3c00,color:#fff
    class G1,G2,G3 gen
    class C1,C2,C3,C4 cpl
```

Deleting the amber boxes makes MUD support purely an `mcp_servers:` entry, which
is the direction `ITERATIONS.md` §10 describes. It has **not** been done — the
MCP path was added alongside so nothing working today breaks.

Session statefulness is *not* the cause of that coupling: session state lives
entirely server-side of the MCP boundary. What sessions do cost is semantic —
connect-before-use, and staleness after a reconnect — and that lands in the
model's reasoning, not in the harness.
