import torch
from capx.envs.simulators.libero import FrankaLiberoEnv
from capx.envs.tasks.base import CodeExecEnvConfig
from capx.envs.tasks.franka.franka_libero_env import FrankaLiberoCodeEnv
from capx.integrations.base_api import list_apis
print('LIBERO APIs:', [n for n in list_apis() if 'Libero' in n], flush=True)
low=FrankaLiberoEnv(suite_name='libero_spatial',task_id=0,privileged=True,enable_render=False)
env=FrankaLiberoCodeEnv(CodeExecEnvConfig(low_level=low,apis=['FrankaLiberoPrivilegedApi'],privileged=True))
obs,info=env.reset(seed=0)
print('Observation keys:',list(obs),flush=True)
obs,reward,terminated,truncated,info=env.step("open_gripper()\nprint('API_EXEC_OK')")
print('Execution:',info,'reward:',reward,flush=True)
assert info['sandbox_rc']==0
assert 'API_EXEC_OK' in info['stdout']
print('CAPX_SMOKE_OK',flush=True)
