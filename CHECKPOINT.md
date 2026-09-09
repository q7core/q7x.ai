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
- [x] 2. iptables 3100+3210 + persist — DONE 01:16. New rule inserted after the 8000,7331 rule: `-A INPUT -s 172.18.0.0/16 -p tcp -m multiport --dports 3100,3210 -m comment --comment "Docker compose to host: ideatracker(3100) notekeeper-web(3210)" -j ACCEPT`; `netfilter-persistent save` OK; present in /etc/iptables/rules.v4.
- [ ] 3a. Sylys: disable nk-watchdog.timer + notekeeper.service (ONLY Sylys change)
- [~] 3b. Note Keeper bot on q7x — 01:25 prepared: /opt/notekeeper ← rsync of ~/dev/notekeeper@e596276 (bot files only), venv built (asyncpg 0.30.0, PTB 21.7), /opt/notekeeper/.env = payload with ONLY DATABASE_URL host swapped to session pooler (auth proven 01:20: notekeeper_user via aws-1-us-east-2.pooler.supabase.com:5432, search_path=notekeeper,public, 478 notes). Unit installed (User=ubuntu, Restart=always). Start pending 3a.
- [~] 3c. Note Keeper web — /opt/notekeeper-web ← repo @e596276; web/.env = payload with pooler hosts + HOST=0.0.0.0 (PORT=3210, ORIGIN unchanged); unit installed. npm ci running detached (~/q7c706-logs/nkweb-npmci.log).
- [~] 3d. nk-watchdog on q7x — script + unit + timer installed 01:25 (script recreated from Sylys /usr/local/bin/nk-watchdog, alert text tagged '(q7x)'); enable pending 3a.
- [~] 4. IdeaTracker — /opt/ideatracker ← Sylys working tree @9b94462 (via Mac ~/dev/YouTubeIdeaTracker, PAT stripped, no .git on q7x); .env.local = payload with pooler host (video_tracker_user auth proven, search_path=video_tracker); unit installed (next start -p 3100 -H 0.0.0.0, NODE_OPTIONS=--dns-result-order=ipv4first). npm ci running detached (~/q7c706-logs/it-npmci.log).
- [x] 5. diekackwurst static + sylys landing archive + compose volume — DONE 01:25. /var/www/kackwurst (1.9M, root:root, a+rX), /var/www/sylys-landing-archive (index.html + admin/, NOT served). docker-compose.yml: added `/var/www/kackwurst:/srv/kackwurst:ro` (backup docker-compose.yml.bak-q7c706).
- [~] 6. Caddy — blocks for notes.sylys.ai, yt.sylys.ai, diekackwurst.com, www.diekackwurst.com appended 01:25 (backup caddy/Caddyfile.bak-q7c706); `caddy validate` = Valid configuration. `docker compose up -d` deferred until apps are up (avoids LE issuance churn while DNS still points at Sylys).
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

## Scratch artifacts
- Unit files, watchdog script, Caddy blocks, env rewriter: `.private/scratch/20260909-q7c706-units/` (also copied to q7x `~/q7c706-units/`). Build logs on q7x: `~/q7c706-logs/`.
