#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
mkdir -p .cache/models/graspgen/checkpoints
export HF_ENDPOINT=https://hf-mirror.com
trap 'echo $? > .setup/graspgen_download.exit' EXIT
for name in graspgen_franka_panda.yml graspgen_franka_panda_gen.pth graspgen_franka_panda_dis.pth; do
  target=".cache/models/graspgen/checkpoints/$name"
  echo "Downloading $name via hf-mirror"
  curl -fL --connect-timeout 30 --retry 8 --retry-delay 10 -C - "https://hf-mirror.com/adithyamurali/GraspGenModels/resolve/main/checkpoints/$name" -o "$target"
done
printf '%s\n' '0597583b89b322d42ceb4e596967d6ed68d1b56cba4039895909ccd5bdc66eff  .cache/models/graspgen/checkpoints/graspgen_franka_panda_gen.pth' 'e47d703c63b54c2d11fbc1effd43898f251b4147250888541e3b16e9c0d19e1c  .cache/models/graspgen/checkpoints/graspgen_franka_panda_dis.pth' | sha256sum -c -
echo 'Panda weights downloaded and SHA256 verified'
