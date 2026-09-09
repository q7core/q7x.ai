# CHECKPOINT — Q7C-706: Migrate Note Keeper, IdeaTracker, diekackwurst.com from Sylys → q7x

Started: 2026-09-08 (UTC 2026-09-09 ~01:05). Executor: Claude Code CLI.
Ticket: https://linear.app/q7core/issue/Q7C-706

## Status legend
- [ ] pending · [~] in progress · [x] DONE (timestamp UTC)

## Steps
- [x] 1. Preflight on q7x — DONE 01:10
  - Node v22.23.2, Python 3.12.3, q7x-caddy + q7x-ollama up, ports 3100/3210 free.
  - **Supabase direct host `db.noynhxxnmjljifabkkgg.supabase.co` is AAAA-only (2600:1f16:…); q7x has NO global IPv6 address → `[Errno 101] Network is unreachable`.** Sylys had a global v6 addr (2a02:4780:2d:b759::1), which is why direct-connect worked there.
  - Pooler `aws-1-us-east-2.pooler.supabase.com` (documented in playbook keys.md § Direct DB users, NOT guessed) TCP-reachable from q7x on 5432 (session) and 6543 (transaction). Decision: use **session mode :5432** (semantic parity: asyncpg prepared statements + postgres.js prepare both work; no code changes). Auth to be proven with a real query before any env file is written (see step 3b notes).
  - GitHub from q7x: no deploy key (`Permission denied (publickey)`) → rsync path.
  - `rproemer/YouTubeIdeaTracker` not visible to the Mac's SSH key; `gh` not installed. Sylys clone at `/var/www/yt.sylys.ai.app` is clean at `9b94462` (matches ticket) but its remote URL embeds a PAT (burned per ROTATION-REPORT A2). Source will be copied read-only from Sylys → Mac `~/dev/YouTubeIdeaTracker` → q7x. PAT will not be used or copied to q7x.
  - Existing iptables: `-A INPUT -s 172.18.0.0/16 -p tcp -m multiport --dports 8000,7331 …` and a separate 9119 rule.
- [ ] 2. iptables 3100+3210 + persist
- [ ] 3a. Sylys: disable nk-watchdog.timer + notekeeper.service (ONLY Sylys change)
- [ ] 3b. Note Keeper bot on q7x (/opt/notekeeper, venv, .env, unit)
- [ ] 3c. Note Keeper web on q7x (/opt/notekeeper-web, npm ci/build, .env HOST=0.0.0.0, unit)
- [ ] 3d. nk-watchdog on q7x
- [ ] 4. IdeaTracker on q7x (/opt/ideatracker, npm ci/build, unit :3100)
- [ ] 5. diekackwurst static + sylys landing archive + compose volume
- [ ] 6. Caddy blocks + compose up -d + validate + pre-DNS smoke test
- [ ] 7. DNS flip (Cloudflare) — see "DNS before" below
- [ ] 8. Verify (real output)
- [ ] 9. Encode state change (playbook project files, commit/push toolkit, zip)
- [ ] 10. Summary

## DNS before (recorded 01:12 UTC, all proxied=true, ttl=auto)
Zone sylys.ai (df361771f416b87815f4b8ebe6706c53):
- A notes.sylys.ai → 187.77.12.201  id e0659e2fb29a08e069c971ef97e8a49d
- A yt.sylys.ai    → 187.77.12.201  id 49405e88d30259b2db3c1a15c38007c6
Zone diekackwurst.com (319a7454d7bbde6f5c3695e97546bd20):
- A     diekackwurst.com     → 187.77.12.201       id a12069f58c5f1b561ff8ce762e58dd9d
- CNAME www.diekackwurst.com → diekackwurst.com    id a917c409ee877d47244ca60ec21262f4 (CNAME, not A — will keep as CNAME, just un-proxy)
Rollback = PATCH each record back to the value above with proxied=true.
Untouched by design: sylys.ai, www, gw, brief (already → q7x), stcouncil.

## Sylys state before 3a (01:12 UTC)
notekeeper=active/enabled, notekeeper-web=active, nk-watchdog.timer=active/enabled, pm2 ideatracker online (left running).
