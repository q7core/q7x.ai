# q7x.ai

A system-level AI agent built from the ground up. Not a wrapper around someone else's framework — a clean, opinionated tool designed to be genuinely powerful *and* genuinely easy to use.

## What This Is

The agent space is split between two failure modes: tools built by brilliant engineers that are hostile to non-engineers, and pretty wrappers that are just a chat box over an API with no real depth. q7x targets the middle — a system-level agent that can actually operate on your infrastructure, remember what it's learned across sessions, and route tasks intelligently between local and cloud models.

## Architecture

```
  you
   │
   ▼
q7x Core ──▶ LLM (OpenRouter / local Ollama)
   │
   ├──▶ Memory Abstraction Layer  (context injection, session indexing)
   │         └── SQLite
   │
   └──▶ Session log (JSONL)
```

**Core components:**

- **q7x Core** — The agent process. Manages conversation state, routes to the right LLM, injects memory context, logs sessions.
- **Memory Layer** (custom) — A standalone service that indexes session history, extracts entities and facts, and serves relevant context on demand via a simple HTTP interface. Not raw chat logs — structured knowledge retrieved selectively.
- **LLM Backends** — OpenRouter for cloud model access (frontier models), local Ollama for fast/private tasks. The agent routes based on task complexity.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Why Build This

Three reasons:

1. **Immediate utility.** This isn't a learning exercise that lives in a drawer. The agent handles real tasks from day one — server management, document processing, research, workflow automation.

2. **Memory is the product.** Every existing agent forgets everything between sessions or dumps the entire history into context (expensive and dumb). q7x's memory layer — with entity extraction, lazy-loaded context, and selective injection — is the actual differentiator.

3. **Two interfaces, one core.** CLI for direct use, Telegram bot for mobile and push notifications. Same agent logic underneath.

## Current Status

**MVP 0.1 — Working CLI with cross-session memory**

- Python CLI running on self-hosted infrastructure
- Cross-session memory via standalone memory abstraction service
- OpenRouter LLM backend (free preview model + paid fallback)
- Sessions logged as JSONL, indexed and queryable

🏗️ **In active development.** TypeScript rewrite and Telegram interface are next. See [docs/implementation-plan.md](docs/implementation-plan.md).

## Deployment

Designed to run on your own infrastructure — a VPS, home server, or cloud instance. Tested on Oracle Cloud ARM (Ubuntu 24.04). Minimal resource requirements: 2 cores, 4GB RAM, 10GB disk.

```bash
# Eventually:
git clone https://github.com/q7core/q7x.ai.git
cd q7x.ai
cp .env.example .env
# Edit .env with your credentials
pnpm install
pnpm start
```

*Full setup docs coming as the TypeScript build stabilises.*

## Configuration

```bash
cp .env.example .env
cp config/config.example.json config/config.json
```

See [.env.example](.env.example) for available settings.

## Documentation

- [Architecture](docs/architecture.md) — System design and component overview
- [Implementation Plan](docs/implementation-plan.md) — Phased development roadmap
- [Architecture Decision Records](docs/adr/) — Why we chose what we chose

## License

[MIT](LICENSE)
