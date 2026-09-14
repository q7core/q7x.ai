import {readFileSync} from 'node:fs';
// Public allowlist only: never resolve a request path against the filesystem.
const names={'index.html':'text/html','styles.css':'text/css','tokens.css':'text/css','app.mjs':'text/javascript','clients.mjs':'text/javascript','draft.mjs':'text/javascript','config.mjs':'text/javascript','favicon.svg':'image/svg+xml'};
const files=new Map(Object.entries(names).map(([name,type])=>[name,{type,body:readFileSync(new URL('./public/discussions/'+name,import.meta.url))}]));
export function serveWorkspace(req,res){
  const path=new URL(req.url,'http://localhost').pathname;
  if(path!=='/discussions' && !path.startsWith('/discussions/')) return false;
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{Allow:'GET, HEAD'});res.end();return true;}
  if(path==='/discussions'){res.writeHead(308,{Location:'/discussions/'});res.end();return true;}
  const file=files.get(path==='/discussions/'?'index.html':path.slice('/discussions/'.length));
  if(!file){res.writeHead(404,{'Content-Type':'text/plain'});res.end('Not found');return true;}
  res.writeHead(200,{'Content-Type':file.type+'; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"});
  res.end(req.method==='HEAD'?undefined:file.body);return true;
}
