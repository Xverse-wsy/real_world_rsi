import concurrent.futures, hashlib, json, os, threading, time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
meta=json.loads((ROOT/".setup/molmo_hf_metadata.json").read_text())
dest=ROOT/".cache/models/molmo2-8b"
rev=meta["sha"]
block=16*1024*1024
files=[f for f in meta["siblings"] if f["rfilename"].endswith(".safetensors")]
lock=threading.Lock(); local=threading.local(); tasks=[]; state={}; descriptors={}
for f in files:
    name=f["rfilename"]; total=f["size"]; target=dest/name; part=dest/(name+".part"); marker=dest/(name+".ranges.json")
    if target.exists() and target.stat().st_size==total:
        print("EXISTING",name,flush=True); continue
    if marker.exists(): done=set(json.loads(marker.read_text()))
    else:
        length=part.stat().st_size if part.exists() else 0
        done=set(range(length//block))
        marker.write_text(json.dumps(sorted(done)))
    fd=os.open(part,os.O_CREAT|os.O_RDWR,0o644)
    os.ftruncate(fd,total)
    descriptors[name]=fd
    state[name]={"done":done,"marker":marker,"total":(total+block-1)//block,"file":f}
    for idx in range((total+block-1)//block):
        if idx not in done: tasks.append((name,idx,idx*block,min((idx+1)*block,total)-1))
completed=0
print("RANGE TASKS",len(tasks),"workers",8,flush=True)
def fetch(task):
    global completed
    name,idx,start,end=task
    if not hasattr(local,"session"): local.session=requests.Session()
    url=f"https://hf-mirror.com/allenai/Molmo2-8B/resolve/{rev}/{name}"
    for attempt in range(12):
        try:
            with local.session.get(url,headers={"Range":f"bytes={start}-{end}"},params={"download":"true","capx_block":idx,"capx_attempt":attempt},timeout=(30,90)) as r:
                if r.status_code!=206 or r.headers.get("Content-Range","")!=f"bytes {start}-{end}/{state[name]['file']['size']}":
                    raise RuntimeError("Range HTTP "+str(r.status_code))
                data=r.content
            if len(data)!=end-start+1: raise RuntimeError("Truncated block")
            offset=0
            while offset<len(data): offset+=os.pwrite(descriptors[name],data[offset:],start+offset)
            with lock:
                item=state[name]; item["done"].add(idx)
                tmp=item["marker"].with_suffix(".tmp")
                tmp.write_text(json.dumps(sorted(item["done"]))); tmp.replace(item["marker"])
                completed+=1
                if completed%32==0: print("COMPLETED BLOCKS",completed,"/",len(tasks),flush=True)
            return
        except Exception as exc:
            if attempt in [0,5,11]: print("RETRY BLOCK",name,idx,attempt+1,type(exc).__name__,flush=True)
            time.sleep(min(attempt+1,10))
    raise RuntimeError("Block failed "+name+" "+str(idx))
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(fetch,tasks))
finally:
    for fd in descriptors.values(): os.fsync(fd); os.close(fd)
for f in files:
    name=f["rfilename"]; target=dest/name; part=dest/(name+".part"); path=part if part.exists() else target
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda:stream.read(16*1024*1024),b""): h.update(b)
    if h.hexdigest()!=f["lfs"]["sha256"]: raise RuntimeError("SHA256 mismatch "+name)
    if path!=target: part.replace(target)
    print("VERIFIED",name,f["size"],flush=True)
# Fetch any remaining tokenizer/configuration files.
for f in meta["siblings"]:
    name=f["rfilename"]
    if name.endswith(".safetensors") or name in [".gitattributes","molmo_2_logo_RGB.png"]: continue
    target=dest/name
    if target.exists() and target.stat().st_size==f.get("size"): continue
    r=requests.get(f"https://hf-mirror.com/allenai/Molmo2-8B/resolve/{rev}/{name}",timeout=60); r.raise_for_status()
    target.write_bytes(r.content)
    assert target.stat().st_size==f["size"]
(ROOT/".setup/molmo_download.json").write_text(json.dumps({"repo_id":"allenai/Molmo2-8B","revision":rev,"endpoint":"https://hf-mirror.com","path":str(dest),"files":meta["siblings"]},indent=2))
(ROOT/".setup/molmo_download.exit").write_text("0\n")
print("ALL FILES DOWNLOADED AND SHA256 VERIFIED",flush=True)
