import concurrent.futures, hashlib, json, time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
meta=json.loads((ROOT/".setup/molmo_hf_metadata.json").read_text())
rev=meta["sha"]
dest=ROOT/".cache/models/molmo2-8b"
dest.mkdir(parents=True, exist_ok=True)
def fetch(f):
    name=f["rfilename"]
    if name in [".gitattributes", "molmo_2_logo_RGB.png"]: return
    target=dest/name
    expected=f.get("size")
    lfs=f.get("lfs") or {}
    def verify(path):
        if not path.exists() or (expected is not None and path.stat().st_size!=expected): return False
        if lfs.get("sha256"):
            h=hashlib.sha256()
            with path.open("rb") as stream:
                for b in iter(lambda:stream.read(16*1024*1024), b""): h.update(b)
            return h.hexdigest()==lfs["sha256"]
        return True
    if verify(target):
        print("VERIFIED existing",name,flush=True); return
    part=target.with_name(target.name+".part")
    for attempt in range(8):
        try:
            pos=part.stat().st_size if part.exists() else 0
            if expected is not None and pos==expected and verify(part):
                part.replace(target); print("VERIFIED",name,expected,flush=True); return
            headers={"Range":f"bytes={pos}-"} if pos else {}
            url=f"https://hf-mirror.com/allenai/Molmo2-8B/resolve/{rev}/{name}"
            with requests.get(url, headers=headers, stream=True, timeout=(30,150), params={"download":"true", "capx_retry":str(attempt)},) as r:
                if r.status_code not in [200,206]: raise RuntimeError("HTTP "+str(r.status_code))
                if r.status_code==206:
                    assert r.headers.get("Content-Range","").startswith(f"bytes {pos}-")
                else: pos=0
                last=pos
                with part.open("ab" if pos else "wb") as stream:
                    for chunk in r.iter_content(8*1024*1024):
                        stream.write(chunk); pos+=len(chunk)
                        if pos-last>512*1024*1024:
                            print("PROGRESS",name,pos,"/",expected,flush=True); last=pos
            if not verify(part): raise RuntimeError("Size/hash verification failed")
            part.replace(target)
            print("VERIFIED",name,target.stat().st_size,flush=True)
            return
        except Exception as exc:
            print("RETRY",name,attempt+1,type(exc).__name__,flush=True)
            time.sleep(min(2**attempt,30))
    raise RuntimeError("Download failed: "+name)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(fetch,meta["siblings"]))
(ROOT/".setup/molmo_download.json").write_text(json.dumps({"repo_id":"allenai/Molmo2-8B","revision":rev,"endpoint":"https://hf-mirror.com","path":str(dest),"files":meta["siblings"]},indent=2))
(ROOT/".setup/molmo_download.exit").write_text("0\n")
print("ALL FILES DOWNLOADED AND VERIFIED",flush=True)
