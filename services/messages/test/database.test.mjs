// Uses the dedicated API role. Adds durable records in a unique verification channel.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { createPool, createStore } from '../store.mjs';

const pool = createPool();
const store = createStore(pool);
const channel = `verification-${randomUUID()}`;
const message = (text, key = null) => ({sender:'api-test',channel,text,idempotency_key:key});
after(() => pool.end());

test('deduplicates simultaneous retries and rejects conflicting reuse', async () => {
  const rows = await Promise.all(Array.from({length:5}, () => store.post(message('retry-safe','same-key'))));
  assert.equal(new Set(rows.map(x=>x.id)).size,1);
  await assert.rejects(store.post(message('changed','same-key')), {code:'23505'});
});

test('concurrent messages page numerically without gaps or duplicates', async () => {
  const written=await Promise.all(Array.from({length:15},(_,i)=>store.post(message(`concurrent ${i}`))));
  const seen=[];
  let cursor='0';
  for (;;) {
    const page=await store.list({channel,direction:'forward',cursor,limit:3});
    if (!page.length) break;
    seen.push(...page.map(x=>x.id)); cursor=page.at(-1).id;
  }
  assert.equal(seen.length,16);
  assert.equal(new Set(seen).size,seen.length);
  assert.ok(written.every(x=>seen.includes(x.id)));
  for (let i=1;i<seen.length;i++) assert.ok(BigInt(seen[i])>BigInt(seen[i-1]));
});

test('a delayed commit cannot be overtaken by a later message', async () => {
  const first=await pool.connect();
  let second;
  try {
    await first.query('BEGIN');
    const {rows:[pending]}=await first.query('SELECT id::text FROM ai_chat.append_message($1,$2,$3,$4)', ['api-test',channel,'delayed commit',null]);
    let finished=false;
    second=store.post(message('must follow commit')).then(row=>{finished=true;return row;});
    await delay(200);
    assert.equal(finished,false,'later writer must wait for transaction commit');
    const visible=await store.list({channel,direction:'forward',cursor:pending.id,limit:100});
    assert.equal(visible.length,0,'no higher bookmark may become visible yet');
    await first.query('COMMIT');
    const following=await second;
    assert.ok(BigInt(following.id)>BigInt(pending.id));
    const page=await store.list({channel,direction:'forward',cursor:(BigInt(pending.id)-1n).toString(),limit:100});
    assert.deepEqual(page.map(x=>x.id),[pending.id,following.id]);
  } finally { await first.query('ROLLBACK'); first.release(); if(second) await second; }
});

test('API role cannot bypass ordering, change messages or access counter', async () => {
  for (const sql of [
    "INSERT INTO ai_chat.messages(id,sender,text) VALUES(999999999,'bad','bad')",
    'UPDATE ai_chat.messages SET text=text WHERE false',
    'DELETE FROM ai_chat.messages WHERE false',
    'SELECT * FROM ai_chat.message_counter',
    'SELECT * FROM sp_production.property LIMIT 0',
  ]) await assert.rejects(pool.query(sql), {code:'42501'});
  const {rows:[privileges]}=await pool.query("SELECT has_schema_privilege(current_user,'sp_production','USAGE') AS business_access, current_user");
  assert.equal(privileges.business_access,false);
  assert.equal(privileges.current_user,'ai_chat_api');
});
