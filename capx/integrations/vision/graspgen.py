"""HTTP client for the isolated GraspGen Panda service.

The returned matrices use TCP positions and GraspGen's gripper axes. LIBERO's
sample_grasp_pose applies Rz(pi/2) to express orientation in panda_hand axes.
Unlike Contact-GraspNet results these must NOT receive the legacy 120 mm shift.
"""
from __future__ import annotations

import base64
import io
import os

import numpy as np
import requests

PANDA_TCP_DEPTH = 0.097  # MuJoCo panda_hand -> gripper0_grip_site, metres.


def encode_array(array: np.ndarray) -> str:
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(array), allow_pickle=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_array(value: str) -> np.ndarray:
    return np.load(io.BytesIO(base64.b64decode(value)), allow_pickle=False)


def panda_base_to_tcp(grasps: np.ndarray) -> np.ndarray:
    """Move the learned gripper base origin to LIBERO's actual grasp site.

    GraspGen Panda closes along X; panda_hand closes along Y. Their approach Z
    axes coincide, so the 97 mm translation precedes the caller's Rz(pi/2).
    Keep the learned hand origin: do not use GraspGen's nominal fingertip depth
    (105.27314 mm) as LIBERO's observation-site offset.
    """
    poses = np.asarray(grasps, dtype=np.float64)
    if poses.ndim != 3 or poses.shape[1:] != (4, 4) or not np.isfinite(poses).all():
        raise ValueError("GraspGen must return finite (N, 4, 4) poses")
    poses = poses.copy()
    poses[:, :3, 3] += poses[:, :3, 2] * PANDA_TCP_DEPTH
    return poses


def init_graspgen_point_clouds():
    url = os.environ.get("GRASPGEN_SERVICE_URL", "http://127.0.0.1:8117").rstrip("/")

    def plan(pc_full, pc_segment, **_compatibility_args):
        response = requests.post(
            url + "/plan_point_clouds",
            json={"pc_full_base64": encode_array(np.asarray(pc_full, dtype=np.float32)),
                  "pc_segment_base64": encode_array(np.asarray(pc_segment, dtype=np.float32))},
            timeout=(10, 180),
        )
        response.raise_for_status()
        result = response.json()
        if result.get("pose_frame") != "graspgen_panda_base":
            raise ValueError("Unexpected GraspGen pose convention; refusing to execute")
        poses = panda_base_to_tcp(decode_array(result["grasps_base64"]))
        scores = decode_array(result["scores_base64"]).reshape(-1)
        if not len(poses) or len(poses) != len(scores) or not np.isfinite(scores).all():
            raise ValueError("GraspGen returned no valid collision-filtered candidates")
        print(f"GraspGen: {len(poses)} candidates after scene collision filtering")
        return poses, scores, poses[:, :3, 3].copy()

    return plan
