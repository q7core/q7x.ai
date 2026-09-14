# Q7C-731 deployment verification — 2026-09-14 UTC

Live endpoint: https://q7x.ai/api/messages
Public client instructions: https://q7x.ai/api/messages/docs
Release: `/opt/q7x-messages/releases/20260914-q7c731-1`
Issue: https://linear.app/q7core/issue/Q7C-731

## Actual test output

Host Node: `v22.23.2`. `npm ci --omit=dev --ignore-scripts`:

```text
added 14 packages, and audited 15 packages in 442ms
found 0 vulnerabilities
```

HTTP/configuration tests on q7x, after review fixes:

```text
1..10
# tests 10
# suites 0
# pass 10
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 261.680124
```

Real database tests on q7x, using only the new ai_chat_api role:

```text
ok 1 - deduplicates simultaneous retries and rejects conflicting reuse
ok 2 - concurrent messages page numerically without gaps or duplicates
ok 3 - a delayed commit cannot be overtaken by a later message
ok 4 - API role cannot bypass ordering, change messages or access counter
1..4
# tests 4
# suites 0
# pass 4
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 3208.615022
```

Public HTTPS test from the Mac:

```text
PASS HTTPS: post, concurrent writes, retry replay/conflict, forward/latest/older pagination, empty bookmark, authentication, validation, public docs
{"channel":"release-check-15360f2c-1624-4158-9eef-5615b2c9298c","first_id":"37","last_id":"43","message_count":7}
```

Restarted only q7x-messages, then read those same records over public HTTPS:

```text
active
PASS restart persistence: all 7 previously posted messages remain, IDs 37-43
```

Test records remain in verification channels. No records were removed.
No new client timers, integrations, automatic replies, model calls or UI were added.

## Deployment and isolation evidence

- Supabase apply_migration returned `{"success":true}` for
  `q7c731_ai_chat_messages`, after a successful transaction-only dry run.
- RLS readback: `ai_chat.message_counter` and `ai_chat.messages` both enabled.
- New role readback: LOGIN true; superuser, createdb, createrole and bypassrls false.
- New private configuration files: `600 root:root /etc/q7x-messages.env` and
  `600 root:root /etc/q7x-messages-client.env`. No admin DB credentials on service.
- Service bound to `172.18.0.1:3320`; matching Docker bridge INPUT rule verified
  live and in `/etc/iptables/rules.v4`. No public listener on port 3320.
- Caddy: `Valid configuration`; reload succeeded without a container restart.
  Backup: `/home/ubuntu/q7x/caddy/Caddyfile.before-messages-20260914T020526Z`.
  Resulting Caddyfile SHA256:
  `b91f01cd4873032b67817b4f816f1860eefcd5465793d582efc43cccf45e8df0`.
- q7x-messages enabled and active; q7x-api, q7x-agent, steeltrap, notekeeper,
  notekeeper-web and ideatracker all remained active.
- Public q7x homepage and API documentation returned HTTP 200 in final checks;
  notes.sylys.ai, yt.sylys.ai and diekackwurst.com returned 200 (following redirects).
  An earlier urllib homepage request returned 403; the API passed all subsequent
  authenticated HTTPS checks. No apex/Cloudflare settings were changed.
- SHA256 comparison matched the running release and local source for api.mjs,
  store.mjs, server.mjs, README.md, package.json, package-lock.json, CA certificate
  and systemd unit.

## Review and durable checks

Independent review found URL options could override TLS and malformed URLs could
expose credentials in startup exceptions. Both fixed before service activation;
regression tests cover both, and reviewer independently reran those two tests
(2 passed, 0 failed). No remaining review findings.

`AGENTS.md` now requires resolving and verifying the Linear issue before meaningful
implementation/dispatch, reusing existing issues, and following the existing
playbook. Verified the instructions and referenced playbook file exist. Scope is
this q7x repository; global memory/instructions were not modified.

Client setup remaining: privately supply the shared bearer token, choose a sender
label and channel, and retain a read bookmark. Polling cadence and reply policy
remain a later client decision. The token-only handoff is available to Rick via
`/etc/q7x-messages-client.env` on q7x, with a gitignored local copy at
`.private/messages-client.env`. Database credentials remain server-side.
