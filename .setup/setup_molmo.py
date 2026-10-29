import os, subprocess, json, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.update(HF_ENDPOINT="https://hf-mirror.com", HF_HUB_OFFLINE="0", TRANSFORMERS_OFFLINE="0", HF_HUB_DISABLE_XET="1", HF_HUB_DOWNLOAD_TIMEOUT="120")
venv = ROOT / ".venv-molmo"
subprocess.run(["/home/wenchaoxu/.local/bin/uv", "venv", "--python", str(ROOT / ".venv-libero/bin/python"), str(venv)], check=True)
install_log = open(ROOT / ".setup/molmo_install.log", "w")
installer = subprocess.Popen(["/home/wenchaoxu/.local/bin/uv", "pip", "install", "--python", str(venv / "bin/python"), "--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple", "vllm==0.15.0"], stdout=install_log, stderr=subprocess.STDOUT)
try:
    from huggingface_hub import snapshot_download
    revision = "e28fa28597e5ec5e0cca2201dd8ab33d48bc4a1b"
    dest = ROOT / ".cache/models/molmo2-8b"
    snapshot_download("allenai/Molmo2-8B", revision=revision, local_dir=str(dest), endpoint="https://hf-mirror.com", max_workers=8, ignore_patterns=["*.png", ".gitattributes"])
    rc = installer.wait()
    if rc:
        raise RuntimeError("vLLM installation failed; see molmo_install.log")
    (ROOT / ".setup/molmo_download.json").write_text(json.dumps({"repo_id":"allenai/Molmo2-8B", "revision":revision, "endpoint":"https://hf-mirror.com", "path":str(dest)}, indent=2))
    (ROOT / ".setup/molmo_setup.exit").write_text("0\n")
    print("Molmo download and vLLM installation complete", flush=True)
except Exception:
    traceback.print_exc()
    installer.wait()
    (ROOT / ".setup/molmo_setup.exit").write_text("1\n")
    raise
