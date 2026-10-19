/* Shared private Briefs publishing UI. No publication occurs on page load. */
(() => {
  if (window.q7BriefPublisherLoaded) return;
  window.q7BriefPublisherLoaded = true;
  if (!/^\/Workbench\/Briefs\/[^/]+\.html$/.test(location.pathname) || location.pathname.endsWith('/index.html')) return;
  const style = document.createElement('style');
  style.textContent = '[data-publish]{margin-left:8px;padding:10px 22px;cursor:pointer}.q7-publish-dialog{width:min(960px,95vw);max-height:94vh;border:1px solid #147b79;border-radius:8px;padding:22px;color:#203240;background:white;font:16px/1.5 Arial}.q7-publish-dialog::backdrop{background:#0009}.q7-publish-dialog iframe{width:100%;height:45vh;border:1px solid #ccd8dd}.q7-publish-dialog button{margin:10px 8px 0 0;padding:10px 16px}.q7-publish-dialog input[type=url]{width:100%;padding:10px;box-sizing:border-box}.q7-publish-dialog [role=status]{white-space:pre-wrap}.q7-publish-warning{background:#fff3d8;padding:12px}.q7-publish-fallback{text-align:center;padding:12px}@media print{[data-publish],.q7-publish-dialog,.q7-publish-fallback{display:none!important}}';
  document.head.append(style);
  const button = document.createElement('button'); button.type='button'; button.dataset.publish=''; button.textContent='Publish';
  const print = document.querySelector('[data-print],button[onclick*="print"]');
  if (print) print.after(button);
  else { const bar=document.createElement('div'); bar.className='q7-publish-fallback'; bar.append(button); document.body.prepend(bar); }
  async function request(action,body) {
    const response=await fetch('/api/brief-publish/'+action,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Brief-Publish':'1'},body:JSON.stringify(body)});
    if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('The publishing helper is unavailable or your sign-in expired. Reload the private brief and try again.');
    const result=await response.json(); if (!response.ok) throw new Error(result.error || 'Publishing failed.'); return result;
  }
  button.addEventListener('click',async () => {
    if (location.origin!=='https://desk.q7hub.com') { alert('Open this brief at https://desk.q7hub.com'+location.pathname+' to publish from your authenticated private session.'); return; }
    button.disabled=true;
    const d=document.createElement('dialog'); d.className='q7-publish-dialog';
    d.innerHTML='<h2>Publish this brief publicly?</h2><p class="q7-publish-warning">Anyone with the link can read and forward this copy without signing in. Review the entire preview for confidential text, images, personal information and credentials. This creates a separate snapshot; later private edits do not update it. Copies downloaded by recipients cannot be recalled.</p><p>Scripts, forms, private links and unsupported interactive graphics are excluded. Only this brief’s referenced supported images and CSS are included.</p><p role="status" aria-live="polite">Preparing preview — nothing has been published.</p><iframe sandbox title="Exact public snapshot preview" hidden></iframe><p><label><input type="checkbox"> I reviewed the complete preview and approve its contents for public access.</label></p><button type="button" data-confirm disabled>Publish publicly</button><button type="button" data-close>Cancel</button><div data-result hidden><label>Public link<input type="url" readonly></label><button type="button" data-copy>Copy link</button></div>';
    document.body.append(d); d.showModal();
    let token; const status=d.querySelector('[role=status]'), confirm=d.querySelector('[data-confirm]'), check=d.querySelector('input[type=checkbox]'), close=d.querySelector('[data-close]');
    close.onclick=()=>d.close(); d.addEventListener('close',()=>{d.remove();button.disabled=false;});
    check.onchange=()=>{confirm.disabled=!token || !check.checked;};
    try { const p=await request('prepare',{name:decodeURIComponent(location.pathname.split('/').pop())}); token=p.token; const frame=d.querySelector('iframe'); frame.srcdoc=p.html; frame.hidden=false; status.textContent='Preview ready. '+p.assets.length+' referenced asset(s) embedded. Nothing has been published.'; }
    catch(e) { status.textContent=e.message; }
    confirm.onclick=async()=>{
      confirm.disabled=true; close.disabled=true; check.disabled=true; status.textContent='Publishing and checking the public URL…';
      const preventCancel=e=>e.preventDefault(); d.addEventListener('cancel',preventCancel);
      try {
        const p=await request('confirm',{token,confirmPublic:true});
        if(p.url){d.querySelector('[data-result]').hidden=false;d.querySelector('input[type=url]').value=p.url;}
        if(p.verified){status.textContent='Published. The public page was fetched without authentication and matched this preview exactly.';confirm.hidden=true;close.textContent='Close';}
        else {status.textContent=p.error;confirm.disabled=false;confirm.textContent='Retry / verify publication';}
      } catch(e) {status.textContent=e.message+' Publication may have completed. Retry this same preview to verify.';confirm.disabled=false;confirm.textContent='Retry / verify publication';}
      finally {close.disabled=false;d.removeEventListener('cancel',preventCancel);}
    };
    d.querySelector('[data-copy]').onclick=async()=>{const input=d.querySelector('input[type=url]');try{await navigator.clipboard.writeText(input.value);status.textContent+=' Link copied.';}catch{input.focus();input.select();status.textContent+=' Copy the selected link manually.';}};
  });
})();
