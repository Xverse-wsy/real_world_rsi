#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
exec > >(tee -a .setup/packages.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/packages.exit; echo "Packages exit: $rc"' EXIT
source .setup/activate.sh
uv pip install numpy==1.26.4 setuptools wheel hatchling
uv pip install --no-deps --no-build-isolation -r .setup/requirements.local.txt
uv pip install --no-deps -e .
mkdir -p "$LIBERO_CONFIG_PATH"
cat > "$LIBERO_CONFIG_PATH/config.yaml" <<CONFIG
assets: $PWD/capx/third_party/LIBERO-PRO/libero/libero/assets
bddl_files: $PWD/capx/third_party/LIBERO-PRO/libero/libero/bddl_files
benchmark_root: $PWD/capx/third_party/LIBERO-PRO/libero/libero
datasets: $PWD/capx/third_party/LIBERO-PRO/libero/datasets
init_states: $PWD/capx/third_party/LIBERO-PRO/libero/libero/init_files
CONFIG
python .setup/smoke_libero.py
