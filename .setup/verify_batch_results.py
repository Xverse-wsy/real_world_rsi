from pathlib import Path
import json,re,time,os
root=Path('outputs/libero_batch_20261015_115252')
while True:
 p=root/'summary.json'
 if p.exists():
  data=json.loads(p.read_text())
  for r in data['results']:
   log=Path(r['output_dir'])/'run.log'
   if log.exists():
    matches=list(re.finditer(r'Code generation success rate / Average reward / Task completed:\s*([\d.]+)/([\d.]+)/(\d+)',log.read_text(errors='replace')))
    if matches:
     m=matches[-1];r['reward']=float(m[2]);r['task_completed']=int(m[3])==1
  for name in data['by_suite']:
   rows=[r for r in data['results'] if r['suite']==name]
   data['by_suite'][name]={'finished':len(rows),'succeeded':sum(r['task_completed'] is True for r in rows),'unknown':sum(r['task_completed'] is None for r in rows)}
  tmp=root/'summary_verified.json.tmp';tmp.write_text(json.dumps(data,indent=2));tmp.replace(root/'summary_verified.json')
  if not Path('/proc/202136').exists():break
 time.sleep(5)
