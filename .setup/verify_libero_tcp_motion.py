import json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from capx.envs.simulators.libero import FrankaLiberoEnv
from capx.integrations.franka.libero import FrankaLiberoApi
ROOT=Path(__file__).resolve().parent.parent
E=FrankaLiberoEnv(suite_name="libero_spatial",task_id=0,seed=0)
A=FrankaLiberoApi(E)
sim=E.handle.env.sim
base_id=E.base_link_idx
site=sim.model.site_name2id("gripper0_grip_site")
def actual_tcp():
    R=sim.data.xmat[base_id].reshape(3,3)
    return R.T @ (sim.data.site_xpos[site]-sim.data.xpos[base_id])
results=[]
for idx,target in enumerate([np.array([0.5,0.04,0.35]),np.array([0.53,-0.03,0.32]),np.array([0.5,0.04,0.35])]):
    quat=np.array([0.,1.,0.,0.])
    if idx==2:
        xyzw=(Rotation.from_euler("y",0.3)*Rotation.from_quat([1.,0.,0.,0.])).as_quat()
        quat=xyzw[[3,0,1,2]]
    A.goto_pose(target,quat,z_approach=0.05 if idx==2 else 0.)
    observed=A.get_observation()["robot_cartesian_pos"]
    tcp=actual_tcp()
    delta=observed[:3]-target
    physical_error=float(np.linalg.norm(tcp-target))
    observation_error=float(np.linalg.norm(observed[:3]-tcp))
    item={"requested":target.tolist(),"observed":observed.tolist(),"physical_tcp":tcp.tolist(),"delta":delta.tolist(),"physical_error_m":physical_error,"observation_error_m":observation_error,"steps":E._sim_step_count,"orientation_error_rad":float((Rotation.from_quat(observed[3:7][[1,2,3,0]]).inv()*Rotation.from_quat(quat[[1,2,3,0]])).magnitude())}
    results.append(item);print(json.dumps(item),flush=True)
    if FrankaLiberoApi._TCP_OFFSET[2]==-0.097:
        assert physical_error<0.005,item
        assert observation_error<1e-8,item
        assert item["orientation_error_rad"]<0.03,item
out=ROOT/".setup"/("tcp_motion_after.json" if FrankaLiberoApi._TCP_OFFSET[2]==-0.097 else "tcp_motion_before.json")
out.write_text(json.dumps(results,indent=2))
E.close()
print("TCP motion verification complete",flush=True)
