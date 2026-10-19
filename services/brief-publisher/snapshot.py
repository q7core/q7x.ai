"""Fail-closed static Brief snapshot. No script execution or network fetches."""
import base64, html, ipaddress, re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_BYTES = 16 * 1024 * 1024
CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-src 'none'"
TAGS = set('html head body title style main section article header footer nav aside div span p h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table thead tbody tfoot tr td th caption colgroup col figure figcaption a img br hr strong b em i u s del ins small sub sup code pre blockquote details summary label'.split())
VOID = {'img','br','hr','col'}
DROP = {'script','iframe','object','embed','template','noscript','textarea','select','button','svg','math'}
ATTRS = {'class','id','title','lang','dir','colspan','rowspan','scope','width','height','alt','role','open','start'}

class SnapshotError(ValueError): pass

def css_safe(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # Escapes can conceal URL/import tokens. Refuse rather than guess.
    if re.search(r'\\|/\*|url\s*\(|@import|expression\s*\(|</style|behavior\s*:|-moz-binding', css, re.I):
        raise SnapshotError('A stylesheet uses unsupported external or dynamic content. Remove it before publishing.')
    return css

def public_href(value):
    u = urlsplit(value)
    if value.startswith('#'): return value
    if u.scheme not in ('https','http') or not u.hostname or u.username or u.password: return None
    host = u.hostname.lower().rstrip('.')
    if host in ('localhost','q7hub') or host.endswith(('.q7hub.com','.local','.internal','.localhost','.ts.net')): return None
    try:
        if not ipaddress.ip_address(host).is_global: return None
    except ValueError: pass
    # Credential-bearing URLs must never leave the private page.
    if re.search(r'(token|secret|password|signature|api.?key|credential|authorization)=',u.query,re.I): return None
    return value

class Snapshot(HTMLParser):
    def __init__(self,root,name):
        super().__init__(convert_charrefs=True)
        self.root=Path(root).resolve(); self.name=name; self.stem=Path(name).stem
        self.out=[]; self.drop=0; self.style=False; self.assets=[]
    def asset(self,value,kind):
        u=urlsplit(value)
        if u.scheme or u.netloc or u.query or u.fragment: raise SnapshotError('Assets must be local files belonging to this brief.')
        rel=Path(unquote(u.path))
        if rel.is_absolute() or any(p.startswith('.') or '\\' in p for p in rel.parts): raise SnapshotError('Unsafe asset path.')
        permitted = (kind=='css' and rel.parts[:1]==('css',)) or rel.parts[:2]==('attachments',self.stem)
        if not permitted: raise SnapshotError('An asset is outside this brief’s attachment folder or shared CSS folder.')
        current=self.root
        for part in rel.parts:
            current=current/part
            if current.is_symlink(): raise SnapshotError('Symlink assets cannot be published.')
        if not current.is_file() or current.stat().st_size>MAX_BYTES: raise SnapshotError('Asset is missing or too large.')
        data=current.read_bytes(); self.assets.append(rel.as_posix())
        if kind=='css': return css_safe(data.decode('utf-8'))
        signatures=[(b'\x89PNG\r\n\x1a\n','image/png'),(b'\xff\xd8\xff','image/jpeg'),(b'GIF87a','image/gif'),(b'GIF89a','image/gif')]
        mime=next((m for sig,m in signatures if data.startswith(sig)),None)
        if data[:4]==b'RIFF' and data[8:12]==b'WEBP': mime='image/webp'
        if not mime: raise SnapshotError('Only PNG, JPEG, GIF and WebP images are supported; convert other formats first.')
        return 'data:'+mime+';base64,'+base64.b64encode(data).decode()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if self.drop:
            if tag not in VOID and tag not in ('input','meta','link','embed','source','area','base','wbr'): self.drop+=1
            return
        if tag in DROP or 'hidden' in a or a.get('aria-hidden')=='true' or re.search(r'(display\s*:\s*none|visibility\s*:\s*hidden)',a.get('style',''),re.I) or 'data-publish' in a or 'toolbar' in a.get('class','').split():
            if tag not in VOID and tag not in ('input','meta','link','embed','source','area','base','wbr'): self.drop=1
            return
        if tag in ('html','head','body','meta'): return
        if tag=='link':
            if a.get('rel','').lower()=='stylesheet': self.out.append('<style>'+self.asset(a.get('href',''),'css')+'</style>')
            return
        if tag=='input':
            if a.get('type')=='checkbox': self.out.append('<span class="box" aria-label="checkbox"></span>')
            return
        if tag not in TAGS: return
        kept=[]
        for key,val in attrs:
            if val is None: val=''
            if key in ATTRS or key.startswith('aria-'): kept.append((key,val))
            elif key=='style': kept.append((key,css_safe(val)))
            elif tag=='a' and key=='href':
                href=public_href(val)
                if href: kept.extend([('href',href),('rel','noreferrer noopener')])
            elif tag=='img' and key=='src':
                # Existing inline raster images are parsed and size-checked too.
                if re.fullmatch(r'data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+',val):
                    if len(val)>MAX_BYTES: raise SnapshotError('Inline image too large.')
                    kept.append(('src',val))
                else: kept.append(('src',self.asset(val,'image')))
        self.out.append('<'+tag+''.join(' '+k+'="'+html.escape(v,quote=True)+'"' for k,v in kept)+'>')
        if tag=='style': self.style=True
    def handle_endtag(self,tag):
        if self.drop:
            self.drop-=1; return
        if tag in TAGS and tag not in VOID and tag not in ('html','head','body'): self.out.append('</'+tag+'>')
        if tag=='style': self.style=False
    def handle_data(self,data):
        if not self.drop: self.out.append(css_safe(data) if self.style else html.escape(data))

def snapshot(root,name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.html',name) or name=='index.html': raise SnapshotError('Select an individual brief.')
    path=Path(root)/name
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES: raise SnapshotError('Brief missing, unsafe or too large.')
    source=path.read_text('utf-8')
    if re.search(r'<meta[^>]+http-equiv=[\"\']?refresh', source, re.I) or not re.search(r'<(main|section|article|p|div)\b',source,re.I): raise SnapshotError('This redirect or incomplete document cannot be published. Open the actual brief.')
    p=Snapshot(root,name); p.feed(source); p.close()
    if p.drop: raise SnapshotError('Unbalanced document markup; fix before publishing.')
    head='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="'+html.escape(CSP,quote=True)+'">'
    body=('<!doctype html>\n<html><head>'+head+'</head><body>'+''.join(p.out)+'</body></html>').encode()
    if len(body)>MAX_BYTES: raise SnapshotError('Public snapshot exceeds 16 MiB.')
    return body,sorted(set(p.assets))
