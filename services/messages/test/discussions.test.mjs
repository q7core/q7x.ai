import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {prepareDraft, normalizeDraft, draftsMatch} from '../public/discussions/draft.mjs';
import {clientDefinitions, getClientStatus, receiveMessage} from '../public/discussions/clients.mjs';

test('opening draft uses the existing outgoing message fields without invented IDs',()=>{
  const draft=prepareDraft({topic:'A useful question?',perspective:'My perspective.',participantIds:['codex','hermes']});
  assert.deepEqual(Object.keys(draft.message).sort(),['channel','sender','text']);
  assert.equal(draft.message.sender,'rick');
  assert.equal(draft.message.channel,'general');
  assert.equal(draft.message.text,'A useful question?\n\nMy perspective:\nMy perspective.');
  assert.deepEqual(draft.participantIds,['codex','hermes']);
});
test('draft validation requires a question and participants and respects API text bound',()=>{
  assert.throws(()=>prepareDraft({topic:' ',participantIds:['codex']}),/question/);
  assert.throws(()=>prepareDraft({topic:'Question',participantIds:[]}),/participant/);
  assert.throws(()=>prepareDraft({topic:'x'.repeat(1601),participantIds:['codex']}),/long/);
  const draft=prepareDraft({topic:'語'.repeat(1600),perspective:'語'.repeat(2000),participantIds:['codex']});
  assert.ok(Buffer.byteLength(draft.message.text)<=16384);
});
test('saved browser state is normalized, bounded and limited to known participants',()=>{
  assert.deepEqual(normalizeDraft(null),{topic:'',perspective:'',participantIds:[]});
  assert.deepEqual(normalizeDraft({topic:'test',perspective:42,participantIds:['codex','unknown','codex']}),{topic:'test',perspective:'',participantIds:['codex']});
  assert.equal(normalizeDraft({topic:'x'.repeat(5000)}).topic.length,1600);
});
test('all five clients honestly report unavailable capabilities and cannot deliver',async()=>{
  assert.equal(clientDefinitions.length,5);
  for(const client of clientDefinitions){
    assert.equal(getClientStatus(client.id).state,'not_connected');
    assert.equal(getClientStatus(client.id).capabilities.receiveMessage,false);
    await assert.rejects(receiveMessage(client.id,{id:'1',sender:'rick',channel:'general',text:'hi',created_at:'2026-09-14T00:00:00Z'}),/not connected/);
  }
});
test('prepared notes become stale for text or participant edits, and recover when edits are undone',()=>{
  const prepared={topic:'Question?',perspective:'Context',participantIds:['codex','hermes']};
  assert.equal(draftsMatch(prepared,null),false);
  assert.equal(draftsMatch({...prepared,topic:'Changed?'},prepared),false);
  assert.equal(draftsMatch({...prepared,perspective:''},prepared),false);
  assert.equal(draftsMatch({...prepared,participantIds:[]},prepared),false);
  assert.equal(draftsMatch(JSON.parse(JSON.stringify(prepared)),prepared),true);
});
test('participant order does not mark a restored note stale or mutate saved state',()=>{
  const prepared={topic:'Question?',perspective:'',participantIds:['hermes','codex']};
  assert.equal(draftsMatch({...prepared,participantIds:['codex','hermes']},prepared),true);
  assert.deepEqual(prepared.participantIds,['hermes','codex']);
});
test('every scripted control and accessible description exists in the shipped HTML',()=>{
  const html=readFileSync(new URL('../public/discussions/index.html',import.meta.url),'utf8');
  const app=readFileSync(new URL('../public/discussions/app.mjs',import.meta.url),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
  assert.equal(new Set(ids).size,ids.length,'HTML IDs must be unique');
  for(const [,id] of app.matchAll(/\$\('([^']+)'\)/g)) assert.ok(ids.includes(id),`Missing scripted control: ${id}`);
  for(const [,references] of html.matchAll(/aria-(?:describedby|labelledby)="([^"]+)"/g)){
    for(const id of references.split(/\s+/)) assert.ok(ids.includes(id),`Missing accessible description: ${id}`);
  }
});
