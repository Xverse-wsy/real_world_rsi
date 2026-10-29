#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
exec > >(tee -a .setup/download_sam3_modelscope.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/download_sam3_modelscope.exit; echo "ModelScope download exit: $rc"' EXIT
source .setup/activate.sh
python .setup/download_sam3_modelscope.py
