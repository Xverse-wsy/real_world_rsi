# LIBERO subtask prompt

On A800, `.setup/run_openai_libero.py` now defaults to
`--prompt-profile subtasks`. This loads `env_configs/libero/subtask_prompt.yaml`
and replaces only `env.cfg.prompt` and `env.cfg.multi_turn_prompt` in a generated
copy of the selected config. Original configs and historical outputs are preserved.
The generated config is retained under `.setup/prompt_configs`, and its path is
printed at launch.

The prompt asks for an observable subtask plan, one subtask per response,
verification before dependent actions, and renewed localization/grasp sampling
after an object falls or moves. These are model instructions, not enforced
execution-state checks.

To restore the previous prompt behavior, append this argument to the existing
OpenAI runner command:

```bash
--prompt-profile original
```

This uses the selected input config's unchanged prompts. The existing runtime
success-checker feedback remains active, as it was before this change.

A800 pre-change backups (runner, original base config, extracted prompt strings):

```text
/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.setup/backups/prompt_before_subtasks_20261015_155705/
```

No simulation or paid API trial was started for this change. Validation covered
Python syntax, prompt formatting fields, unchanged original config, and CLI help.
