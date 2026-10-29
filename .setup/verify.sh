set -euo pipefail
exec > >(tee -a .setup/verify.log) 2>&1
trap 'rc=$?; echo "$rc" > .setup/verify.exit; echo "Verification exit: $rc"' EXIT
source .setup/activate.sh
uv pip check > .setup/pip_check.txt 2>&1 || cat .setup/pip_check.txt
python .setup/smoke_libero.py
python .setup/smoke_capx.py
python -c 'import sam3; import contact_graspnet_pytorch.contact_graspnet; import pyroki; import capx.web.server; print("COMPONENT_IMPORTS_OK")'
python capx/envs/launch.py --help > .setup/launch_help.txt
