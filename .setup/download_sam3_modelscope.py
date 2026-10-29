import requests,hashlib,json,subprocess,os
from pathlib import Path
root=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
repo=root/'.cache/huggingface/hub/models--facebook--sam3'
blobs=repo/'blobs'; blobs.mkdir(parents=True,exist_ok=True)
endpoint='https://modelscope.cn/api/v1/models/facebook/sam3'
r=requests.get(endpoint+'/repo/files',params={'Revision':'master','Recursive':'true'},timeout=30)
r.raise_for_status()
files={f['Path']:f for f in r.json()['Data']['Files']}
weight=files['sam3.pt']; config=files['config.json']
expected='9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e'
assert weight['Sha256']==expected
revision=weight['Revision']
print('Source: ModelScope facebook/sam3; revision:',revision,flush=True)
print('Weight bytes:',weight['Size'],'Target:',blobs/expected,flush=True)
config_response=requests.get(endpoint+'/repo',params={'Revision':config['Revision'],'FilePath':'config.json'},timeout=30)
config_response.raise_for_status(); content=config_response.content; json.loads(content)
assert len(content)==config['Size']
assert hashlib.sha256(content).hexdigest()==config['Sha256']
git_hash=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
assert git_hash=='3e600e765b0f1b4c52680aed9ad242c9a90f7ed1'
(blobs/git_hash).write_bytes(content)
url=endpoint+'/repo?Revision='+revision+'&FilePath=sam3.pt'
subprocess.run(['aria2c','--continue=true','--file-allocation=none','--max-connection-per-server=8','--split=8','--min-split-size=32M','--max-tries=5','--retry-wait=5','--connect-timeout=20','--timeout=120','--console-log-level=warn','--summary-interval=30','--checksum=sha-256='+expected,'--dir='+str(blobs),'--out='+expected,url],check=True)
path=blobs/expected
assert path.stat().st_size==weight['Size']
h=hashlib.sha256()
with path.open('rb') as handle:
 for block in iter(lambda:handle.read(16*1024*1024),b''):h.update(block)
assert h.hexdigest()==expected
hf_revision='3c879f39826c281e95690f02c7821c4de09afae7'
snapshot=repo/'snapshots'/hf_revision;snapshot.mkdir(parents=True,exist_ok=True)
for name,blob in [('sam3.pt',expected),('config.json',git_hash)]:
 link=snapshot/name
 if not link.exists():link.symlink_to('../../blobs/'+blob)
(repo/'refs').mkdir(exist_ok=True)
(repo/'refs/main').write_text(hf_revision)
stable=root/'.cache/models/sam3';stable.mkdir(parents=True,exist_ok=True)
for name in ['sam3.pt','config.json']:
 link=stable/name
 if not link.exists():link.symlink_to(snapshot/name)
manifest={'source':'ModelScope facebook/sam3','source_revision':revision,'hf_equivalent_revision':hf_revision,'sha256':expected,'bytes':path.stat().st_size,'checkpoint_path':str(stable/'sam3.pt'),'hf_cache_snapshot':str(snapshot)}
(root/'.setup/sam3_download.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('SHA256 verified:',expected,flush=True)
print('Checkpoint:',stable/'sam3.pt',flush=True)
print('SAM3_DOWNLOAD_COMPLETE',flush=True)
