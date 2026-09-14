# Q7C-733 — discussion workspace

Verified Linear issue: https://linear.app/q7core/issue/Q7C-733
Title: Create agent discussion landing page with portable client placeholders.
Project: General Admin and Infrastructure. State: In Progress at implementation.
Parent Q7C-732 remains open for live dispatch/adapters.

1. Add buildless HTML/CSS/ES modules at public/discussions, served at /discussions/
   by an explicit file allowlist in the existing Node service. Caddy routes this
   path to that service; preserve API and existing homepage, adding only a link.
2. Render five participant choices from plain client definitions and capabilities.
   Draft preparation builds the existing API's sender/channel/text shape. No DI
   container, inheritance, fake connectivity, messages or execution.
3. Prepare/edit/save a local browser draft, with explicit device-only status,
   input bounds and resilient storage failure handling. Controls for live runs
   stay disabled. Outcomes remain honest empty states.
4. Check contract behavior and existing API tests, then inspect desktop/mobile
   layout and interactions in external Chrome. Stage a new immutable service
   release, validate/reload Caddy, verify live page and API, commit/push and close
   only Q7C-733 with actual evidence.

## Product context

Register: product. User: Rick, choosing any subset of his agent tools to discuss
a question with his own perspective. Immediate success is a usable opening draft;
later integrations provide real discussion. Personality: precise, open, composed.
Keep the lowercase q7x mark and navy/cyan direction. Use familiar controls, clear
status and restrained motion. Avoid fabricated activity and technical launch
details. Aim for WCAG AA contrast, native keyboard controls and reduced motion.
