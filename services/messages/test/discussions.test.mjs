import {test} from 'node:test';
import assert from 'node:assert/strict';
import {prepareDraft, normalizeDraft} from '../public/discussions/draft.mjs';
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
