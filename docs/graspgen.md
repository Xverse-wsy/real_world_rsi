# GraspGen backend for LIBERO

`FrankaLiberoApi` supports `CAPX_GRASP_BACKEND=graspgen` for
`sample_grasp_pose` and `plan_grasp_from_point_clouds`. The default remains
`contact_graspnet`; the A800 OpenAI runner switches its own default to GraspGen
only after the background readiness checks pass. Existing depth-image and alternate robot interfaces still
use Contact-GraspNet. There is no silent fallback if GraspGen fails.

The model runs in a separate environment and HTTP service on port 8117. On the
A800 setup, run `bash .setup/start_graspgen.sh` in screen. The Panda checkpoints
are stored under `.cache/models/graspgen/checkpoints/`; the isolated environment
is `.venv-graspgen`, using Python 3.10 and the official PyTorch 2.1 stack.

After the service is ready, run a task in the existing LIBERO environment:

```bash
CAPX_GRASP_BACKEND=graspgen python .setup/run_openai_libero.py --model gpt-6.1-sol
```

Use `CAPX_GRASP_BACKEND=contact_graspnet` to select the original backend.
The runner still requires `OPENAI_API_KEY` from the interactive shell.
Its `--grasp-backend graspgen` / `--grasp-backend contact_graspnet` flags can
also select the backend explicitly. Check `.setup/graspgen_status.json` for
background setup status and `.setup/graspgen_server.log` for service logs.

## Pose contract

Both point clouds and predicted grasp transforms are in the robot base frame,
in metres. The service returns the learned Panda gripper-base pose, with jaw
closing along X and approach along positive Z. The adapter translates by
97 mm along the grasp's **local** positive Z to reach MuJoCo's grip site.
`sample_grasp_pose` then applies its existing local Rz(pi/2) to express the
orientation in panda_hand axes. `goto_pose` subtracts the same local 97 mm to
recover the physical hand origin. The Contact-GraspNet-only 120 mm shift is
skipped. GraspGen's nominal 105.27314 mm fingertip depth is not used as the
MuJoCo observation-site offset.

## Candidate checks and limits

The service samples 200 diffusion grasps, ranks up to 100 candidates, and
filters the open-gripper mesh against observed scene points. Target points
are excluded from obstacles using a 5 mm nearest-neighbour threshold. This
is a point-cloud approximation: segmentation errors and occluded obstacles
remain possible.

The LIBERO API tries up to the 10 highest-ranked remaining candidates. It
checks IK residuals for the grasp and a 10 cm pre-grasp, accepting at most
10 mm position and 0.15 rad orientation error. These checks do not validate
whole-arm collisions, the entire approach trajectory, grasp stability, or
object identity. The code-generating model must still verify a lift before
transport and check task completion after placement.

The adapter tests cover tilted TCP conversion, jaw-axis alignment, protocol
convention rejection and candidate-score preservation. End-to-end task success
must be measured separately from successful inference.
