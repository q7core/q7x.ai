# Brief publishing

Implementation: [Q7HU-783](https://pm.q7hub.com/q7hub/issues/Q7HU-783).

The private Briefs Publish button prepares an inert snapshot for review, then requires a separate public-audience checkbox and confirmation. It never publishes on page load. Canonical source files remain on q7hub. Public copies are immutable, independent snapshots at `https://q7x.ai/pub/<seven-alphanumeric>.html`.

The helper listens only on 127.0.0.1:8766. The existing Cloudflare Access desk audience protects its narrow Caddy route. POST requires the exact desk Origin, Host, JSON type and custom header. There is no CORS, public write API, new credential, or credential in JavaScript. Preview tokens expire after 30 minutes. The read-only workspace server and its authentication remain intact.

Only the selected Briefs-root HTML file, shared CSS, and explicitly referenced raster images/CSS in `attachments/<brief-stem>/` are eligible. Files are embedded, never recursively copied. Symlinks, traversal, external assets, dynamic CSS and oversized snapshots fail closed. Scripts, forms, comments, private links and interactive SVG are omitted; the user reviews the exact result. This is not a secret detector: visible text and image content require human review. Recipient copies cannot be recalled.

Oracle receives bytes through the existing q7xvps SSH identity and existing sudo capability. `receiver.py` is installed root-owned at `/opt/q7x-publisher/receiver.py`; output is root-owned under `/var/www/steeltrap/.q7x-public`, exposed through the existing read-only mount solely by the q7x `/pub` route. The steeltrap direct path is blocked. No listing or arbitrary filename is served. Atomic exclusive creation prevents overwrites; identical retries use the same URL. Success requires an unauthenticated HTTPS fetch with no redirects and an exact byte match. Uncertain outcomes return the possible public URL and keep the same snapshot/code for retry.

## Deployment

Run `python3 -m unittest discover -s services/brief-publisher -v` in the repository. Copy the receiver using the existing SSH route, install it root-owned, and create the output directory root-owned mode 0755. Run `deploy_oracle.py` via SSH as ubuntu. It validates a narrow Caddy change, preserves an exact backup and reloads Caddy; it does not restart containers. Run `deploy_local.py` on q7hub from this directory to install the helper LaunchAgent and validate/reload the narrow desk route. Then run `integrate_controls.py`; it backs up every modified Brief and never sends content to Oracle. Add this shared script to any new custom Brief format; normal brief-v1.js loads it automatically.

Only synthetic documents may be used for acceptance. Keep real briefs private unless Rick explicitly confirms publication through their controls. Verify both anonymous private-route denial and public synthetic page byte equality.

## Recovery

Public snapshots are separate from private source. Retiring an exact public file requires removing/moving that publication on Oracle; retained recipient copies are outside control. To disable publishing, remove only the narrow desk publishing route and unload only `com.q7core.brief-publisher`; restore exact backed-up Caddy content only after checking for intervening edits. Private workspace service stays running. Disable public delivery by removing the exact public Caddy route; preserve snapshot files for recovery. Do not restore a whole old configuration over unrelated changes.
