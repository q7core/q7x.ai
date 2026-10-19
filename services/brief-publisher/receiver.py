"""Oracle receiver: one bounded immutable HTML file; invoked via existing SSH."""
import hashlib, os, re, sys, tempfile
from pathlib import Path
ROOT=Path('/var/www/steeltrap/.q7x-public')
LIMIT=16*1024*1024

def write_snapshot(root,code,data):
    if not re.fullmatch('[A-Za-z0-9]{7}',code): raise ValueError('Invalid publication code')
    if not data.startswith(b'<!doctype html>') or len(data)>LIMIT: raise ValueError('Invalid snapshot')
    root=Path(root)
    if root.is_symlink() or not root.is_dir(): raise ValueError('Unsafe publication directory')
    target=root/(code+'.html')
    if target.exists() or target.is_symlink():
        if not target.is_symlink() and target.is_file() and target.read_bytes()==data: return
        raise FileExistsError('Publication code collision')
    fd,tmp=tempfile.mkstemp(prefix='.upload-',dir=root)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno()); os.fchmod(f.fileno(),0o644)
        os.link(tmp,target) # exclusive atomic publication; never overwrite
    finally: os.unlink(tmp)

if __name__=='__main__':
    try:
        data=sys.stdin.buffer.read(LIMIT+1)
        write_snapshot(ROOT,sys.argv[1],data)
        print(hashlib.sha256(data).hexdigest())
    except FileExistsError: sys.exit(73)
