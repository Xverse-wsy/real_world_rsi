"""Back up and patch the A800 one-episode runner; never start an evaluation."""
import ast
from datetime import datetime
from pathlib import Path
import shutil


def main():
    root=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
    path=root/'.setup/run_openai_libero.py'
    source=path.read_text()
    if 'ApiPauseGate' in source:
        print('Runner already has the API pause guard')
        return
    replacements=[
        ('    from openai import OpenAI\n',
         '    from openai import OpenAI, OpenAIError\n'
         '    from capx.llm.api_pause import ApiPauseGate, IncompleteResponseError\n'),
        ('timeout=200.0, max_retries=2)', 'timeout=200.0, max_retries=0)'),
        ('    client.models.retrieve(args.model)\n', '''    active_env = {}
    def api_wait(event):
        import hashlib
        import json
        env = active_env.get("env")
        if env is None:
            return
        low = env.low_level_env
        sim = low.handle.env.sim
        physical = sim.get_state().flatten().tobytes() + sim.data.ctrl.tobytes()
        current = dict(simulation_identity=id(sim), state_sha256=hashlib.sha256(physical).hexdigest(),
                       code_step=env._step_count, control_steps=low._sim_step_count,
                       execution_namespace_identity=id(env._exec_globals))
        if event == "begin":
            active_env["before"] = current
        else:
            if current != active_env.pop("before"):
                raise RuntimeError("Scene or execution state changed during API pause")
            with (gate.directory / "scene_checks.jsonl").open("a") as stream:
                stream.write(json.dumps(dict(state_unchanged=True, state=current)) + "\\n")
            print("API wait ended: original scene and execution context verified unchanged.", flush=True)
    control_dir = ROOT / ".setup/api_control" / ("capx_" + str(os.getpid()) + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    gate = ApiPauseGate(control_dir, on_wait=api_wait)
    print("API pause control directory:", control_dir, flush=True)
    gate.call(lambda: client.models.retrieve(args.model), retryable=(OpenAIError,))
'''),
        ('''        response = client.responses.create(
            model=query_args.model,
            input=messages,
            max_output_tokens=args.max_output_tokens,
            reasoning={"effort": args.reasoning_effort},
            store=False,
        )
        if response.status != "completed":
            raise RuntimeError("OpenAI response did not complete: " + str(response.status))
        if not response.output_text:
            raise RuntimeError("OpenAI response contained no executable text.")
''', '''        def request_response():
            response = client.responses.create(
                model=query_args.model,
                input=messages,
                max_output_tokens=args.max_output_tokens,
                reasoning={"effort": args.reasoning_effort},
                store=False,
            )
            if response.status != "completed" or not response.output_text:
                raise IncompleteResponseError("Response is incomplete or empty")
            return response
        response = gate.call(request_response, retryable=(OpenAIError, IncompleteResponseError))
'''),
        ('    from capx.envs.launch import LaunchArgs, main as launch\n', '''    from capx.envs.launch import LaunchArgs, main as launch
    import capx.envs.runner as runner
    original_trial = runner._run_single_trial
    trial_signature = inspect.signature(original_trial)
    def run_trial_with_api_guard(*call_args, **call_kwargs):
        bound = trial_signature.bind(*call_args, **call_kwargs)
        active_env["env"] = bound.arguments["env"]
        try:
            return original_trial(*call_args, **call_kwargs)
        finally:
            active_env.clear()
    runner._run_single_trial = run_trial_with_api_guard
'''),
    ]
    for old,new in replacements:
        assert source.count(old)==1,('Unexpected runner version; no changes written',old[:90],source.count(old))
        source=source.replace(old,new)
    ast.parse(source)
    backup=path.with_name(path.name+'.before_api_pause_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
    shutil.copy2(path,backup)
    path.write_text(source)
    print('Runner patched; backup:',backup)


if __name__=='__main__':main()
