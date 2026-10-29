#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
export CUDA_VISIBLE_DEVICES=3
export CUDA_HOME=/usr/local/cuda-12.4
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
exec .venv-graspgen/bin/python capx/serving/launch_graspgen_server.py --port 8117
