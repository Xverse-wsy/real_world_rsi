#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
export CUDA_VISIBLE_DEVICES=3
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="$PWD/.cache/huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
exec .venv-molmo/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$PWD/.cache/models/molmo2-8b" \
  --served-model-name allenai/Molmo2-8B \
  --host 127.0.0.1 --port 8122 \
  --dtype bfloat16 --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.45 --max-model-len 8192 \
  --max-num-seqs 2 --enforce-eager \
  --trust-remote-code
