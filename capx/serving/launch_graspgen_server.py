"""Isolated GraspGen inference service; run with .venv-graspgen/bin/python."""
from __future__ import annotations

import argparse
import base64
from contextlib import asynccontextmanager
import io
from pathlib import Path
import sys
import threading

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "capx/third_party/GraspGen"))
LOCK = threading.Lock()
STATE = {}


def encode(array):
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(array), allow_pickle=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def cloud(value):
    data = np.load(io.BytesIO(base64.b64decode(value)), allow_pickle=False)
    if data.ndim != 2 or data.shape[1] != 3 or len(data) > 2_000_000:
        raise ValueError("Expected (N,3) point cloud with at most 2 million points")
    data = np.asarray(data, dtype=np.float32)
    return data[np.isfinite(data).all(axis=1)]


@asynccontextmanager
async def lifespan(app):
    import torch
    import trimesh
    from grasp_gen.grasp_server import GraspGenSampler, load_grasp_cfg
    from grasp_gen.robot import get_gripper_info
    cfg = load_grasp_cfg(STATE["config"])
    if cfg.data.gripper_name != "franka_panda":
        raise RuntimeError("CAP-X adapter currently supports only franka_panda")
    STATE["sampler"] = GraspGenSampler(cfg)
    info = get_gripper_info("franka_panda")
    # Match the official scene demo: collision mesh lives in GraspGen axes.
    mesh = info.collision_mesh.copy()
    STATE["surface"] = trimesh.sample.sample_surface(mesh, 1500)[0].astype(np.float32)
    STATE["torch"] = torch
    yield
    STATE.clear()


app = FastAPI(lifespan=lifespan)


class PlanRequest(BaseModel):
    pc_full_base64: str
    pc_segment_base64: str


@app.get("/health")
def health():
    return {"ready": "sampler" in STATE, "backend": "graspgen", "gripper": "franka_panda",
            "pose_frame": "graspgen_panda_base", "collision_filter": True}


@app.post("/plan_point_clouds")
def plan(req: PlanRequest):
    from scipy.spatial import cKDTree
    from grasp_gen.grasp_server import GraspGenSampler
    from grasp_gen.utils.point_cloud_utils import filter_colliding_grasps_fast
    try:
        scene, target = cloud(req.pc_full_base64), cloud(req.pc_segment_base64)
        if len(target) < 32:
            raise ValueError("At least 32 finite target points are required")
        # Exclude intended object contacts from obstacle checks, as in the
        # official scene demo. Full scene and target share the robot base frame.
        distances, _ = cKDTree(target).query(scene)
        obstacles = scene[distances > 0.005]
        rng = np.random.default_rng(0)
        if len(target) > 4096:
            target = target[rng.choice(len(target), 4096, replace=False)]
        if len(obstacles) > 8192:
            obstacles = obstacles[rng.choice(len(obstacles), 8192, replace=False)]
        with LOCK, STATE["torch"].inference_mode():
            grasps, scores = GraspGenSampler.run_inference(
                target, STATE["sampler"], grasp_threshold=-1, num_grasps=200,
                topk_num_grasps=100, min_grasps=1, max_tries=2, remove_outliers=True,
            )
            grasps = grasps.detach().cpu().numpy()
            scores = scores.detach().cpu().numpy()
            if not len(grasps):
                raise ValueError("GraspGen found no candidates")
            keep = filter_colliding_grasps_fast(
                obstacles, grasps, gripper_surface_points=STATE["surface"],
                collision_threshold=0.005, batch_size=4, device="cuda",
            )
            grasps, scores = grasps[keep], scores[keep]
            if not len(grasps):
                raise ValueError("All GraspGen candidates collided with observed scene points")
            order = np.argsort(-scores)
            return {"grasps_base64": encode(grasps[order]), "scores_base64": encode(scores[order]),
                    "pose_frame": "graspgen_panda_base", "collision_filter": True,
                    "obstacle_points": len(obstacles)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=str(ROOT / ".cache/models/graspgen/checkpoints/graspgen_franka_panda.yml"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8117)
    args = parser.parse_args()
    STATE["config"] = args.checkpoint
    uvicorn.run(app, host=args.host, port=args.port)
