#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=3 MUJOCO_EGL_DEVICE_ID=3
export LIBERO_CONFIG_PATH=/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/libero-resources/config
export JAX_PLATFORMS=cpu MUJOCO_GL=egl PYOPENGL_PLATFORM=egl LIBERO_TYPE=standard ROBOT_PLATFORM=LIBERO
export HF_ENDPOINT=https://hf-mirror.com HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONPATH=/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/RLinf:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/openpi/src:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/openpi/packages/openpi-client/src
trap 'echo "$?" > /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.setup/capx_api_pause_check_20261019_163137.exit' EXIT
/home/wenchaoxu/miniconda3/envs/corrector-eval/bin/python -u -m hybrid.check_api_pause 2>&1 | tee /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.setup/capx_api_pause_check_20261019_163137.log
