import {clientDefinitions} from './clients.mjs';
import {config} from './config.mjs';
const known=new Set(clientDefinitions.map(client=>client.id));
export function normalizeDraft(value) {
  const data=value && typeof value==='object' ? value : {};
  return {
    topic:typeof data.topic==='string'?data.topic.slice(0,1600):'',
    perspective:typeof data.perspective==='string'?data.perspective.slice(0,2000):'',
    participantIds:Array.isArray(data.participantIds)?[...new Set(data.participantIds.filter(id=>known.has(id)))]:[],
  };
}
export function prepareDraft(value) {
  if ((value?.topic?.length??0)>1600 || (value?.perspective?.length??0)>2000) throw new Error('Your draft is too long. Please shorten it.');
  const draft=normalizeDraft(value);
  if(!draft.topic.trim()) throw new Error('Add a question before preparing your draft.');
  if(!draft.participantIds.length) throw new Error('Choose at least one participant.');
  const text=draft.topic.trim()+(draft.perspective.trim()?'\n\nMy perspective:\n'+draft.perspective.trim():'');
  if(text.includes('\0') || new TextEncoder().encode(text).length>16384) throw new Error('Your draft contains unsupported text or is too long.');
  return {participantIds:draft.participantIds,message:{sender:config.sender,channel:config.channel,text}};
}
export function draftsMatch(current,prepared) {
  if(!prepared) return false;
  const a=normalizeDraft(current), b=normalizeDraft(prepared);
  return a.topic===b.topic && a.perspective===b.perspective &&
    a.participantIds.length===b.participantIds.length && a.participantIds.every(id=>b.participantIds.includes(id));
}
