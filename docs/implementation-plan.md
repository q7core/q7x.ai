# q7x Implementation Plan

Development follows a phased approach. Each phase produces something working — no phase is just "architecture."

## Phase 1: Foundation — Agent SDK Hello World

**Goal:** TypeScript project that receives a Telegram message, passes it to the Claude Agent SDK, and sends the response back.

**Components:**
- Project scaffold (TypeScript, pnpm, eslint)
- grammY Telegram bot with user whitelist
- Minimal Agent SDK wrapper (prompt in → response out)
- System prompt loaded from config
- Working directory on the server for agent file operations
- systemd service for the agent process
- `max_budget_usd` safety cap per query

**Deliverable:** Message the bot, Claude processes it with full tool access, response comes back.

## Phase 2: Session Management & Trust Boundaries

**Goal:** Conversations persist across messages. Dangerous actions require approval.

**Components:**
- Session persistence: Telegram chat ID → Agent SDK session mapping in SQLite
- Auto-resume within configurable timeout
- `/new` and `/continue` commands
- Trust boundary UI: Inline keyboard approve/deny for bash commands and file writes
- Response formatting: Code blocks, tool use summaries, Telegram 4096-char chunking
- Action audit log in SQLite

**Deliverable:** Multi-turn conversations with explicit approval for system actions.

## Phase 3: Memory Layer

**Goal:** The agent remembers across sessions — structured knowledge, not raw chat dumps.

**Components:**
- SQLite schema: entities, aliases, sessions, decisions, summaries
- Post-conversation extraction: Distill facts/decisions from each exchange (via Ollama or Haiku)
- Memory Normalization Layer: Map natural language references to canonical entity keys
- Pre-conversation injection: Query SQLite for relevant context, inject into system prompt
- Memory commands: `/remember`, `/forget`, `/memory`, `/memory search`

**Deliverable:** An agent that gets smarter over time and can tell you what it knows.

## Phase 4: Intelligent Routing

**Goal:** Route messages to the cheapest/fastest backend that can handle them.

**Components:**
- Triage classifier on local Ollama (~100 tokens per classification)
- Three routes: memory (instant, free) → Ollama (fast, free) → Agent SDK (powerful, $$)
- Cost tracking in SQLite: per-session and aggregate
- `/cost` command for spend visibility
- Daily budget cap (configurable)
- Graceful fallback chain if backends are unavailable

**Deliverable:** Smart, cost-aware routing with full transparency.

## Phase 5: MCP & Extensibility

**Goal:** Connect to external services, establish the plugin pattern.

**Components:**
- Custom in-process MCP server for q7x tools (memory query, server status)
- External MCP server integration (Notion, Google Calendar, etc.)
- Future: Web dashboard on the existing Caddy/HTTPS setup

**Deliverable:** Extensible agent with external service access.

## Open Questions

- **LLM routing heuristics**: How does the triage classifier decide? Cost? Complexity estimate? Keyword matching? Learned behavior?
- **Compaction strategy**: When and how does the agent summarize old context? What gets kept vs. distilled vs. dropped?
- **Memory schema evolution**: How do we handle schema migrations as the memory model matures?
- **Session model**: Does a Telegram conversation map 1:1 to an agent session, or is the agent always "on" with continuous context?
