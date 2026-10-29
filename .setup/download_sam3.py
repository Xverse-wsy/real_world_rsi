import os, json
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import get_token
root=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
cache=root/'.cache/huggingface/hub'
token=get_token()
if not token:
    previous_token=Path.home()/'.cache/huggingface/token'
    if previous_token.is_file():
        token=previous_token.read_text().strip()
print('Endpoint:',os.environ['HF_ENDPOINT'],flush=True)
print('Cache:',cache,flush=True)
print('Stored HF authentication available:',bool(token),flush=True)
api=HfApi(endpoint=os.environ['HF_ENDPOINT'],token=token)
info=api.model_info('facebook/sam3',files_metadata=True)
print('Revision:',info.sha,flush=True)
result={'repo':'facebook/sam3','revision':info.sha,'cache_dir':str(cache),'files':{}}
for filename in ('config.json','sam3.pt'):
    print('Downloading:',filename,flush=True)
    path=hf_hub_download(repo_id='facebook/sam3',filename=filename,revision=info.sha,cache_dir=str(cache),token=token)
    result['files'][filename]={'path':path,'bytes':Path(path).stat().st_size}
    print('Saved:',path,'bytes:',Path(path).stat().st_size,flush=True)
(root/'.setup/sam3_download.json').write_text(json.dumps(result,indent=2)+'\n')
print('SAM3_DOWNLOAD_COMPLETE',flush=True)
