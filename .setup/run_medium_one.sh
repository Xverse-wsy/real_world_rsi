#!/usr/bin/env bash
# Prepare services and run exactly one episode only when invoked by the user.
set -eo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
source .setup/activate.sh
source /home/wenchaoxu/wsy/CLIProxyAPI/.setup/client.env
set -u
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=3
export MUJOCO_EGL_DEVICE_ID=3
export PYTHONUNBUFFERED=1
export NO_PROXY="127.0.0.1,localhost,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
RUN_NAME="libero_spatial_0_medium_$(date +%Y%m%d_%H%M%S)_$$"
RUN_DIR="$PWD/outputs/gpt-6.1-sol/$RUN_NAME"
mkdir -p "$RUN_DIR"
exec > >(tee -a "$RUN_DIR/run.log") 2>&1
trap 'rc=$?; echo "$rc" > "$RUN_DIR/exit_code"; echo "Exit code: $rc | Files: $RUN_DIR"' EXIT
echo "Output: $RUN_DIR"
echo "One episode | Spatial task_id=0 | GPU=3 | gpt-6.1-sol | medium | original | GraspGen"
python - <<'PY'
from openai import OpenAI
import urllib.request
client=OpenAI(timeout=20, max_retries=0)
client.models.retrieve("gpt-6.1-sol")
print("Proxy model check: OK", flush=True)
for name, port in [("SAM3",8114),("Pyroki",8116),("GraspGen",8117)]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=10) as r:
            assert r.status == 200
    except Exception as exc:
        raise SystemExit(f"{name} is unavailable on port {port}: {exc}")
    print(f"{name}: OK", flush=True)
PY
molmo_ready() {
    python - <<'PY'
import json, sys, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8122/v1/models", timeout=3) as r:
        data=json.load(r)
    sys.exit(0 if any(m["id"]=="allenai/Molmo2-8B" for m in data["data"]) else 1)
except Exception:
    sys.exit(1)
PY
}
if ! molmo_ready; then
    if ! screen -ls | grep -q '[.]capx_molmo_medium[[:space:]]'; then
        echo "Starting Molmo2-8B on GPU 3 in screen capx_molmo_medium."
        screen -dmS capx_molmo_medium bash -o pipefail -c \
          'bash .setup/start_molmo.sh 2>&1 | tee -a .setup/molmo_medium_server.log'
    fi
    ready=0
    for attempt in $(seq 1 120); do
        if molmo_ready; then ready=1; break; fi
        if ! screen -ls | grep -q '[.]capx_molmo_medium[[:space:]]'; then
            echo "Molmo startup exited; see .setup/molmo_medium_server.log"
            exit 1
        fi
        echo "Waiting for Molmo2-8B ($attempt/120)..."
        sleep 5
    done
    if [ "$ready" -ne 1 ]; then
        echo "Molmo startup timed out; see .setup/molmo_medium_server.log"
        exit 1
    fi
fi
echo "Molmo2-8B: OK"
python - "$RUN_DIR" <<'PY'
from pathlib import Path
import sys, yaml
run=Path(sys.argv[1])
cfg=yaml.safe_load(Path("env_configs/libero/franka_libero_spatial_0.yaml").read_text())
# Healthy shared services were checked above; do not spawn duplicate servers.
cfg["api_servers"]=[]
(run/"config.yaml").write_text(yaml.safe_dump(cfg,sort_keys=False))
PY
python -u .setup/run_openai_libero.py \
  --model gpt-6.1-sol \
  --reasoning-effort medium \
  --prompt-profile original \
  --grasp-backend graspgen \
  --config-path "$RUN_DIR/config.yaml" \
  --output-dir "$PWD/outputs/$RUN_NAME"
