require_relative "primitives"

module MudManager
  # The single source of truth for the agent-facing command surface.
  #
  # Before this file the same information was transcribed by hand three times:
  # once as Primitives methods, once as Boukensha::Tools::Mud registrations, and
  # it would have been a third time as an MCP tool schema. Each transcription is
  # a place for silent drift — a schema promising an enum the primitive rejects
  # fails only at runtime, on that one argument, mid-session.
  #
  # Now: this table generates the MCP `tools/list` schema AND dispatches the
  # call. Primitives keeps doing the validation. Adding a command is one edit.
  #
  # Each entry:
  #   name:        MCP tool name (also the CLI subcommand)
  #   description: shown to the model
  #   params:      { name => { type:, description:, enum:, required: } }
  #   invoke:      lambda(params_hash) -> Primitives::Command (or String)
  module ToolTable
    P = Primitives

    # Params that appear over and over.
    TARGET  = { type: "string", description: "Name or keyword of the target", required: true }.freeze
    OBJECT  = { type: "string", description: "Name or keyword of the object", required: true }.freeze
    TEXT    = { type: "string", description: "The text to send", required: true }.freeze

    def self.enum(values, description, required: true)
      { type: "string", description: description, enum: values, required: required }
    end

    TOOLS = [
      # ---------- movement & posture ----------
      {
        name: "move",
        description: "Move the character one room in a compass direction.",
        params: { "direction" => enum(P::DIRECTIONS, "Direction to move") },
        invoke: ->(a) { P.move(a["direction"]) }
      },
      {
        name: "set_position",
        description: "Change body position: stand, sit, rest, sleep or wake.",
        params: { "position" => enum(P::POSITIONS, "Position to adopt") },
        invoke: ->(a) { P.set_position(a["position"]) }
      },
      {
        name: "flee",
        description: "Attempt to flee from combat in a random direction.",
        params: {},
        invoke: ->(_a) { P.flee }
      },
      {
        name: "enter",
        description: "Enter a portal, door or object by keyword.",
        params: { "keyword" => { type: "string", description: "What to enter", required: false } },
        invoke: ->(a) { P.enter(a["keyword"]) }
      },
      {
        name: "follow",
        description: "Follow another character, or stop following if no leader given.",
        params: { "leader" => { type: "string", description: "Who to follow", required: false } },
        invoke: ->(a) { P.follow(a["leader"]) }
      },
      {
        name: "track",
        description: "Track a character to find which way they went.",
        params: { "victim" => TARGET },
        invoke: ->(a) { P.track(a["victim"]) }
      },

      # ---------- looking & information ----------
      {
        name: "look",
        description: "Look at the room, or at/in a specific target.",
        params: {
          "target"      => { type: "string", description: "What to look at", required: false },
          "preposition" => enum(P::LOOK_PREPS, "How to look (in/at/direction)", required: false)
        },
        invoke: ->(a) { P.look(target: a["target"], preposition: a["preposition"]) }
      },
      {
        name: "examine",
        description: "Examine an object or character closely.",
        params: { "target" => TARGET },
        invoke: ->(a) { P.examine(a["target"]) }
      },
      {
        name: "info_self",
        description: "Report information about your own character: score, inventory, equipment, gold, exits, time, weather and similar.",
        params: { "kind" => enum(P::INFO_SELF, "Which report to request") },
        invoke: ->(a) { P.info_self(a["kind"]) }
      },
      {
        name: "info_world",
        description: "Request world information: who is online, help, news, credits and similar.",
        params: {
          "kind"   => enum(P::INFO_WORLD, "Which report to request"),
          "filter" => { type: "string", description: "Optional argument, e.g. a help topic", required: false }
        },
        invoke: ->(a) { P.info_world(a["kind"], filter: a["filter"]) }
      },
      {
        name: "consider",
        description: "Judge how dangerous a target would be to fight.",
        params: { "target" => TARGET },
        invoke: ->(a) { P.consider(a["target"]) }
      },
      {
        name: "diagnose",
        description: "Check the physical condition of a target, or yourself.",
        params: { "target" => { type: "string", description: "Who to diagnose", required: false } },
        invoke: ->(a) { P.diagnose(a["target"]) }
      },
      {
        name: "report_hp",
        description: "Report your current hit points, mana and movement to the room.",
        params: {},
        invoke: ->(_a) { P.report_hp }
      },

      # ---------- combat ----------
      {
        name: "attack",
        description: "Attack a target. 'hit' is the normal attack; 'murder' and 'kill' bypass some safeties.",
        params: {
          "style"  => enum(P::ATTACK_STYLES, "Attack style"),
          "target" => TARGET
        },
        invoke: ->(a) { P.attack(a["style"], a["target"]) }
      },
      {
        name: "skill_strike",
        description: "Use a combat skill against a target: backstab, bash, kick, rescue or assist.",
        params: {
          "skill"  => enum(P::STRIKE_SKILLS, "Skill to use"),
          "target" => TARGET
        },
        invoke: ->(a) { P.skill_strike(a["skill"], a["target"]) }
      },
      {
        name: "cast_spell",
        description: "Cast a spell, optionally at a target.",
        params: {
          "spell"  => { type: "string", description: "Spell name", required: true },
          "target" => { type: "string", description: "Optional target", required: false }
        },
        invoke: ->(a) { P.cast(a["spell"], target: a["target"]) }
      },
      {
        name: "use_magic_item",
        description: "Use a magic item: 'use' a staff/wand, 'quaff' a potion, 'recite' a scroll.",
        params: {
          "mode"   => enum(P::SPELL_ITEM, "How to use the item"),
          "item"   => OBJECT,
          "target" => { type: "string", description: "Optional target", required: false }
        },
        invoke: ->(a) { P.use_magic_item(a["mode"], a["item"], target_args: a["target"]) }
      },

      # ---------- communication ----------
      {
        name: "say",
        description: "Speak to the current room: say, emote or reply.",
        params: {
          "mode" => enum(P::LOCAL_SAY, "How to speak"),
          "text" => TEXT
        },
        invoke: ->(a) { P.say_local(a["mode"], a["text"]) }
      },
      {
        name: "tell",
        description: "Speak privately to one character: tell, whisper or ask.",
        params: {
          "mode"   => enum(P::TARGETED_SAY, "How to address them"),
          "target" => TARGET,
          "text"   => TEXT
        },
        invoke: ->(a) { P.say_targeted(a["mode"], a["target"], a["text"]) }
      },
      {
        name: "channel_say",
        description: "Broadcast on a global channel: shout, gossip, auction, grats or holler.",
        params: {
          "channel" => enum(P::CHANNELS, "Channel to use"),
          "text"    => TEXT
        },
        invoke: ->(a) { P.say_channel(a["channel"], a["text"]) }
      },

      # ---------- objects ----------
      {
        name: "get_item",
        description: "Pick up an object, optionally from a container.",
        params: {
          "object"    => OBJECT,
          "container" => { type: "string", description: "Container to take from", required: false },
          "count"     => { type: "integer", description: "How many", required: false }
        },
        invoke: ->(a) { P.get(a["object"], container: a["container"], count: a["count"]) }
      },
      {
        name: "drop_item",
        description: "Drop, donate or junk an object.",
        params: {
          "mode"   => enum(P::DROP_MODES, "How to dispose of it"),
          "object" => OBJECT,
          "count"  => { type: "integer", description: "How many", required: false }
        },
        invoke: ->(a) { P.drop(a["mode"], a["object"], count: a["count"]) }
      },
      {
        name: "put_item",
        description: "Put an object into a container.",
        params: {
          "object"    => OBJECT,
          "container" => { type: "string", description: "Container to put it in", required: true },
          "count"     => { type: "integer", description: "How many", required: false }
        },
        invoke: ->(a) { P.put(a["object"], a["container"], count: a["count"]) }
      },
      {
        name: "give_item",
        description: "Give an object to another character.",
        params: {
          "object" => OBJECT,
          "target" => TARGET,
          "count"  => { type: "integer", description: "How many", required: false }
        },
        invoke: ->(a) { P.give(a["object"], a["target"], count: a["count"]) }
      },
      {
        name: "equip_item",
        description: "Wear, wield, grab, hold or remove an item.",
        params: {
          "operation" => enum(P::EQUIP_OPS, "Equipment operation"),
          "object"    => OBJECT,
          "body_loc"  => { type: "string", description: "Optional body location", required: false }
        },
        invoke: ->(a) { P.equip(a["operation"], a["object"], body_loc: a["body_loc"]) }
      },
      {
        name: "consume_item",
        description: "Eat, taste, drink or sip something.",
        params: {
          "mode"   => enum(P::CONSUME_MODES, "How to consume it"),
          "object" => OBJECT
        },
        invoke: ->(a) { P.consume(a["mode"], a["object"]) }
      },
      {
        name: "door",
        description: "Open, close, lock, unlock or pick a door or container.",
        params: {
          "verb"      => enum(P::DOOR_VERBS, "What to do"),
          "target"    => TARGET,
          "direction" => enum(P::DIRECTIONS, "Which exit, for doors", required: false)
        },
        invoke: ->(a) { P.door(a["verb"], a["target"], direction: a["direction"]) }
      },

      # ---------- economy & character ----------
      {
        name: "shop",
        description: "Interact with a shopkeeper: buy, sell, list, value or offer.",
        params: {
          "operation" => enum(P::SHOP_OPS, "Shop operation"),
          "args"      => { type: "string", description: "Item or arguments", required: false }
        },
        invoke: ->(a) { P.shop(a["operation"], args: a["args"]) }
      },
      {
        name: "practice",
        description: "Practice a skill with a guildmaster, or list practisable skills.",
        params: { "skill" => { type: "string", description: "Skill to practice", required: false } },
        invoke: ->(a) { P.practice(a["skill"]) }
      },
      {
        name: "save_character",
        description: "Save the character to disk.",
        params: {},
        invoke: ->(_a) { P.save_char }
      },

      # ---------- escape hatch ----------
      {
        name: "send_raw",
        description: "Send a raw command line to the MUD, unvalidated. Use only when no specific tool fits.",
        params: { "line" => { type: "string", description: "Exact line to send", required: true } },
        invoke: ->(a) { a["line"].to_s }
      }
    ].freeze

    BY_NAME = TOOLS.each_with_object({}) { |t, h| h[t[:name]] = t }.freeze

    # Session-management tools, handled by the daemon rather than Primitives.
    SESSION_TOOLS = [
      {
        name: "mud_connect",
        description: "Open a MUD session and log the character in. Safe to call again; returns the existing session if already connected.",
        params: {
          "session"  => { type: "string", description: "Session name (default: 'default')", required: false },
          "host"     => { type: "string", description: "MUD host", required: false },
          "port"     => { type: "integer", description: "MUD port", required: false },
          "username" => { type: "string", description: "Character name", required: false },
          "password" => { type: "string", description: "Character password", required: false }
        }
      },
      {
        name: "mud_disconnect",
        description: "Close a MUD session.",
        params: { "session" => { type: "string", description: "Session name", required: false } }
      },
      {
        name: "mud_status",
        description: "List live MUD sessions and whether each is connected.",
        params: {}
      }
    ].freeze

    # ---- schema generation -------------------------------------------------

    # Render one entry as an MCP tool descriptor (JSON Schema for inputSchema).
    def self.to_mcp(entry)
      props   = {}
      required = []
      entry[:params].each do |pname, spec|
        prop = { "type" => spec[:type], "description" => spec[:description] }
        prop["enum"] = spec[:enum] if spec[:enum]
        props[pname] = prop
        required << pname if spec[:required]
      end
      schema = { "type" => "object", "properties" => props }
      schema["required"] = required unless required.empty?
      {
        "name"        => entry[:name],
        "description" => entry[:description],
        "inputSchema" => schema
      }
    end

    # The full MCP tools/list payload: session management plus gameplay.
    def self.mcp_tools
      (SESSION_TOOLS + TOOLS).map { |e| to_mcp(e) }
    end

    # Build the raw MUD line for a gameplay tool. Raises ArgumentError via
    # Primitives when an enum or required argument is wrong.
    def self.build_line(name, args)
      entry = BY_NAME[name] or raise ArgumentError, "unknown tool: #{name}"
      result = entry[:invoke].call(args || {})
      result.respond_to?(:raw) ? result.raw : result.to_s
    end

    def self.gameplay_tool?(name) = BY_NAME.key?(name)
  end
end
