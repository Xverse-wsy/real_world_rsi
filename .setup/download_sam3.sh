#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
exec > >(tee -a .setup/download_sam3.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/download_sam3.exit; echo "Download exit: $rc"' EXIT
source .setup/activate.sh
export HF_HUB_OFFLINE=0
export TRANSFORMERS_OFFLINE=0
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=120
python .setup/download_sam3.py
