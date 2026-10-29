#!/usr/bin/env bash
set -euo pipefail
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
exec > >(tee -a .setup/install_archives.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/install.exit; echo "Installer exit: $rc"' EXIT
source .setup/env.sh
mkdir -p .setup/archives
python3 - <<'PY'
import subprocess,configparser
cfg=configparser.ConfigParser(); cfg.read('.gitmodules')
with open('.setup/archives/repos.tsv','w') as f:
    for section in cfg.sections():
        path=cfg[section]['path']
        if path.endswith('/b1k'): continue
        commit=subprocess.check_output(['git','ls-tree','HEAD',path],text=True).split()[2]
        repo=cfg[section]['url'].removeprefix('https://github.com/').removesuffix('.git')
        f.write(f'{path}\t{commit}\t{repo}\n')
PY
while IFS=$'\t' read -r path commit repo; do
  if test -f "$path/.capx_archive_commit" && test "$(cat "$path/.capx_archive_commit")" = "$commit"; then continue; fi
  echo "Downloading source $repo @ $commit"
  archive=".setup/archives/${commit}.tar.gz"
  curl -fsSL --retry 5 --connect-timeout 20 --max-time 300 "https://codeload.github.com/$repo/tar.gz/$commit" -o "$archive"
  mkdir -p "$path"
  tar -xzf "$archive" --strip-components=1 -C "$path"
  echo "$commit" > "$path/.capx_archive_commit"
done < .setup/archives/repos.tsv
uv venv .venv-libero --python /home/wenchaoxu/miniconda3/envs/rsi-libero/bin/python3.12
source .venv-libero/bin/activate
uv sync --frozen --active --extra libero --extra contactgraspnet
mkdir -p "$LIBERO_CONFIG_PATH"
cat > "$LIBERO_CONFIG_PATH/config.yaml" <<CONFIG
assets: $PWD/capx/third_party/LIBERO-PRO/libero/libero/assets
bddl_files: $PWD/capx/third_party/LIBERO-PRO/libero/libero/bddl_files
benchmark_root: $PWD/capx/third_party/LIBERO-PRO/libero/libero
datasets: $PWD/capx/third_party/LIBERO-PRO/libero/datasets
init_states: $PWD/capx/third_party/LIBERO-PRO/libero/libero/init_files
CONFIG
python .setup/smoke_libero.py
