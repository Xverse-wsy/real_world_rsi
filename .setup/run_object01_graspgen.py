import getpass,os,subprocess,sys
from pathlib import Path
from datetime import datetime
root=Path(__file__).resolve().parent.parent
os.chdir(root)
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"]=getpass.getpass("OpenAI API key (hidden): ").strip()
if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit("Empty key; no task started")
out=root/"outputs"/("object_01_graspgen_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
out.mkdir()
(root/".setup/object01_graspgen_output.txt").write_text(str(out))
cmd=[sys.executable,"-u",str(root/".setup/run_openai_libero.py"),"--model","gpt-6.1-sol","--grasp-backend","graspgen","--config-path",str(root/"outputs/libero_batch_20261015_115252/configs/libero_object_01.yaml"),"--output-dir",str(out)]
print("Running exactly one episode: libero_object task 01; output:",out,flush=True)
with (out/"run.log").open("w") as log:
    process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    try:
        for line in process.stdout:
            log.write(line);log.flush();print(line,end="",flush=True)
        code=process.wait()
    except KeyboardInterrupt:
        process.send_signal(__import__("signal").SIGINT);process.wait();raise
(out/"exit_code.txt").write_text(str(code))
raise SystemExit(code)
