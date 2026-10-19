"""Private loopback publishing helper. Existing Cloudflare desk auth stays at edge."""
import hashlib, json, secrets, string, subprocess, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from snapshot import snapshot, SnapshotError, MAX_BYTES
ROOT=Path('/Users/rproemer/q7core/Workbench/Briefs')
ORIGIN='https://desk.q7hub.com'
PORT=8766
PENDING={}; LOCK=threading.Lock()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def verify(url,data):
    request=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'Q7BriefPublisher/1'})
    with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as r:
        return r.status==200 and r.headers.get_content_type()=='text/html' and r.read(MAX_BYTES+1)==data

def publish(item):
    if not item.get('code'): item['code']=''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(7))
    code=item['code']; data=item['data']; url='https://q7x.ai/pub/'+code+'.html'
    if item.get('attempted'):
        try:
            if verify(url,data): return {'url':url,'verified':True}
        except Exception: pass
        # Same code and identical bytes are idempotent at the receiver.
    item['attempted']=True
    try:
        p=subprocess.run(['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','q7xvps','sudo','-n','/usr/bin/python3','/opt/q7x-publisher/receiver.py',code],input=data,capture_output=True,timeout=45)
        if p.returncode==73:
            item.pop('code'); item.pop('attempted'); return {'error':'Link collision; click Publish again to allocate a fresh link.'}
        if p.returncode or p.stdout.decode().strip()!=hashlib.sha256(data).hexdigest(): raise RuntimeError('transfer')
        if not verify(url,data): raise RuntimeError('verification')
        return {'url':url,'verified':True}
    except Exception:
        return {'url':url,'verified':False,'error':'Publication outcome is not confirmed. This URL may already be public. Retry verification using Publish again; do not create another preview.'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,status,value):
        data=json.dumps(value).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self): self.respond(405,{'error':'Use the Publish control on an individual private brief.'})
    def do_POST(self):
        self.connection.settimeout(10)
        if self.headers.get('Host')!='localhost:'+str(PORT) or self.headers.get('Origin')!=ORIGIN or self.headers.get('X-Brief-Publish')!='1' or self.headers.get('Content-Type')!='application/json':
            self.respond(403,{'error':'Publish from the authenticated desk.q7hub.com brief.'}); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<4096: raise ValueError()
            req=json.loads(self.rfile.read(n)); now=time.time()
            with LOCK:
                for token,item in list(PENDING.items()):
                    if now-item['time']>1800 and not item.get('busy'): del PENDING[token]
                if self.path=='/api/brief-publish/prepare':
                    if len(PENDING)>=12: raise SnapshotError('Too many previews. Close them and retry in 30 minutes.')
                    data,assets=snapshot(ROOT,req.get('name',''))
                    token=secrets.token_urlsafe(32); PENDING[token]={'data':data,'time':now}
                    result={'token':token,'html':data.decode(),'assets':assets,'sha256':hashlib.sha256(data).hexdigest()}
                elif self.path=='/api/brief-publish/confirm':
                    item=PENDING.get(req.get('token',''))
                    if not item: raise SnapshotError('Preview expired. Close this dialog and prepare again.')
                    if req.get('confirmPublic') is not True: raise SnapshotError('Explicit public confirmation is required.')
                    if item.get('busy'): raise SnapshotError('Publication is already running. Wait before retrying.')
                    item['busy']=True; result=None
                else:
                    self.respond(404,{'error':'Unknown action'}); return
            if result is None:
                try: result=item.get('result') or publish(item)
                finally:
                    with LOCK: item['busy']=False
                if result.get('verified'): item['result']=result
            self.respond(200,result)
        except (ValueError,TypeError,KeyError,SnapshotError) as e:
            self.respond(400,{'error':str(e) if isinstance(e,SnapshotError) else 'Invalid request.'})
        except Exception: self.respond(500,{'error':'Could not prepare this brief. Check local assets and try again.'})

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
