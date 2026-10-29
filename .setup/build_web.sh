set -euo pipefail
exec > >(tee -a .setup/web.log) 2>&1
cd web-ui
node --version
npm ci --registry=https://registry.npmmirror.com
npm run build
