import os
import numpy as np
import torch
from libero import benchmark
from libero.utils import get_libero_path
from libero.envs import OffScreenRenderEnv
print('torch:', torch.__version__, 'cuda:', torch.version.cuda, 'available:', torch.cuda.is_available(), flush=True)
assert torch.cuda.is_available()
print('CUDA tensor:', (torch.ones(4, device='cuda') * 2).cpu(), flush=True)
suite = benchmark.get_benchmark_dict()['libero_spatial']()
task = suite.get_task(0)
print('Task:', task.language, flush=True)
path = os.path.join(get_libero_path('bddl_files'), task.problem_folder, task.bddl_file)
env = OffScreenRenderEnv(bddl_file_name=path, camera_heights=128, camera_widths=128)
try:
    env.seed(0)
    obs = env.reset()
    for _ in range(5):
        obs, reward, done, info = env.step(np.zeros(7))
    print('Camera:', obs['agentview_image'].shape, 'reward:', reward, 'done:', done, flush=True)
finally:
    env.close()
print('LIBERO_SMOKE_OK', flush=True)
