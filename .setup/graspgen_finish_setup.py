"""Wait for background install, start GraspGen, then validate before selecting it."""
from pathlib import Path
import ast
import json
import os
import subprocess
import time
import traceback
import urllib.request

ROOT = Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
os.chdir(ROOT)
STATUS = ROOT / '.setup/graspgen_status.json'


def status(stage, **details):
    value = dict(stage=stage, timestamp=time.strftime('%Y-%m-%d %H:%M:%S'), **details)
    STATUS.write_text(json.dumps(value, indent=2))
    print(json.dumps(value), flush=True)


SMOKE = r'''
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from capx.integrations.vision.graspgen import init_graspgen_point_clouds
rng=np.random.default_rng(7)
# Dense 4 cm cube, resting on a tabletop in robot-base coordinates.
target=rng.uniform(-.02,.02,size=(2048,3)).astype(np.float32)
axes=rng.integers(0,3,len(target));target[np.arange(len(target)),axes]=rng.choice([-.02,.02],len(target))
target += np.array([.55,0,.06],np.float32)
table=rng.uniform([.25,-.4,.039],[.85,.4,.039],size=(8192,3)).astype(np.float32)
grasps,scores,_=init_graspgen_point_clouds()(np.concatenate([target,table]),target)
assert len(grasps)>0 and np.isfinite(grasps).all()
np.savez('.setup/graspgen_smoke_grasps.npz',grasps=grasps,scores=scores)
from capx.integrations.franka.libero import FrankaLiberoApi
from capx.integrations.motion.pyroki_context import get_pyroki_context
from capx.integrations.motion import pyroki_snippets
api=FrankaLiberoApi.__new__(FrankaLiberoApi)
ctx=get_pyroki_context('panda_description',target_link_name='panda_hand')
api._robot=ctx.robot;api._target_link_name=ctx.target_link_name;api._pks=pyroki_snippets
idx=api._select_reachable_grasp(grasps,scores)
print(json.dumps({'candidates':len(grasps),'selected_reachable_candidate':idx,'score':float(scores[idx])}))
'''


def main():
    status('waiting_for_environment', weights='downloaded_sha256_verified')
    deadline=time.monotonic()+10800
    for filename in ['graspgen_download.exit','graspgen_setup.exit']:
        path=ROOT/'.setup'/filename
        while not path.exists():
            if time.monotonic()>deadline:raise TimeoutError('Background setup timed out: '+filename)
            time.sleep(10)
        if path.read_text().strip()!='0':
            raise RuntimeError(filename+' failed; inspect corresponding .log')
    status('starting_service')
    try:
        urllib.request.urlopen('http://127.0.0.1:8117/health', timeout=2).close()
    except Exception:
        subprocess.run(['screen','-dmS','capx_graspgen_server','bash','-c',
                        'bash .setup/start_graspgen.sh > .setup/graspgen_server.log 2>&1; exec bash'],check=True)
    deadline=time.monotonic()+600
    while True:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8117/health',timeout=3) as response:
                health=json.load(response)
            if health.get('ready'):break
        except Exception:pass
        if time.monotonic()>deadline:raise TimeoutError('GraspGen service failed to become ready')
        time.sleep(5)
    status('validating_inference_and_ik')
    script=ROOT/'.setup/graspgen_smoke_test.py';script.write_text(SMOKE)
    env=os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='3',MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='3',
               LIBERO_CONFIG_PATH=str(ROOT/'.setup/libero'),HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1',CAPX_GRASP_BACKEND='graspgen')
    with (ROOT/'.setup/graspgen_smoke_test.log').open('w') as log:
        subprocess.run([str(ROOT/'.venv-libero/bin/python'),str(script)],env=env,
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    # Switch only after real model inference, collision filtering, and IK pass.
    runner=ROOT/'.setup/run_openai_libero.py';text=runner.read_text()
    old='default=os.environ.get("CAPX_GRASP_BACKEND", "contact_graspnet")'
    new='default=os.environ.get("CAPX_GRASP_BACKEND", "graspgen")'
    if old not in text and new not in text:raise RuntimeError('Runner changed; refusing automatic edit')
    text=text.replace(old,new,1);ast.parse(text);runner.write_text(text)
    status('ready',default_backend='graspgen',gpu=3,url='http://127.0.0.1:8117',
           weights='sha256_verified',checks=['adapter_tests','real_model_inference','scene_collision_filter','grasp_and_pregrasp_ik'],
           task_success_tested=False)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        status('failed',error=str(exc),default_backend='contact_graspnet')
        traceback.print_exc()
        raise
