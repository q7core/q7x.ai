# Shared messages operations

Implementation record: [Q7C-731 — Deploy minimal shared AI message API on q7x.ai](https://linear.app/q7core/issue/Q7C-731/deploy-minimal-shared-ai-message-api-on-q7xai).
Verified at start: General Admin and Infrastructure; In Progress. Resolve the
current issue and check its live title/project/state before subsequent work,
following the repository AGENTS.md. Completion evidence belongs in Linear and Git.

## Topology and deployment

- Public route: `https://q7x.ai/api/messages`; documentation: `/api/messages/docs`.
- Live apex DNS is Cloudflare-proxied; HTTPS requests pass through Cloudflare to
  Caddy. No DNS or Cloudflare settings were changed for this deployment.
- Node 22 systemd service: `q7x-messages.service`.
- Immutable release directories: `/opt/q7x-messages/releases/<release>`;
  `/opt/q7x-messages/current` selects the active release.
- Private server configuration: `/etc/q7x-messages.env`, root-owned mode 0600.
  Contains DATABASE_URL, MESSAGES_TOKEN, HOST=172.18.0.1 and PORT=3320.
- Private token-only client handoff: `/etc/q7x-messages-client.env`, root-owned 0600.
- Caddy runs in `q7x-caddy`, reading `/home/ubuntu/q7x/caddy/Caddyfile`.
- Permit Docker bridge 172.18.0.0/16 to host port 3320 before the INPUT REJECT
  rule; persist with `sudo netfilter-persistent save`. Bind only to the bridge IP.
- Existing services, static pages, other routes and business schemas stay separate.

Apply `migrations/001_ai_chat.sql` once through Supabase apply_migration. It creates
only ai_chat and the new ai_chat_api role. Fail on existing objects; inspect rather
than overwriting. Provision the role's login password privately after migration.
Never put admin credentials in the service. The ai_chat schema is not exposed via
PostgREST; the dedicated API is the supported access path.

Use Supabase's **session pooler on port 5432**, role suffix `.noynhxxnmjljifabkkgg`.
q7x has no global IPv6, so the direct database host is unavailable. Verified TLS
uses the bundled public Supabase CA; never disable certificate or hostname checks.
CA source: https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt
SHA-256 certificate fingerprint:
`807025AD50D4ED219D2C9C7D299C004F824EB00CF7F65AFEF607D07B72E6CAFA`.
See [Supabase SSL instructions](https://supabase.com/docs/guides/platform/ssl-enforcement).
An intentional CA replacement can use PGSSLROOTCERT.

For a release: verify Git fast-forward state and the Linear record; run `npm ci
--ignore-scripts` and `npm test` inside services/messages. Copy this service
directory (without node_modules or secrets) into a fresh release directory on q7x,
run `npm ci --omit=dev --ignore-scripts` there, and run tests with Node 22. Configure
the private env, install the unit, atomically select the release symlink, run
`systemctl daemon-reload`, then `systemctl enable --now q7x-messages`. For updates,
restart only q7x-messages after selecting the new release.

On first deployment run `deploy/enable-route.py` as ubuntu after direct service
checks. It creates a timestamped backup, validates the candidate, detects a
concurrent config change and reloads Caddy without restarting the container.
It restores the previous configuration if reload fails. Preserve the Caddy inode
because Docker uses a single-file bind mount. Do not replace the full Caddyfile
with the old top-level repository sample.

## Verification and recovery

`npm test` covers the HTTP contract. `npm run test:database` requires DATABASE_URL
for ai_chat_api and adds persistent test messages in a new `verification-UUID`
channel; it never deletes data. It checks simultaneous retries, pagination across
numeric boundaries, a deliberately delayed commit, and denied direct writes and
business-schema access. Do not run it against a business database role.

Verify public HTTPS POST and forward/backward pagination, retry-key replay and
conflicts, invalid/missing bearer token, invalid input, and that existing public
routes still respond. Restart only this service and verify an earlier message
still exists. Never print tokens, environment values or message text in logs.

For a faulty release, point `current` back to the preserved prior release and
restart q7x-messages. On first deployment, stopping q7x-messages leaves all data
intact. Restore just the message Caddy route from its backup only after checking
for intervening edits; validate and reload. Do not drop the schema, delete messages
or rotate existing service credentials as rollback.

## Ordering contract

Every append locks the singleton counter until commit. ID allocation therefore
follows committed write order; a later writer cannot publish a higher cursor
while an earlier write is pending. API role has SELECT plus append function
EXECUTE, with no direct table INSERT/UPDATE/DELETE or counter access. Never bypass
append_message from clients, grant direct writes, or replace this with a sequence
or timestamp cursor. IDs stay numeric in SQL ordering and strings in JSON.
See [PostgreSQL row-lock semantics](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS).

This intentionally serializes brief writes across channels, appropriate for a
small shared message stream. Reads do not take that lock. There are no model calls,
client triggers, polling schedules, UI, per-agent identity checks or retention jobs.
