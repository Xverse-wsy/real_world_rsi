#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
exec > >(tee -a .setup/install.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/install.exit; echo "Installer exit: $rc"' EXIT
source .setup/env.sh
export GIT_LFS_SKIP_SMUDGE=1
git submodule update --init --recursive capx/third_party/LIBERO-PRO capx/third_party/libero_dependencies/robosuite capx/third_party/contact_graspnet_pytorch capx/third_party/sam3 capx/third_party/curobo capx/third_party/verl capx/third_party/robosuite
uv python install 3.12
uv venv .venv-libero --python 3.12
source .venv-libero/bin/activate
uv sync --active --extra libero --extra contactgraspnet
mkdir -p "$LIBERO_CONFIG_PATH"
cat > "$LIBERO_CONFIG_PATH/config.yaml" <<CONFIG
assets: $PWD/capx/third_party/LIBERO-PRO/libero/libero/assets
bddl_files: $PWD/capx/third_party/LIBERO-PRO/libero/libero/bddl_files
benchmark_root: $PWD/capx/third_party/LIBERO-PRO/libero/libero
datasets: $PWD/capx/third_party/LIBERO-PRO/libero/datasets
init_states: $PWD/capx/third_party/LIBERO-PRO/libero/libero/init_files
CONFIG
python -c 'import torch, mujoco, libero; print("torch",torch.__version__,"CUDA",torch.cuda.is_available()); print("mujoco",mujoco.__version__)'
