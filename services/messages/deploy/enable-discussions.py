"""Q7C-733: additive Caddy route and homepage link, preserving existing files."""
from pathlib import Path
import datetime, re, subprocess

source=Path('/home/ubuntu/q7x/caddy/Caddyfile')
home=Path('/home/ubuntu/q7x/caddy/index.html')
original=source.read_bytes(); homepage=home.read_bytes()
if b'@discussions path' in original or b'href="/discussions/"' in homepage:
    raise SystemExit('Discussion route/link already exists; inspect before editing')
pattern=rb'(?m)^q7x\.ai \{\n'
if len(re.findall(pattern,original))!=1 or homepage.count(b'<div class="status">Building</div>')!=1:
    raise SystemExit('Unexpected source structure; refusing to replace')
updated=re.sub(pattern,lambda m:m.group()+b'    @discussions path /discussions /discussions/*\n    reverse_proxy @discussions 172.18.0.1:3320\n\n',original,count=1)
updated_home=homepage.replace(b'<div class="status">Building</div>',b'<div class="status">Building</div>\n        <p class="contact"><a href="/discussions/">Open discussion workspace &rarr;</a></p>',1)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
candidate=source.with_name('Caddyfile.discussions-candidate-'+stamp)
candidate.write_bytes(updated)
def run(*args):subprocess.run(args,check=True)
remote='/tmp/Caddyfile.discussions-'+stamp
run('docker','cp',str(candidate),'q7x-caddy:'+remote)
run('docker','exec','q7x-caddy','caddy','validate','--config',remote,'--adapter','caddyfile')
if source.read_bytes()!=original or home.read_bytes()!=homepage:
    raise SystemExit('Source changed concurrently; refusing to write')
source.with_name('Caddyfile.before-discussions-'+stamp).write_bytes(original)
home.with_name('index.html.before-discussions-'+stamp).write_bytes(homepage)
source.write_bytes(updated)
try:run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
except subprocess.CalledProcessError:
    source.write_bytes(original)
    run('docker','exec','q7x-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
    raise
home.write_bytes(updated_home)
print('Discussion route and homepage link enabled; backup suffix:',stamp)
