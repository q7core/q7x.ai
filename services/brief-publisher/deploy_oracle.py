"""Run over existing SSH as ubuntu; narrow, validated Caddy reload (no restart)."""
from pathlib import Path
import datetime, subprocess, re

def run(*a): subprocess.run(a,check=True)
source=Path('/home/ubuntu/q7x/caddy/Caddyfile'); original=source.read_bytes()
marker=b'    # Q7HU-783 public Brief snapshots\n'
if marker in original: raise SystemExit('Publisher route already installed; inspect before updating.')
if len(re.findall(rb'(?m)^q7x\.ai \{\n',original))!=1 or original.count(b'\nsteeltrap.io {\n')!=1: raise SystemExit('Unexpected live Caddy configuration')
block=b'''    # Q7HU-783 public Brief snapshots
    @published path_regexp published ^/pub/[A-Za-z0-9]{7}\\.html$
    handle @published {
        uri strip_prefix /pub
        root * /srv/steeltrap/.q7x-public
        header X-Robots-Tag "noindex, nofollow"
        header Cache-Control "no-store"
        header Referrer-Policy "no-referrer"
        header Content-Security-Policy "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; sandbox"
        file_server
    }
    @pubOther path /pub /pub/*
    handle @pubOther {
        respond 404
    }

'''
updated=original.replace(b'q7x.ai {\n',b'q7x.ai {\n'+block,1).replace(b'\nsteeltrap.io {\n',b'\nsteeltrap.io {\n    respond /.q7x-public* 404\n',1)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
candidate=source.with_name('Caddyfile.publisher-candidate-'+stamp);backup=source.with_name('Caddyfile.before-publisher-'+stamp)
candidate.write_bytes(updated)
container='/tmp/Caddyfile.publisher-'+stamp
run('docker','cp',str(candidate),'q7x-caddy:'+container)
run('docker','exec','q7x-caddy','caddy','validate','--config',container,'--adapter','caddyfile')
if source.read_bytes()!=original: raise SystemExit('Concurrent Caddy edit; refusing update')
backup.write_bytes(original);source.write_bytes(updated)
try:run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
except Exception:
 source.write_bytes(original);run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile');raise
print('Public route enabled; backup:',backup)
