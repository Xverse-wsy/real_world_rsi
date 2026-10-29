#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
trap 'echo $? > .setup/graspgen_setup.exit' EXIT
export PATH="$HOME/.local/bin:$PATH"
export CUDA_HOME=/usr/local/cuda-12.4
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export CUDA_VISIBLE_DEVICES=3
export TORCH_CUDA_ARCH_LIST=8.0
export MAX_JOBS=4
export UV_HTTP_TIMEOUT=180
export UV_HTTP_RETRIES=5
export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
uv python install 3.10
uv venv --python 3.10 .venv-graspgen
uv pip install --python .venv-graspgen/bin/python 'torch==2.1.0' 'torchvision==0.16.0' 'numpy==1.26.4' 'setuptools<78' wheel ninja
uv pip install --python .venv-graspgen/bin/python --no-deps --no-index --find-links https://data.pyg.org/whl/torch-2.1.0+cu121.html torch-scatter torch-cluster
uv pip install --python .venv-graspgen/bin/python h5py hydra-core matplotlib meshcat webdataset scikit-learn scipy tensorboard 'trimesh==4.5.3' 'transformers==4.45.2' 'tensordict==0.2.1' 'diffusers==0.11.1' 'timm==1.0.15' 'huggingface-hub==0.25.2' 'PyOpenGL==3.1.0' addict spconv-cu120 'yapf==0.40.1' tensorboardx sharedarray 'yourdfpy==0.0.56' pyrender scene-synthesizer imageio pytest viser pyzmq msgpack msgpack-numpy fastapi uvicorn torch-geometric
uv pip install --python .venv-graspgen/bin/python --no-deps -e capx/third_party/GraspGen
uv pip install --python .venv-graspgen/bin/python --no-build-isolation --no-deps capx/third_party/GraspGen/pointnet2_ops
.venv-graspgen/bin/python -c 'from grasp_gen.grasp_server import GraspGenSampler; print("GraspGen imports OK")'
echo 'GraspGen environment ready'
