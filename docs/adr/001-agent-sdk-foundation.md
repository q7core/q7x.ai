# ADR-001: Claude Agent SDK as Foundation

**Status:** Accepted  
**Date:** 2026-03-02

## Context

q7x needs an agentic runtime — the core loop where the AI model can use tools (bash, file I/O, web search), observe results, reason about next steps, and self-correct. Building this from scratch is a significant engineering effort with well-known pitfalls (context management, tool orchestration, error recovery, session persistence).

Anthropic's Claude Agent SDK (formerly Claude Code SDK) provides exactly this runtime. It's the engine that powers Claude Code, extracted into a library available as both Python and TypeScript packages.

### Alternatives Considered

1. **Build from scratch** — Maximum control, but months of work replicating solved problems (context compaction, tool orchestration, permission management). High risk of subtle bugs in the agentic loop.

2. **LangChain / LangGraph** — Popular frameworks, but heavy abstraction layers that obscure what's actually happening. Philosophy conflicts with q7x's "not a black box" principle.

3. **OpenClaw / NanoClaw** — Community tools that wrap Claude Code. Dependency on third-party maintenance, unclear licensing trajectory, limited architectural control.

4. **Raw Anthropic API + custom loop** — More control than Agent SDK, but we'd still be rebuilding compaction, tool management, and session persistence.

## Decision

Use the Claude Agent SDK as the agentic runtime. Build q7x's differentiating features (memory layer, intelligent routing, Telegram UX) on top of it.

## Rationale

- **Proven runtime**: Powers Claude Code, which Anthropic uses internally. Battle-tested at scale.
- **Free capabilities**: Context compaction, tool orchestration, MCP integration, session persistence, cost budgeting — all included.
- **Flexible auth**: Supports both subscription (personal) and API key (business) authentication with no code changes.
- **Right level of abstraction**: Provides the agentic loop without dictating application architecture. We control the memory layer, routing, and UX entirely.
- **Active development**: Anthropic is investing heavily in the SDK (renamed from "Code SDK" to "Agent SDK" to reflect broader vision).

## Tradeoffs

- **Vendor lock-in**: Tightly coupled to Anthropic's Claude models. If we need to switch providers, the Agent SDK layer would need replacement. Mitigated by keeping the memory layer and routing logic provider-agnostic.
- **ARM64 compatibility**: The SDK depends on the Claude Code CLI, which has had ARM64 Linux issues historically. Needs validation on target hardware. Fallback: Python SDK.
- **Proprietary license**: The Agent SDK is not open source (proprietary Anthropic license). This limits our ability to fork or modify the runtime itself.

## Consequences

- q7x's core agentic loop is provided, not built. Development effort focuses on differentiation: memory, routing, UX.
- The project depends on Anthropic maintaining and improving the SDK.
- Architecture must keep a clean boundary between "Agent SDK concerns" and "q7x concerns" so the runtime could theoretically be swapped.
