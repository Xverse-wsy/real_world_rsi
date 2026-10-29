#!/usr/bin/env bash
set -eo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
source .setup/activate.sh
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=3 MUJOCO_EGL_DEVICE_ID=3
export JAX_PLATFORMS=cpu PYTHONUNBUFFERED=1
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
trap 'echo "$?" > /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/exit_code' EXIT
.venv-libero/bin/python -u cliproxy_a800_setup/check_normal_execution.py \
  --runner .setup/run_openai_libero.py.before_api_pause_20261019_163105.bak \
  --output /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/before 2>&1 | tee /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/before.log
.venv-libero/bin/python -u cliproxy_a800_setup/check_normal_execution.py \
  --runner .setup/run_openai_libero.py \
  --output /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/after 2>&1 | tee /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/after.log
.venv-libero/bin/python cliproxy_a800_setup/compare_normal_execution.py /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor
export LIBERO_CONFIG_PATH=/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/libero-resources/config
export JAX_PLATFORMS=cpu MUJOCO_GL=egl PYOPENGL_PLATFORM=egl LIBERO_TYPE=standard ROBOT_PLATFORM=LIBERO
export PYTHONPATH=/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/RLinf:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/openpi/src:/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/openpi/packages/openpi-client/src
/home/wenchaoxu/miniconda3/envs/corrector-eval/bin/python -u -m hybrid.check_api_worker 2>&1 | tee /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/hybrid_normal.log
/home/wenchaoxu/miniconda3/envs/corrector-eval/bin/python -u -m hybrid.check_api_pause 2>&1 | tee /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/outputs/capx_api_review_20261019_164239/hybrid_pause.log
echo ALL_REVIEW_CHECKS_PASSED
