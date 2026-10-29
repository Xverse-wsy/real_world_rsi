"""Run one LIBERO episode through an OpenAI-compatible Responses API."""
import argparse
import inspect
from datetime import datetime
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--model", help="Exact OpenAI API model ID")
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--config-path", default=str(ROOT / "env_configs/libero/franka_libero_spatial_0.yaml"))
    parser.add_argument("--output-dir")
    parser.add_argument("--prompt-profile", choices=["original", "subtasks"], default="subtasks", help="subtasks: one observable subtask per turn; original: unchanged input-config prompts")
    parser.add_argument("--grasp-backend", choices=["contact_graspnet", "graspgen"], default=os.environ.get("CAPX_GRASP_BACKEND", "graspgen"))
    args = parser.parse_args()
    if not args.list_models and not args.model:
        parser.error("Specify --list-models or --model.")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("Set OPENAI_API_KEY using the interactive shell prompt.")
    from openai import OpenAI, OpenAIError
    from capx.llm.api_pause import ApiPauseGate, IncompleteResponseError
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1"
    client = OpenAI(api_key=key, base_url=base_url, timeout=200.0, max_retries=0)
    if args.list_models:
        for model_id in sorted(model.id for model in client.models.list()):
            print(model_id)
        return
    active_env = {}
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
                stream.write(json.dumps(dict(state_unchanged=True, state=current)) + "\n")
            print("API wait ended: original scene and execution context verified unchanged.", flush=True)
    control_dir = ROOT / ".setup/api_control" / ("capx_" + str(os.getpid()) + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    gate = ApiPauseGate(control_dir, on_wait=api_wait)
    print("API pause control directory:", control_dir, flush=True)
    gate.call(lambda: client.models.retrieve(args.model), retryable=(OpenAIError,))
    print("Reasoning effort:", args.reasoning_effort, flush=True)
    def query_model(query_args, prompt):
        messages = []
        for message in prompt:
            content = message["content"]
            if isinstance(content, list):
                parts = []
                for part in content:
                    if part.get("type") == "text":
                        parts.append({"type": "input_text", "text": part["text"]})
                    elif part.get("type") == "image_url":
                        parts.append({"type": "input_image", "image_url": part["image_url"]["url"]})
                    else:
                        raise ValueError("Unsupported prompt content type")
                content = parts
            messages.append({"role": message["role"], "content": content})
        def request_response():
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
        return {"content": response.output_text, "reasoning": None}
    os.environ["CAPX_GRASP_BACKEND"] = args.grasp_backend
    print("Grasp backend:", args.grasp_backend)
    os.environ["CUDA_VISIBLE_DEVICES"] = "3"
    os.environ["MUJOCO_EGL_DEVICE_ID"] = "3"
    os.environ["CAPX_LIBERO_SAM3_TEXT_ONLY"] = "0"
    print("LIBERO perception: SAM3 text segmentation; local Molmo disabled"
          if os.environ["CAPX_LIBERO_SAM3_TEXT_ONLY"] == "1"
          else "LIBERO perception: local Molmo + SAM3")
    import capx.llm.client as llm
    # Register this exact account model ID so cap-x actually captures feedback images.
    if args.model not in llm.VLM_MODELS:
        llm.VLM_MODELS.append(args.model)
    import capx.envs.trial as trial
    original_multiturn = trial._handle_multi_turn_step
    multiturn_signature = inspect.signature(original_multiturn)
    def handle_multiturn(*call_args, **call_kwargs):
        bound = multiturn_signature.bind(*call_args, **call_kwargs)
        completed = bool(bound.arguments["info_step"].get("task_completed", False))
        bound.arguments["multi_turn_prompt"] += (
            "\nAuthoritative environment success checker: Task Completed=" + str(completed)
            + "\nIf Task Completed is False, do not claim success or answer FINISH merely because "
              "there were no Python errors. Inspect the attached current image and respond with "
              "REGENERATE followed by corrective executable code. Answer FINISH when the checker is True."
        )
        return original_multiturn(*bound.args, **bound.kwargs)
    trial._handle_multi_turn_step = handle_multiturn
    llm.query_model = query_model
    trial._query_model = query_model
    from capx.envs.launch import LaunchArgs, main as launch
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
    config_path = Path(args.config_path).resolve()
    print("Prompt profile:", args.prompt_profile)
    if args.prompt_profile == "subtasks":
        import yaml
        import uuid
        config = yaml.safe_load(config_path.read_text())
        profile_path = ROOT / "env_configs/libero/subtask_prompt.yaml"
        profile = yaml.safe_load(profile_path.read_text())
        for field in ("prompt", "multi_turn_prompt"):
            config["env"]["cfg"][field] = profile[field]
        config_dir = ROOT / ".setup/prompt_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        generated_path = config_dir / (config_path.stem + "_subtasks_" + uuid.uuid4().hex + ".yaml")
        generated_path.write_text(yaml.safe_dump(config, sort_keys=False))
        print("Original config:", config_path)
        print("Effective config:", generated_path)
        config_path = generated_path
    launch(LaunchArgs(
        config_path=str(config_path),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        total_trials=1,
        num_workers=1,
        record_video=True,
        use_visual_feedback=True,
        use_img_differencing=False,
        use_video_differencing=False,
        use_parallel_ensemble=False,
        use_multimodel=False,
        output_dir=args.output_dir or str(ROOT / "outputs" / ("libero_spatial_0_openai_api_" + datetime.now().strftime("%Y%m%d_%H%M%S"))),
    ))

if __name__ == "__main__":
    main()
