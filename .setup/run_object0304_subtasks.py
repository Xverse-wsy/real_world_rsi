import getpass,json,os,re,subprocess,sys,time
from pathlib import Path
from datetime import datetime
root=Path(__file__).resolve().parent.parent
os.chdir(root)
out=root/'outputs'/('object_03_04_graspgen_subtasks_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
out.mkdir()
(root/'.setup/object0304_subtasks_output.txt').write_text(str(out))
(out/'status.json').write_text(json.dumps({'state':'waiting_for_api_key','tasks':[3,4], 'prompt_profile':'subtasks'}))
print('Output:',out,flush=True)
if not os.environ.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY']=getpass.getpass('OpenAI API key (hidden): ').strip()
if not os.environ.get('OPENAI_API_KEY'):
    raise SystemExit('Empty key; no task started')
results=[]
for task in (3,4):
    taskout=out/('task_%02d'%task)
    taskout.mkdir()
    (out/'status.json').write_text(json.dumps({'state':'running','current_task':task,'results':results},indent=2))
    cmd=[sys.executable,'-u',str(root/'.setup/run_openai_libero.py'),'--model','gpt-6.1-sol','--grasp-backend','graspgen','--prompt-profile','subtasks','--config-path',str(root/('outputs/libero_batch_20261015_115252/configs/libero_object_%02d.yaml'%task)),'--output-dir',str(taskout)]
    print('Starting object task %02d (one episode)'%task,flush=True)
    start=time.monotonic()
    with (taskout/'run.log').open('w') as log:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        try:
            for line in proc.stdout:
                log.write(line);log.flush();print(line,end='',flush=True)
            code=proc.wait()
        except KeyboardInterrupt:
            proc.send_signal(__import__('signal').SIGINT);proc.wait();raise
    text=(taskout/'run.log').read_text(errors='replace')
    match=re.search(r'Code generation success rate / Average reward / Task completed:\s*([\d.]+)/([\d.]+)/(\d+)',text)
    result={'task_id':task,'exit_code':code,'task_completed':bool(int(match[3])) if match else None,'reward':float(match[2]) if match else None,'elapsed_seconds':round(time.monotonic()-start,2),'output_dir':str(taskout)}
    results.append(result)
    (taskout/'exit_code.txt').write_text(str(code))
    (out/'summary.json').write_text(json.dumps(results,indent=2))
(out/'status.json').write_text(json.dumps({'state':'finished','results':results},indent=2))
print('Both episodes finished:',json.dumps(results),flush=True)
