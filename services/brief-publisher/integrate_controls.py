"""Attach UI only. Never calls the publisher or changes any brief content."""
from pathlib import Path
import datetime, shutil
ROOT=Path('/Users/rproemer/q7core/Workbench/Briefs')
SOURCE=Path(__file__).resolve().parent
backup=Path('/Users/rproemer/q7core-Backups')/(datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')+' - Brief publishing controls')
backup.mkdir()
shared=ROOT/'js/brief-v1.js';shutil.copy2(shared,backup/'brief-v1.js')
loader='\n/* Public copies require explicit confirmation in the private publishing dialog. */\n{ const s=document.createElement("script"); s.src="/Workbench/Briefs/js/brief-publish.js"; document.head.append(s); }\n'
if 'brief-publish.js' not in shared.read_text():shared.write_text(shared.read_text()+loader)
shutil.copy2(SOURCE/'brief-publish.js',ROOT/'js/brief-publish.js')
changed=[]
for path in ROOT.glob('*.html'):
 if path.name=='index.html':continue
 text=path.read_text()
 if 'brief-v1.js' in text or 'brief-publish.js' in text:continue
 # Preserve original markup byte-for-byte apart from the extra script include.
 marker='<script src="/Workbench/Briefs/js/brief-publish.js"></script>'
 if '</body>' not in text.lower() and '</html>' not in text.lower():
  # Redirect-only documents have no user-visible page controls.
  changed.append(path.name+': redirect/incomplete; retained unchanged');continue
 import re
 end='</body>' if '</body>' in text.lower() else '</html>'
 updated=re.sub(end,marker+end,text,count=1,flags=re.I)
 shutil.copy2(path,backup/path.name);path.write_text(updated);changed.append(path.name)
print('Control integration:',changed,'Backup:',backup)
