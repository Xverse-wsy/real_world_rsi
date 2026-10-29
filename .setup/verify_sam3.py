from pathlib import Path
import os, torch
from huggingface_hub import hf_hub_download
from sam3.model_builder import build_sam3_image_model
root=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
for name in ('config.json','sam3.pt'):
 path=hf_hub_download('facebook/sam3',name,local_files_only=True)
 print('OFFLINE_CACHE',name,path,flush=True)
checkpoint=root/'.cache/models/sam3/sam3.pt'
model=build_sam3_image_model(checkpoint_path=str(checkpoint),load_from_HF=False,device='cuda',enable_inst_interactivity=True)
print('MODEL_DEVICE',next(model.parameters()).device,flush=True)
print('MODEL_PARAMETER_COUNT',sum(p.numel() for p in model.parameters()),flush=True)
print('SAM3_OFFLINE_LOAD_OK',flush=True)
