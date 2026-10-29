"""Run five tasks from each standard LIBERO suite, one episode per task."""
import argparse
import copy
from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SUITES = ['libero_spatial', 'libero_object', 'libero_goal', 'libero_10', 'libero_90']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='gpt-6.1-sol')
    parser.add_argument('--suites', nargs='+', choices=SUITES, default=SUITES)
    parser.add_argument('--tasks-per-suite', type=int, default=5)
    parser.add_argument('--output-dir')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.tasks_per_suite <= 10:
        parser.error('--tasks-per-suite must be between 1 and 10')
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import yaml
    from libero import benchmark
    suites = list(dict.fromkeys(args.suites))
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = Path(args.output_dir or ROOT / 'outputs' / ('libero_batch_' + stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    configs = out / 'configs'
    configs.mkdir()
    base = yaml.safe_load((ROOT / 'env_configs/libero/franka_libero_spatial_0.yaml').read_text())
    plan = []
    for name in suites:
        suite = benchmark.get_benchmark_dict()[name]()
        for task_id in range(args.tasks_per_suite):
            task = suite.get_task(task_id)
            cfg = copy.deepcopy(base)
            cfg['env']['cfg']['low_level']['suite_name'] = name
            cfg['env']['cfg']['low_level']['task_id'] = task_id
            cfg['trials'] = 1
            cfg['num_workers'] = 1
            path = configs / f'{name}_{task_id:02d}.yaml'
            path.write_text(yaml.safe_dump(cfg, sort_keys=False))
            plan.append(dict(suite=name, task_id=task_id, task_name=task.name,
                             language=task.language, config=str(path),
                             output_dir=str(out / name / f'task_{task_id:02d}')))
    manifest = dict(model=args.model, tasks=plan, trials_per_task=1,
                    task_selection='first N IDs, task_order_index=0',
                    gpu=3, molmo=True, visual_feedback=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Batch directory: {out}', flush=True)
    print(f'{len(suites)} suites x {args.tasks_per_suite} tasks x 1 episode = {len(plan)} episodes', flush=True)
    if args.dry_run:
        print('Dry run complete; no model API requests or simulation executed.', flush=True)
        return
    if not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = getpass.getpass('OpenAI API key (hidden; stored only in process memory): ').strip()
    if not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Empty API key; no tasks started.')
    with urllib.request.urlopen('http://127.0.0.1:8122/v1/models', timeout=10) as response:
        names = [item['id'] for item in json.load(response)['data']]
    if 'allenai/Molmo2-8B' not in names:
        raise SystemExit('Molmo2-8B is not ready; no tasks started.')
    # Fail early on model access/authentication rather than repeat the same failure 25 times.
    from openai import OpenAI
    OpenAI(base_url='https://api.openai.com/v1').models.retrieve(args.model)
    results = []
    for idx, task in enumerate(plan, 1):
        task_out = Path(task['output_dir'])
        task_out.mkdir(parents=True)
        print(f'[{idx}/{len(plan)}] {task["suite"]} task {task["task_id"]}: {task["language"]}', flush=True)
        started = time.monotonic()
        command = [sys.executable, '-u', str(ROOT / '.setup/run_openai_libero.py'),
                   '--model', args.model, '--config-path', task['config'],
                   '--output-dir', str(task_out)]
        with (task_out / 'run.log').open('w') as log:
            proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        summaries = sorted(task_out.rglob('summaries.txt'))
        completed = None
        reward = None
        if summaries or (task_out / 'run.log').exists():
            text = summaries[-1].read_text() if summaries else (task_out / 'run.log').read_text(errors='replace')
            match = re.search(r'Code generation success rate / Average reward / Task completed:\s*([\d.]+)/([\d.]+)/(\d+)', text)
            if match:
                reward = float(match[2])
                completed = int(match[3]) == 1
        result = dict(suite=task['suite'], task_id=task['task_id'], task_name=task['task_name'],
                      process_returncode=proc.returncode, task_completed=completed, reward=reward,
                      elapsed_seconds=round(time.monotonic()-started, 2), output_dir=str(task_out))
        results.append(result)
        summary = dict(model=args.model, planned=len(plan), finished=len(results), results=results,
                       by_suite={name: dict(finished=sum(r['suite']==name for r in results),
                                            succeeded=sum(r['suite']==name and r['task_completed'] is True for r in results),
                                            unknown=sum(r['suite']==name and r['task_completed'] is None for r in results))
                                 for name in suites})
        temporary = out / 'summary.json.tmp'
        temporary.write_text(json.dumps(summary, indent=2))
        temporary.replace(out / 'summary.json')
        print(f'  completed={completed}, reward={reward}, returncode={proc.returncode}; log={task_out / "run.log"}', flush=True)
    print(f'Batch finished. Results: {out / "summary.json"}', flush=True)


if __name__ == '__main__':
    main()
