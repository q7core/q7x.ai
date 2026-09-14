import { test } from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createApi } from '../api.mjs';
import { createPool } from '../store.mjs';

const token = 'test-token-with-at-least-thirty-two-characters';
test('malformed database URLs never include credentials in errors', () => {
  const secret='example-private-password';
  assert.throws(() => createPool({DATABASE_URL:`postgres://user:${secret}@[invalid]/database`}), error => {
    assert.equal(error.input,undefined);
    assert.equal(error.cause,undefined);
    assert.equal(String(error).includes(secret),false);
    return true;
  });
});
test('database URL options cannot disable certificate verification', () => {
  for (const query of ['ssl=0','ssl=no-verify','sslmode=disable','sslmode=no-verify','sslrootcert=other','uselibpqcompat=true']) {
    assert.throws(() => createPool({DATABASE_URL:`postgresql://example:example@localhost/postgres?${query}`}), /must not include query parameters/);
  }
});
async function fixture(t, store = { list: async () => [], post: async body => ({ ...body, id: '1' }) }) {
  const server = createApi({ token, store });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  return async (path = '', options = {}) => fetch(`http://127.0.0.1:${server.address().port}/api/messages${path}`, {
    ...options, headers: { Authorization: `Bearer ${token}`, ...options.headers },
  });
}

test('both reads and writes require bearer authentication', async t => {
  const request = await fixture(t);
  for (const method of ['GET', 'POST']) {
    const response = await request('', { method, headers: { Authorization: 'Bearer wrong' } });
    assert.equal(response.status, 401);
    assert.equal(response.headers.get('cache-control'), 'no-store');
  }
});

test('query validation rejects ambiguous, unbounded and invalid cursors', async t => {
  const request = await fixture(t);
  for (const query of ['?limit=0', '?limit=101', '?limit=1.5', '?limit=2&limit=3', '?after=-1', '?after=01', '?after=9223372036854775808', '?after=1&before=2', '?channel=', '?unknown=1']) {
    assert.equal((await request(query)).status, 400, query);
  }
});

test('forward pagination returns the last delivered ID, never the lookahead ID', async t => {
  let args;
  const request = await fixture(t, { list: async x => { args = x; return [{id:'11'}, {id:'12'}, {id:'13'}]; } });
  const response = await request('?channel=general&after=10&limit=2');
  assert.equal(response.status, 200);
  const page = await response.json();
  assert.deepEqual(page.messages.map(x => x.id), ['11', '12']);
  assert.equal(page.next_after, '12');
  assert.equal(page.has_more, true);
  assert.equal(args.direction, 'forward');
  assert.equal(args.limit, 3);
});

test('latest pages are chronological and expose older-history bookmark', async t => {
  const request = await fixture(t, { list: async () => [{id:'13'}, {id:'12'}, {id:'11'}] });
  const page = await (await request('?limit=2')).json();
  assert.deepEqual(page.messages.map(x => x.id), ['12', '13']);
  assert.equal(page.next_after, '13');
  assert.equal(page.next_before, '12');
  assert.equal(page.has_more, true);
});

test('empty forward poll preserves bookmark', async t => {
  const request = await fixture(t);
  assert.equal((await (await request('?after=42')).json()).next_after, '42');
});

test('workspace serves only allowed public assets and keeps message reads protected',async t=>{
  const request=await fixture(t);
  const originRequest=async(path,method='GET')=>{
    const response=await request('',{headers:{Authorization:''}});
    const origin=new URL(response.url).origin;
    return fetch(origin+path,{method,redirect:'manual'});
  };
  assert.equal((await originRequest('/discussions')).status,308);
  const page=await originRequest('/discussions/');
  assert.equal(page.status,200);
  assert.ok(page.headers.get('content-security-policy').includes("script-src 'self'"));
  assert.ok((await page.text()).includes('Draft workspace'));
  assert.equal((await originRequest('/discussions/app.mjs')).status,200);
  assert.equal((await originRequest('/discussions/.env')).status,404);
  assert.equal((await originRequest('/discussions/index.html','POST')).status,405);
  assert.equal((await request('',{headers:{Authorization:''}})).status,401);
});

test('POST validates fields, defaults channel and passes retry key', async t => {
  let saved;
  const request = await fixture(t, { post: async x => { saved=x; return {...x,id:'1'}; } });
  const response = await request('', { method:'POST', headers:{'Content-Type':'application/json','Idempotency-Key':'retry-1'}, body:JSON.stringify({sender:'codex',text:'hello'}) });
  assert.equal(response.status, 200);
  assert.deepEqual(saved, {sender:'codex',channel:'general',text:'hello',idempotency_key:'retry-1'});
  for (const body of [null, [], {}, {sender:' ',text:'ok'}, {sender:'x',text:' '}, {sender:'x',text:'ok',extra:1}, {sender:'x',text:'x'.repeat(16385)}, {sender:'x',text:'bad\u0000'}]) {
    assert.equal((await request('', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).status,400);
  }
});

test('oversized body, wrong content type and unknown routes are bounded', async t => {
  const request = await fixture(t);
  assert.equal((await request('', {method:'POST',body:'x'})).status,415);
  assert.equal((await request('', {method:'POST',headers:{'Content-Type':'application/json'},body:'x'.repeat(65537)})).status,413);
  assert.equal((await request('/missing')).status,404);
  assert.equal((await request('',{method:'DELETE'})).status,405);
});

test('database conflicts and failures do not expose internal details', async t => {
  let code = '23505';
  const request = await fixture(t, {post:async()=>{throw Object.assign(new Error('secret database details'),{code});}});
  const options={method:'POST',headers:{'Content-Type':'application/json'},body:'{"sender":"x","text":"ok"}'};
  assert.equal((await request('',options)).status,409);
  code='08006';
  const response=await request('',options);
  assert.equal(response.status,503);
  assert.equal((await response.text()).includes('secret'),false);
});
