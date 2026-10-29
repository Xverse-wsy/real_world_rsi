import base64, hashlib, shutil, tomllib
from importlib.metadata import distributions
from pathlib import Path
source=Path('/home/wenchaoxu/miniconda3/envs/nanojev/lib/python3.12/site-packages')
target=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.venv-libero/lib/python3.12/site-packages')
lock=tomllib.load(open('uv.lock','rb'))
wanted={p['name']:p['version'] for p in lock['package'] if 'version' in p}
for d in distributions(path=[str(source)]):
    name=d.metadata['Name'].lower().replace('_','-')
    if name!='torch' and not name.startswith('nvidia-'): continue
    if wanted.get(name)!=d.version: continue
    files=[]; valid=True
    for f in d.files or []:
        src=Path(d.locate_file(f))
        if not src.is_relative_to(source) or '..' in f.parts: continue
        if not src.is_file(): valid=False; break
        if f.hash:
            h=hashlib.new(f.hash.mode)
            with src.open('rb') as handle:
                for chunk in iter(lambda:handle.read(8*1024*1024),b''): h.update(chunk)
            if base64.urlsafe_b64encode(h.digest()).decode().rstrip('=')!=f.hash.value:
                print('HASH_MISMATCH', name, f, flush=True); valid=False; break
        files.append((src,target/str(f)))
    if not valid:
        print('SKIP',name,d.version,flush=True);continue
    for src,dst in files:
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    print('REUSED',name,d.version,len(files),flush=True)
