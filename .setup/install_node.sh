set -euo pipefail
exec > >(tee -a .setup/node.log) 2>&1
curl -fsSL --retry 3 --connect-timeout 15 --max-time 180 https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz -o .setup/archives/node-v22.14.0-linux-x64.tar.xz
mkdir -p .setup/node22
tar -xJf .setup/archives/node-v22.14.0-linux-x64.tar.xz --strip-components=1 -C .setup/node22
export PATH="$PWD/.setup/node22/bin:$PATH"
bash .setup/build_web.sh
