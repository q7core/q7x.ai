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
- [x] 3a. Sylys — DONE 01:10 UTC. `systemctl disable --now nk-watchdog.timer notekeeper.service` → notekeeper inactive/disabled, nk-watchdog.timer inactive/disabled. notekeeper-web still active, pm2 ideatracker still online, caddy active. Nothing deleted (verified paths still present 01:16).
- [x] 3b. Note Keeper bot on q7x — DONE 01:10:43 (enabled+started after 3a; journal: getMe 200, `store ready`, deleteWebhook, getUpdates every ~10s; 0 × 409/Conflict). Prep notes: — 01:25 prepared: /opt/notekeeper ← rsync of ~/dev/notekeeper@e596276 (bot files only), venv built (asyncpg 0.30.0, PTB 21.7), /opt/notekeeper/.env = payload with ONLY DATABASE_URL host swapped to session pooler (auth proven 01:20: notekeeper_user via aws-1-us-east-2.pooler.supabase.com:5432, search_path=notekeeper,public, 478 notes). Unit installed (User=ubuntu, Restart=always). Start pending 3a.
- [x] 3c. Note Keeper web — DONE 01:12:32 (`npm ci` + `vite build` OK, `Listening on http://0.0.0.0:3210`, `curl 127.0.0.1:3210/` → 303 → /login). Notes: — /opt/notekeeper-web ← repo @e596276; web/.env = payload with pooler hosts + HOST=0.0.0.0 (PORT=3210, ORIGIN unchanged); unit installed. npm ci running detached (~/q7c706-logs/nkweb-npmci.log).
- [x] 3d. nk-watchdog on q7x — DONE 01:10:41 (timer enabled; first run fired immediately and restarted the 0-second-old bot once → one spurious ⚠️/✅ Telegram alert pair; steady state healthy). Notes: — script + unit + timer installed 01:25 (script recreated from Sylys /usr/local/bin/nk-watchdog, alert text tagged '(q7x)'); enable pending 3a.
- [x] 4. IdeaTracker — DONE 01:12:33 (`npm ci` + `next build` OK — 5 routes; `Ready in 513ms` on 0.0.0.0:3100; `curl 127.0.0.1:3100/` → 200, `/videos` → 200). Notes: — /opt/ideatracker ← Sylys working tree @9b94462 (via Mac ~/dev/YouTubeIdeaTracker, PAT stripped, no .git on q7x); .env.local = payload with pooler host (video_tracker_user auth proven, search_path=video_tracker); unit installed (next start -p 3100 -H 0.0.0.0, NODE_OPTIONS=--dns-result-order=ipv4first). npm ci running detached (~/q7c706-logs/it-npmci.log).
- [x] 5. diekackwurst static + sylys landing archive + compose volume — DONE 01:25. /var/www/kackwurst (1.9M, root:root, a+rX), /var/www/sylys-landing-archive (index.html + admin/, NOT served). docker-compose.yml: added `/var/www/kackwurst:/srv/kackwurst:ro` (backup docker-compose.yml.bak-q7c706).
- [x] 6. Caddy — DONE 01:13 (`docker compose up -d` recreated q7x-caddy with the kackwurst mount; validate OK; container→host 3210=303, 3100=200; Host-header smoke: all four → 308 https). Detail: blocks for notes.sylys.ai, yt.sylys.ai, diekackwurst.com, www.diekackwurst.com appended 01:25 (backup caddy/Caddyfile.bak-q7c706); `caddy validate` = Valid configuration. `docker compose up -d` deferred until apps are up (avoids LE issuance churn while DNS still points at Sylys).
- [x] 7. DNS flip — DONE 01:14 UTC via Cloudflare API (PATCH, all `proxied:false`, ttl 300): notes.sylys.ai A → 152.70.114.120; yt.sylys.ai A → 152.70.114.120; diekackwurst.com A → 152.70.114.120; www.diekackwurst.com CNAME → diekackwurst.com (kept as CNAME, un-proxied). Then `docker restart q7x-caddy` → all 4 LE certs obtained in 81s.
- [x] 8. Verify — DONE 01:16 UTC. Real output:
  ```
  notes.sylys.ai      HTTP/2 303 → /login?next=%2F   CN=notes.sylys.ai      issuer Let's Encrypt YE2  exp 2026-12-08  verify ok
  yt.sylys.ai         HTTP/2 200                      CN=yt.sylys.ai         issuer Let's Encrypt YE2  exp 2026-12-08  verify ok
  diekackwurst.com    HTTP/2 200                      CN=diekackwurst.com    issuer Let's Encrypt YE1  exp 2026-12-08  verify ok
  www.diekackwurst.com HTTP/2 301 → https://diekackwurst.com/  CN=www.diekackwurst.com  verify ok
  dig @1.1.1.1 / @8.8.8.8: all three → 152.70.114.120 (propagated by 01:16)
  curl (system resolver) remote_ip=152.70.114.120 for all three
  systemctl: notekeeper active (PID 58193), notekeeper-web active (58549), ideatracker active (58548), nk-watchdog.timer active(waiting); all enabled
  getUpdates last 3 min: 18 · 409/conflict: 0 · pm2 on q7x: none
  Sylys: notekeeper inactive/disabled, nk-watchdog.timer inactive/disabled, notekeeper-web active, caddy active; /opt/notekeeper, /opt/notekeeper-web, /var/www/yt.sylys.ai.app, /var/www/sylys.ai/kackwurst, unit + watchdog files all still present
  ```
  Pending Rick: DM @rpr_notekeeper_bot for the end-to-end capture check.
- [x] 9. Encode — DONE 01:17. claude-toolkit `af6f0e2` (q7x.md, notekeeper.md, yt-idea-tracker.md) + `2a0408d` (zip rebuild), pushed. keys.md (gitignored) updated in place: DB-user table 'Used by' → q7x, pooler note, NK server env → q7x. sync.sh skipped by design (targets Sylys). Follow-up ticket Q7C-707 (stale notekeeper deploy script/units/snippet; IdeaTracker repo access from the Mac).
- [x] 10. Summary — delivered in CC session output + Linear comment.

## DNS before (recorded 01:05 UTC, all proxied=true, ttl=auto)
Zone sylys.ai (df361771f416b87815f4b8ebe6706c53):
- A notes.sylys.ai → 187.77.12.201  id e0659e2fb29a08e069c971ef97e8a49d
- A yt.sylys.ai    → 187.77.12.201  id 49405e88d30259b2db3c1a15c38007c6
Zone diekackwurst.com (319a7454d7bbde6f5c3695e97546bd20):
- A     diekackwurst.com     → 187.77.12.201       id a12069f58c5f1b561ff8ce762e58dd9d
- CNAME www.diekackwurst.com → diekackwurst.com    id a917c409ee877d47244ca60ec21262f4 (CNAME, not A — will keep as CNAME, just un-proxy)
Rollback = PATCH each record back to the value above with proxied=true.
Untouched by design: sylys.ai, www, gw, brief (already → q7x), stcouncil.

## Sylys state before 3a (01:05 UTC)
notekeeper=active/enabled, notekeeper-web=active, nk-watchdog.timer=active/enabled, pm2 ideatracker online (left running).

## Scratch artifacts
- Unit files, watchdog script, Caddy blocks, env rewriter: `.private/scratch/20260909-q7c706-units/` (also copied to q7x `~/q7c706-units/`). Build logs on q7x: `~/q7c706-logs/`.

## Timestamp note
Early entries were written with estimated clock values; authoritative times are the q7x journal (bot start 01:10:43, web/ideatracker 01:12:32, DNS PATCH ~01:14, certs by 01:15:30, verification 01:16 UTC 2026-09-09).

## Rollback (if ever needed)
1. Cloudflare: PATCH the four records back to 187.77.12.201 / CNAME diekackwurst.com with `proxied:true`.
2. Sylys: `systemctl enable --now notekeeper.service nk-watchdog.timer` (only after `sudo systemctl disable --now notekeeper` on q7x — single poller rule).
3. q7x: `cp caddy/Caddyfile.bak-q7c706 caddy/Caddyfile; cp docker-compose.yml.bak-q7c706 docker-compose.yml; docker compose up -d`.
