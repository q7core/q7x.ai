# q7x Architecture

## Overview

q7x is a system-level AI agent that runs on your own infrastructure. It combines Anthropic's Claude Agent SDK (the engine that powers Claude Code) with a custom memory layer and intelligent routing to create an agent that operates on your server, remembers across sessions, and manages costs transparently.

## Design Principles

1. **KISS, always.** Default to the simplest thing that works. Never be naively simple — know what you're trading off and choose consciously.

2. **Memory is a first-class citizen.** Not "dump everything into context" and not "forget everything between sessions." Efficient, selective memory — lazy-loading relevant context, staying aware of what it knows and doesn't know, transparent about token usage and compaction.

3. **Containerize where it adds value.** Use containers for clean separation of the LLM runtime, database, and supporting services. Don't containerize just for the sake of it.

4. **Build on proven foundations, differentiate where it matters.** The Claude Agent SDK provides the agentic loop, tool use, and context management. We build the memory layer, routing intelligence, and UX on top.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     q7x Server                           │
│                                                          │
│  ┌──────────────┐     ┌───────────────────────────────┐  │
│  │  Telegram     │     │   q7x Core Process            │  │
│  │  Bot Layer    │────▶│   (Node.js / TypeScript)      │  │
│  │  (grammY)     │◀────│                               │  │
│  └──────────────┘     │  ┌───────────────────────────┐ │  │
│                        │  │  Claude Agent SDK          │ │  │
│                        │  │                           │ │  │
│                        │  │  • Bash / file tools      │ │  │
│                        │  │  • MCP server integration │ │  │
│                        │  │  • Context compaction     │ │  │
│                        │  │  • Session management     │ │  │
│                        │  └───────────────────────────┘ │  │
│                        │                               │  │
│                        │  ┌───────────────────────────┐ │  │
│                        │  │  Memory Layer (custom)     │ │  │
│                        │  │                           │ │  │
│                        │  │  • SQLite persistent store │ │  │
│                        │  │  • Entity normalization   │ │  │
│                        │  │  • Lazy context retrieval │ │  │
│                        │  │  • Fact extraction        │ │  │
│                        │  └───────────────────────────┘ │  │
│                        │                               │  │
│                        │  ┌───────────────────────────┐ │  │
│                        │  │  LLM Router               │ │  │
│                        │  │                           │ │  │
│                        │  │  Memory → instant answer  │ │  │
│                        │  │  Ollama → fast & free     │ │  │
│                        │  │  Agent SDK → full power   │ │  │
│                        │  └───────────────────────────┘ │  │
│                        └───────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐     ┌───────────────────────────────┐  │
│  │  Ollama       │     │  SQLite                       │  │
│  │  (container)  │     │  ~/.q7x/memory.db             │  │
│  │  Local LLM    │     └───────────────────────────────┘  │
│  └──────────────┘                                        │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Caddy (HTTPS reverse proxy)                         │ │
│  │  Serves future web dashboard                         │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### Claude Agent SDK

The Claude Agent SDK is the agentic runtime — it's the engine that powers Claude Code, extracted into a library. Instead of building our own agentic loop from scratch, we get:

- **Tool orchestration**: Claude decides which tools to use (bash, file I/O, web search) based on the task
- **Context compaction**: Automatic summarization when the context window fills up
- **Session persistence**: Resume conversations across messages
- **MCP integration**: Connect to external services (Notion, Google Calendar, custom tools) via the Model Context Protocol
- **Permission control**: Granular settings for what the agent can do autonomously
- **Cost budgets**: Cap spend per query with `max_budget_usd`

We treat the Agent SDK as infrastructure, not product. The product is what we build on top of it.

### Memory Layer (Core Differentiator)

The memory layer is what makes q7x more than just "Claude Code with a Telegram wrapper." Goals:

- **Knows what it knows.** Can quickly assess whether relevant context exists before making an expensive LLM call.
- **Lazy-loads context.** Doesn't stuff the full history into every prompt. Retrieves only what's relevant to the current task.
- **Stores structured knowledge, not chat logs.** Facts, decisions, preferences, project state — extracted and normalized after each conversation.
- **Transparent.** Token usage, session state, what's in active context vs. long-term storage — queryable and understandable.

#### Memory Normalization Layer

A key architectural concept: before storing or retrieving memory, normalize natural language references to canonical entity keys. "My Oracle server," "the q7x instance," "the ARM box" all map to `infrastructure:oracle_primary`.

This draws from identity resolution work in enterprise data — matching entities across inconsistent references. Modern LLMs make this normalization lightweight enough to run on every memory operation via the local Ollama model.

#### SQLite Schema (Initial Design)

```sql
-- Extracted facts — what the agent "knows"
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source_session TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alias mappings for normalization
CREATE TABLE entity_aliases (
    id INTEGER PRIMARY KEY,
    alias_text TEXT NOT NULL,
    canonical_key TEXT NOT NULL REFERENCES entities(canonical_key),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Session tracking
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    telegram_chat_id TEXT,
    sdk_session_id TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Decisions and preferences
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    reasoning TEXT,
    session_id TEXT REFERENCES sessions(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Compacted session summaries
CREATE TABLE session_summaries (
    id INTEGER PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    summary_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Intelligent Router

Not every message needs a $0.50 Agent SDK call. The router classifies incoming messages and sends them to the cheapest/fastest backend that can handle them:

| Route | When | Cost | Latency |
|-------|------|------|---------|
| **Memory** | Answer exists in SQLite | Free | Instant |
| **Ollama** | Simple question, classification, extraction | Free | ~1-2s |
| **Agent SDK** | Complex task, needs tools, multi-step work | $$$ (API) or plan (sub) | 5-30s |

The triage classifier runs on the local Ollama model (~100 tokens, instant) and routes accordingly. For subscription users, the cost motivation shifts to speed and offline capability.

### Telegram Interface

Telegram is the first communication channel, chosen for:

- Simple, well-documented bot API
- Rich interaction: inline keyboards, file sharing, push notifications
- Mobile-first (the agent is useful from your phone)
- Pluggable — the agent's core logic isn't Telegram-specific

Key UX patterns:

- **Trust boundaries**: Inline keyboards for approve/deny when the agent wants to run commands or modify files
- **Session management**: `/new`, `/continue`, `/memory`, `/cost` commands
- **Response formatting**: Code blocks, tool use summaries, long message chunking
- **Audit trail**: All actions logged in SQLite

### Authentication Model

Two deployment modes, same codebase:

**Personal (Subscription Auth)**
- Authenticate via `claude login` on the host
- Agent SDK uses your Claude Max subscription
- No per-token costs
- For personal use on your own infrastructure

**Business (API Key Auth)**
- Set `ANTHROPIC_API_KEY` in environment
- Per-token billing through Anthropic API
- Full cost tracking, budget caps, routing optimization
- For teams, products, or commercial use

## Infrastructure

### Target Deployment

- **Compute**: ARM-based cloud instance (e.g., Oracle Cloud Free Tier, AWS Graviton, Hetzner ARM)
- **Containers**: Docker for Ollama (LLM runtime) and Caddy (reverse proxy)
- **Agent process**: Native Node.js, managed by systemd
- **Storage**: SQLite file on the host filesystem
- **Domain**: Optional, for future web dashboard

### Resource Requirements

- **CPU**: 2+ cores (4 recommended for concurrent Ollama + Agent SDK)
- **RAM**: 4GB minimum (8GB+ recommended — Ollama model stays resident)
- **Disk**: 10GB minimum (models + database + workspace)
- **Network**: Outbound HTTPS to Anthropic API and Telegram API
