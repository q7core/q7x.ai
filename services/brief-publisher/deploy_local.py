"""Install helper and its narrow desk route; leave workspace server and tunnel running."""
from pathlib import Path
import datetime, os, plistlib, subprocess, time, hashlib
SOURCE=Path(__file__).resolve().parent
HOME=Path('/Users/rproemer')
label='com.q7core.brief-publisher'
plist=HOME/'Library/LaunchAgents'/f'{label}.plist'
installed=plist.exists()
if installed and plistlib.loads(plist.read_bytes()).get('ProgramArguments')!=['/usr/bin/python3','-B',str(SOURCE/'server.py')]: raise SystemExit('Unrecognized existing helper; refusing update')
# Fail on an occupied port before installing anything.
import socket
if not installed:
 s=socket.socket();s.bind(('127.0.0.1',8766));s.close()
config=HOME/'srv/edge/Caddyfile';original=config.read_bytes()
anchor=b'http://desk.q7hub.com {\n'
if b'@briefPublish' in original: raise SystemExit('Publisher route already exists; inspect before updating')
if original.count(anchor)!=1:raise SystemExit('Unexpected desk route')
block=b'''    # Q7HU-783: same private Access audience, preserve Origin for CSRF validation.
    @briefPublish path /api/brief-publish/*
    reverse_proxy @briefPublish host.docker.internal:8766 {
        header_up Host localhost:8766
    }
'''
updated=original.replace(anchor,anchor+block,1)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=config.with_name('Caddyfile.before-brief-publisher-'+stamp)
candidate=config.with_name('Caddyfile.brief-publisher-candidate-'+stamp);candidate.write_bytes(updated)
def run(*a):subprocess.run(a,check=True)
run('docker','cp',str(candidate),'q7-caddy:/tmp/Caddyfile.brief-publisher')
run('docker','exec','q7-caddy','caddy','validate','--config','/tmp/Caddyfile.brief-publisher','--adapter','caddyfile')
plist.write_bytes(plistlib.dumps({'Label':label,'ProgramArguments':['/usr/bin/python3','-B',str(SOURCE/'server.py')],'RunAtLoad':True,'KeepAlive':True,'ProcessType':'Background','StandardOutPath':str(HOME/'Library/Logs/brief-publisher.log'),'StandardErrorPath':str(HOME/'Library/Logs/brief-publisher.log')}))
if not installed: run('launchctl','bootstrap',f'gui/{os.getuid()}',str(plist))
if config.read_bytes()!=original:raise SystemExit('Concurrent edge configuration edit; helper running but route not enabled')
backup.write_bytes(original);config.write_bytes(updated)
# OrbStack file sharing can lag a host write. Confirm exact container bytes first.
for attempt in range(30):
 mounted=subprocess.check_output(['docker','exec','q7-caddy','cat','/etc/caddy/Caddyfile'])
 if mounted==updated:break
 time.sleep(0.2)
else:raise SystemExit('Mounted configuration has not synchronized; route was not reloaded')
try:run('docker','exec','q7-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
except Exception:
 config.write_bytes(original);run('docker','exec','q7-caddy','caddy','reload','--config','/etc/caddy/Caddyfile','--adapter','caddyfile');raise
print('Private publishing route enabled; backup:',backup)
