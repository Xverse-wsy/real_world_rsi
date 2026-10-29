
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
