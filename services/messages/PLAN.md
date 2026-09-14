# Shared message API — Q7C-731

Approved scope: a standalone HTTPS service on q7x.ai, backed by a new ai_chat
schema in the existing Supabase project. Reuse Node 22, systemd and Caddy.
No UI, model calls, client integrations, client timers or messaging platforms.

1. Verify existing host, routes, database and fast-forward Git state.
2. Write HTTP contract tests, demonstrate failures, implement built-in Node HTTP
   service with one dependency (pg). Validate bearer token, JSON and query sizes.
3. Add ai_chat.messages and a transactional counter. Only a security-definer
   append function allocates IDs, holding the counter lock through commit.
   A dedicated role can read messages and execute append, with no direct writes.
4. Apply additive migration, configure private credentials, test real database
   deduplication and delayed-commit ordering. Never mutate other schemas.
5. Deploy companion systemd service and an exact Caddy route with config backup,
   validation and reload. Keep existing services running.
6. Verify HTTPS writes, reads, pagination, auth, restart persistence and existing
   routes; publish instructions, preserve evidence, commit/push and close ticket.

POST /api/messages accepts sender, channel (general by default), text and an
optional Idempotency-Key header. GET without a cursor returns latest N in ascending
order; after reads forward, before pages through older history. IDs are decimal
strings. Forward cursors advance only to delivered messages. Every page states
its direction; has_more is always relative to that direction.
