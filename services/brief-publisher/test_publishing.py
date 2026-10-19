import base64, json, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
from snapshot import snapshot, SnapshotError, public_href
from receiver import write_snapshot
import server

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        (self.root/'css').mkdir(); (self.root/'css/a.css').write_text('/* okay */ p{color:red}')
        (self.root/'attachments'/'sample').mkdir(parents=True)
        (self.root/'attachments'/'sample'/'a.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII='))
    def tearDown(self): self.tmp.cleanup()
    def doc(self,body):
        (self.root/'sample.html').write_text('<html><head><title>Synthetic</title><link rel="stylesheet" href="css/a.css"></head><body>'+body+'</body></html>')
        return snapshot(self.root,'sample.html')[0].decode()
    def test_self_contained_and_inert(self):
        out=self.doc('<div class="toolbar"><button>Print</button></div><script>secret()</script><p onclick="secret()">Synthetic only</p><img src="attachments/sample/a.png"><a href="https://desk.q7hub.com/private">Private</a>')
        self.assertIn('data:image/png;base64,',out);self.assertIn('color:red',out);self.assertNotIn('secret()',out);self.assertNotIn('desk.q7hub',out);self.assertNotIn('<script',out);self.assertIn("default-src",out)
    def test_paths(self):
        for src in ('../secret.png','attachments/other/a.png','https://example.com/a.png','/etc/passwd'):
            with self.assertRaises(SnapshotError): self.doc('<img src="'+src+'">')
        (self.root/'attachments/sample/link.png').symlink_to(self.root/'attachments/sample/a.png')
        with self.assertRaises(SnapshotError): self.doc('<img src="attachments/sample/link.png">')
    def test_css_network(self):
        for css in ('background:url(https://example.com)','@import "x"','background:u\\72l(x)'):
            with self.assertRaises(SnapshotError): self.doc('<style>p{'+css+'}</style>')
    def test_no_hidden_controls(self):
        out=self.doc('<p>Synthetic</p><input type="hidden" value="SECRET"><form action="https://example.com"><textarea>SECRET</textarea></form><!--SECRET-->')
        self.assertNotIn('SECRET',out);self.assertNotIn('<form',out)
    def test_links(self):
        for v in ('javascript:alert(1)','file:///secret','https://127.0.0.1/','https://localhost/','https://db.q7hub.com/','https://x.com/?token=abc'):
            self.assertIsNone(public_href(v))
        self.assertEqual(public_href('https://example.com'),'https://example.com')
    def test_atomic_collision_and_idempotency(self):
        a=b'<!doctype html><p>synthetic</p>'; b=b'<!doctype html><p>different</p>'
        write_snapshot(self.root,'AbC1234',a);write_snapshot(self.root,'AbC1234',a)
        with self.assertRaises(FileExistsError):write_snapshot(self.root,'AbC1234',b)
        with self.assertRaises(ValueError):write_snapshot(self.root,'../evil',a)
        self.assertEqual((self.root/'AbC1234.html').read_bytes(),a)
    def test_implicit_body(self):
        (self.root/'sample.html').write_text('<!doctype html><html><title>Synthetic</title><p>Valid omitted body tags</p></html>')
        out=snapshot(self.root,'sample.html')[0].decode();self.assertIn('Valid omitted body tags',out);self.assertEqual(out.count('<html>'),1)
    def test_source_remains_unchanged(self):
        self.doc('<p>Private source</p>');before=(self.root/'sample.html').read_bytes();snapshot(self.root,'sample.html');self.assertEqual((self.root/'sample.html').read_bytes(),before)
    def test_http_guards_and_explicit_confirmation(self):
        self.doc('<p>Synthetic API test</p>')
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        def post(action,body,origin=server.ORIGIN):
            req=urllib.request.Request('http://127.0.0.1:'+str(http.server_port)+'/api/brief-publish/'+action,data=json.dumps(body).encode(),headers={'Host':'localhost:8766','Origin':origin,'X-Brief-Publish':'1','Content-Type':'application/json'})
            return json.load(urllib.request.urlopen(req))
        try:
            with patch.object(server,'ROOT',self.root),patch.object(server,'publish',return_value={'verified':True,'url':'https://q7x.ai/pub/AbC1234.html'}) as pub:
                with self.assertRaises(urllib.error.HTTPError):post('prepare',{'name':'sample.html'},'https://evil.example')
                prep=post('prepare',{'name':'sample.html'});pub.assert_not_called()
                with self.assertRaises(urllib.error.HTTPError):post('confirm',{'token':prep['token']})
                post('confirm',{'token':prep['token'],'confirmPublic':True});post('confirm',{'token':prep['token'],'confirmPublic':True});self.assertEqual(pub.call_count,1)
        finally:http.shutdown();http.server_close()

if __name__=='__main__':unittest.main()
