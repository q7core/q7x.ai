# q7x Architecture

## Overview

q7x is a system-level AI agent that runs on your own infrastructure. It combines a lightweight agent core with a custom memory abstraction layer and intelligent LLM routing to create an agent that operates on your server, remembers across sessions, and manages costs transparently.

## Design Principles

1. **KISS, always.** Default to the simplest thing that works. Know what you're trading off and choose consciously. Never over-architect.

2. **Memory is a first-class citizen.** Not "dump everything into context" and not "forget everything between sessions." Efficient, selective memory — lazy-loading relevant context, transparent about what it knows and what it doesn't.

3. **Two interfaces, one core.** CLI for direct use. Telegram for mobile and push. The agent logic doesn't know or care which interface it's talking through.

4. **Containerize where it adds value.** LLM runtime in a container makes sense. The agent process doesn't need to be.

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                    q7x Server                         │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │             q7x Core Process                    │  │
│  │                                                 │  │
│  │  • Conversation state (messages array)          │  │
│  │  • Session logging (JSONL)                      │  │
│  │  • LLM routing (OpenRouter / Ollama)            │  │
│  │  • Memory context injection                     │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                             │
│           ┌─────────────┼─────────────┐              │
│           ▼             ▼             ▼              │
│  ┌──────────────┐ ┌──────────┐ ┌───────────────┐    │
│  │   OpenRouter  │ │  Ollama  │ │    Memory     │    │
│  │  (cloud LLM)  │ │ (local)  │ │  Abstraction  │    │
│  │               │ │          │ │    Layer      │    │
│  │  Frontier     │ │  Fast,   │ │               │    │
│  │  models via   │ │  free,   │ │  HTTP service │    │
│  │  API key      │ │  private │ │  port 7331    │    │
│  └──────────────┘ └──────────┘ └───────┬───────┘    │
│                                         │             │
│                                ┌────────▼──────────┐  │
│                                │      SQLite        │  │
│                                │  entity index      │  │
│                                │  session metadata  │  │
│                                └───────────────────┘  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Caddy (HTTPS reverse proxy)                    │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## Component Details

### q7x Core

The agent process. Responsible for:

- Maintaining the conversation `messages` array across turns
- Calling the memory abstraction layer before each LLM call to inject relevant context
- Routing to the appropriate LLM backend based on task complexity
- Logging every message to a JSONL session file for indexing

Currently: Python CLI (`q7x.py`). Planned: TypeScript rewrite with Telegram interface.

### Memory Abstraction Layer

The memory layer is what makes q7x more than a stateless chat wrapper. It is a **standalone HTTP service** — separate process, separate codebase, communicates with q7x Core purely over HTTP.

**Interface contract:**
```
GET /context?q=<query>
→ [{"role": "system", "content": "Relevant context from memory:\n- ..."}]
```

**How it works:**

1. **Indexing** — Batch or watch-mode ingestion of session JSONL files. Each session is parsed, entities extracted via NLP (named entity recognition + part-of-speech tagging + config pattern matching), and stored with the surrounding context snippet.

2. **Deduplication** — Fuzzy matching normalises variants to canonical forms before storage. "Chargers", "the Chargers", "chargers" all resolve to the same entity.

3. **Retrieval** — Query tokens are matched against the entity index. The most relevant context snippets are assembled and returned as a system message, injected into the conversation before the LLM call.

**What gets stored:** Not raw chat logs. Entities — proper nouns, tool names, IPs, file paths, config values, domain-specific nouns — with their occurrence frequency, source (user vs agent), and the surrounding sentence as context.

**Why a separate service:** Clean separation of concerns. q7x Core doesn't need to know how memory works — only that it can ask for context and get back a list of system messages. Other interfaces (Telegram, web) use the same memory layer without modification.

#### Memory Normalization

Before storing or retrieving, natural language references are normalized to canonical keys. "My Oracle server," "the q7x instance," "the ARM box" all map to the same entity. This makes retrieval reliable across sessions where the same thing gets referred to differently.

### LLM Routing

Not every message needs an expensive cloud model call. The routing strategy:

| Route | When | Cost | Latency |
|-------|------|------|---------|
| **Memory only** | Answer exists in index | Free | Instant |
| **Ollama (local)** | Simple question, classification | Free | ~1-2s |
| **OpenRouter (cloud)** | Complex reasoning, multi-step tasks | API cost | 3-15s |

Triage classification runs on the local Ollama model. For the initial CLI, routing is simple — all messages go to OpenRouter. Smart routing is a later phase.

### Session Logging

Every conversation is written to a JSONL file:
```jsonl
{"timestamp": "2026-03-04T18:12:38Z", "role": "user", "content": "..."}
{"timestamp": "2026-03-04T18:12:40Z", "role": "assistant", "content": "..."}
```

The memory abstraction layer watches for new files and indexes them. This is the pipeline from conversation → persistent memory.

### Telegram Interface (Planned)

Telegram is the first communication channel beyond the CLI, chosen for:

- Simple, well-documented bot API
- Rich interaction: inline keyboards, file sharing, push notifications
- Mobile-first
- Pluggable — core agent logic isn't Telegram-specific

Key UX patterns planned:
- **Trust boundaries**: Inline keyboard approve/deny for system-modifying actions
- **Session commands**: `/new`, `/continue`, `/memory`, `/cost`
- **Response formatting**: Code blocks, chunking for Telegram's 4096-char limit

## Infrastructure

### Target Deployment

- **Compute**: ARM-based VPS or cloud instance (Oracle Cloud Free Tier, Hetzner ARM, etc.)
- **OS**: Ubuntu 24.04
- **Agent process**: Native, managed by systemd
- **Memory service**: Standalone process, managed by systemd
- **LLM (local)**: Ollama in Docker
- **Proxy**: Caddy for HTTPS

### Resource Requirements

- **CPU**: 2+ cores (4 recommended)
- **RAM**: 4GB minimum (8GB+ if running Ollama models resident)
- **Disk**: 20GB minimum
- **Network**: Outbound HTTPS to OpenRouter API
