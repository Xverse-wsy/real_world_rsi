import os, subprocess, time, json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
os.chdir(ROOT)
status=ROOT/".setup/molmo_background_status.json"
def update(stage, **details):
    status.write_text(json.dumps({"stage":stage,"updated_unix":time.time(),**details},indent=2))
    print(stage,details,flush=True)
for attempt in range(1,4):
    update("downloading", attempt=attempt)
    with open(ROOT/".setup/molmo_ranges.log","a") as log:
        rc=subprocess.call([str(ROOT/".venv-libero/bin/python"),"-u",str(ROOT/".setup/download_molmo_ranges.py")],stdout=log,stderr=subprocess.STDOUT)
    if rc==0: break
    update("download_retry_wait", attempt=attempt)
    if attempt<3: time.sleep(60)
else:
    update("download_failed", message="HF Mirror failed after retries; partial blocks preserved")
    raise SystemExit(1)
update("starting_service", gpu=3, port=8122)
with open(ROOT/".setup/molmo_server.log","a") as log:
    server=subprocess.Popen(["bash",str(ROOT/".setup/start_molmo.sh")],stdout=log,stderr=subprocess.STDOUT)
    for _ in range(120):
        if server.poll() is not None:
            update("service_failed",exit_code=server.returncode)
            raise SystemExit(1)
        try:
            r=requests.get("http://127.0.0.1:8122/v1/models",timeout=3)
            if r.status_code==200 and any(m["id"]=="allenai/Molmo2-8B" for m in r.json()["data"]):
                update("service_ready",gpu=3,port=8122,pid=server.pid)
                break
        except requests.RequestException: pass
        time.sleep(5)
    else:
        update("service_start_timeout",message="Check molmo_server.log; process retained",pid=server.pid)
    server.wait()
    update("service_exited",exit_code=server.returncode)
