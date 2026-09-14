import {clientDefinitions,getClientStatus} from './clients.mjs';
import {normalizeDraft,prepareDraft,draftsMatch} from './draft.mjs';
import {config} from './config.mjs';

const $=id=>document.getElementById(id);
const storageKey='q7x.discussion-draft.v1';
let prepared=null;
let storageAvailable=true;
let initial=normalizeDraft(null);
try {
  const raw=localStorage.getItem(storageKey);
  const saved=raw && raw.length<40000?JSON.parse(raw):null;
  initial=normalizeDraft(saved);
  if(saved?.prepared) { prepareDraft(saved.prepared); prepared=normalizeDraft(saved.prepared); }
} catch { storageAvailable=false; }

const list=$('participant-list');
for(const client of clientDefinitions){
  const status=getClientStatus(client.id);
  const label=document.createElement('label'); label.className='participant';
  const input=document.createElement('input'); input.type='checkbox';input.name='participant';input.value=client.id;
  input.checked=initial.participantIds.includes(client.id); input.setAttribute('aria-label',client.name);
  label.append(input);
  for(const [className,text] of [['client-symbol',client.mark],['client-name',client.name],['client-description',client.description],['client-status',status.label]]){
    const span=document.createElement('span');span.className=className;span.textContent=text;
    if(className==='client-symbol') span.setAttribute('aria-hidden','true');
    label.append(span);
  }
  list.append(label);
}
$('topic').value=initial.topic;$('perspective').value=initial.perspective;
$('api-link').href=config.messageApiBase.replace(/\/$/,'')+'/docs';
const read=()=>({topic:$('topic').value,perspective:$('perspective').value,participantIds:[...list.querySelectorAll('input:checked')].map(input=>input.value)});
function updateSelection(){
  const current=read(), count=current.participantIds.length;
  const stale=prepared && !draftsMatch(current,prepared);
  $('selection-count').textContent=`${count} selected`;
  $('select-all').disabled=count===clientDefinitions.length;
  $('draft-change-note').hidden=!stale;
  $('copy-note').disabled=!prepared || !!stale;
  $('conversation-status').textContent=!prepared?'Not started':stale?'Edits not prepared':'Draft · Not sent';
}
function save(){
  try {localStorage.setItem(storageKey,JSON.stringify({...read(),prepared}));storageAvailable=true;}
  catch {storageAvailable=false;}
  $('storage-status').textContent=storageAvailable?'Saved in this browser · Not shared with agents.':'Browser storage is unavailable. Your draft lasts while this page stays open.';
}
function showPrepared(){
  if(!prepared) return;
  const draft=prepareDraft(prepared);
  $('preview-text').textContent=draft.message.text;
  $('preview-participants').textContent=draft.participantIds.map(id=>clientDefinitions.find(c=>c.id===id).name).join(' · ');
  $('empty-conversation').hidden=true;$('draft-preview').hidden=false;
  $('conversation-status').textContent='Draft · Not sent';
  $('prepare-button').firstChild.textContent='Update draft ';
  updateSelection();
}
function clearError(){
  $('form-error').hidden=true;$('form-error').textContent='';
  for(const element of [$('topic'),$('perspective'),$('participant-fieldset')]) element.removeAttribute('aria-invalid');
}
function changed(){updateSelection();clearError();$('copy-status').textContent='';save();}
list.addEventListener('change',changed);
$('select-all').addEventListener('click',()=>{
  for(const input of list.querySelectorAll('input')) input.checked=true;
  changed();
});
$('topic').addEventListener('input',changed);$('perspective').addEventListener('input',changed);
$('draft-form').addEventListener('keydown',event=>{
  if(event.key==='Enter' && (event.metaKey || event.ctrlKey) && !event.isComposing){
    event.preventDefault();$('draft-form').requestSubmit();
  }
});
$('draft-form').addEventListener('submit',event=>{
  event.preventDefault();
  try{
    const current=read();prepareDraft(current);prepared=current;
    clearError();$('copy-status').textContent='';showPrepared();save();
    $('conversation-title').setAttribute('tabindex','-1');$('conversation-title').focus({preventScroll:true});
    if(matchMedia('(max-width:760px)').matches) $('conversation-title').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth',block:'start'});
  }catch(error){
    const current=read();
    const target=!current.topic.trim()?$('topic'):!current.participantIds.length?$('participant-fieldset'):current.topic.includes('\0')?$('topic'):$('perspective');
    target.setAttribute('aria-invalid','true');
    $('form-error').textContent=error.message;$('form-error').hidden=false;
    (target===$('participant-fieldset')?list.querySelector('input'):target).focus();
  }
});
$('copy-note').addEventListener('click',async()=>{
  if(!prepared || !draftsMatch(read(),prepared)) return;
  const text=prepareDraft(prepared).message.text;
  try{
    await navigator.clipboard.writeText(text);
    $('copy-status').textContent='Prepared note copied. Nothing was sent to agents.';
  }catch{
    const range=document.createRange();range.selectNodeContents($('preview-text'));
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    $('copy-status').textContent='Automatic copy is unavailable. The note is selected; use your browser’s Copy command.';
  }
});
updateSelection();showPrepared();
if(!storageAvailable) $('storage-status').textContent='Browser storage is unavailable. Your draft lasts while this page stays open.';
else if(initial.topic || initial.perspective || initial.participantIds.length) $('storage-status').textContent='Restored from this browser · Not shared with agents.';
