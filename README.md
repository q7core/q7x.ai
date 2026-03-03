# q7x.ai

A system-level AI agent built from the ground up. Not a wrapper around someone else's framework — a clean, opinionated tool designed to be genuinely powerful *and* genuinely easy to use.

## What This Is

The agent space is split between two failure modes: tools built by brilliant engineers that are hostile to non-engineers, and pretty wrappers that are just a chat box over an API with no real depth. q7x targets the middle — a system-level agent that can actually operate on your infrastructure, remember what it's learned across sessions, and route tasks intelligently between local and cloud models.

Built on Anthropic's [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) with a custom memory layer, intelligent routing, and a Telegram-first interface.

## Architecture

```
Telegram ──▶ q7x Core ──▶ Claude Agent SDK ──▶ Your Server
  you         triage &       agentic runtime     bash, files,
  talk        routing        (tools, compaction)  code, APIs
  here        memory layer
              (SQLite)
                │
                ▼
              Ollama ──▶ Fast local tasks
              (local)    (triage, classification,
                          memory extraction)
```

**Core components:**

- **Claude Agent SDK** — The agentic runtime. Claude can use bash, read/write files, run tools, self-correct, and manage its own context window. We get this for free instead of building it from scratch.
- **Memory Layer** (custom) — SQLite-backed persistent memory with entity normalization. The agent extracts structured knowledge from conversations and retrieves relevant context on demand. Not raw chat logs — distilled facts, decisions, and preferences.
- **Intelligent Router** (custom) — Triages incoming messages to the right backend: instant answers from memory, fast responses from local Ollama, or full agentic sessions via the Agent SDK. Optimizes for speed, cost, and capability.
- **Telegram Interface** — First communication channel. Inline keyboards for trust boundary confirmations, structured responses, session management.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Why Build This

Three reasons:

1. **Immediate utility.** This isn't a learning exercise that lives in a drawer. The agent handles real tasks from day one — server management, document processing, research, workflow automation.

2. **Memory is the product.** Every existing agent forgets everything between sessions or dumps the entire history into context (expensive and dumb). q7x's memory layer — with entity normalization, lazy-loaded context, and transparent token management — is the actual differentiator.

3. **Dual deployment model.** Clone it for personal use with your Claude subscription, or bring your own API key for production/business use. Same codebase, one config switch.

## Deployment Models

### Personal Use (Subscription Auth)
Run on a Mac Mini, VPS, or home server. Authenticate with your Claude Max subscription via `claude login`. Usage counts against your plan — no per-token costs.

### Business Use (API Key Auth)
Set `ANTHROPIC_API_KEY` in your environment. Per-token billing with full cost tracking, budget caps, and the intelligent routing layer to minimize spend.

## Project Status

🏗️ **Building** — Active development. See [docs/implementation-plan.md](docs/implementation-plan.md) for the phased rollout.

## Setup

Coming soon. The project is in early development.

```bash
# Eventually:
git clone https://github.com/YOUR_USERNAME/q7x.ai.git
cd q7x.ai
cp .env.example .env
# Edit .env with your credentials
pnpm install
pnpm start
```

## Configuration

Copy the example files and fill in your values:

```bash
cp .env.example .env
cp config/config.example.json config/config.json
cp config/system-prompt.example.md config/system-prompt.md
```

See [.env.example](.env.example) for all available settings.

## Documentation

- [Architecture](docs/architecture.md) — System design and component overview
- [Implementation Plan](docs/implementation-plan.md) — Phased development roadmap
- [Architecture Decision Records](docs/adr/) — Why we chose what we chose

## License

[MIT](LICENSE)
