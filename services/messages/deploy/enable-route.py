"""Run on q7x after the service is healthy. Preserve unrelated Caddy configuration."""
from pathlib import Path
import datetime, hashlib, re, subprocess

source = Path('/home/ubuntu/q7x/caddy/Caddyfile')
original = source.read_bytes()
marker = b'    # q7x shared messages\n'
if marker in original:
    raise SystemExit('Message route already exists; inspect before changing it')
anchor = b'q7x.ai {\n'
if len(re.findall(rb'(?m)^q7x\.ai \{\n', original)) != 1:
    raise SystemExit('Unexpected Caddyfile structure')
updated = original.replace(anchor, anchor + marker +
    b'    @messages path /api/messages /api/messages/*\n'
    b'    reverse_proxy @messages 172.18.0.1:3320\n\n', 1)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
candidate = source.with_name('Caddyfile.messages-candidate-' + stamp)
backup = source.with_name('Caddyfile.before-messages-' + stamp)
candidate.write_bytes(updated)
def run(*args):
    subprocess.run(args, check=True)
container_candidate = '/tmp/Caddyfile.messages-' + stamp
run('docker','cp',str(candidate),'q7x-caddy:'+container_candidate)
run('docker','exec','q7x-caddy','caddy','validate','--config',container_candidate,'--adapter','caddyfile')
if source.read_bytes() != original:
    raise SystemExit('Caddyfile changed concurrently; refusing to replace it')
backup.write_bytes(original)
# Write in place: Docker bind-mounts this inode. Do not rename over it.
source.write_bytes(updated)
try:
    run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
except subprocess.CalledProcessError:
    source.write_bytes(original)
    run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
    raise
print('Message route enabled; backup:', backup)
print('Caddyfile SHA256:', hashlib.sha256(updated).hexdigest())
