# API 故障暂停与人工恢复

适用于 A800 的 `.setup/run_openai_libero.py` 和 `wcm_pi05_monitor/hybrid` CAP-X 接管入口。

每个待执行 API 请求最多先尝试四次：首次请求，加三次重试，间隔 5、15、30 秒。关闭 OpenAI SDK 的隐式重试，避免实际调用次数叠加。请求失败、空响应或未完成响应不会执行代码。

全部失败后，原进程停在同一请求中，保留仿真环境、物体/机器人状态、对话和 Python 执行上下文。不会 reset、重跑已执行代码、跳到下一条轨迹，也不会交回 pi0.5。等待时没有后台自动探测 API；修复额度或代理账号后手动恢复，重新尝试相同请求。恢复后仍失败则再次进入等待。

API 请求、重试和人工等待不消耗轨迹/恢复的墙钟执行预算；单次 HTTP 超时仍然有效。环境动作步数上限不变。恢复前后检查仿真状态与控制步数；检查失败时禁止继续执行。

## 操作

日志中会显示 `API pause control directory` 或 `API PAUSED` 及目录路径。单独 CAP-X 的控制目录在 `.setup/api_control/capx_<PID>_<时间>/`；混合执行在本条轨迹 CAP-X 输出下的 `api_control/`。

在 A800 新终端中运行，替换最后的目录参数：

```bash
cd /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
.venv-libero/bin/python capx/llm/api_pause.py status /日志中的控制目录
.venv-libero/bin/python capx/llm/api_pause.py resume /日志中的控制目录
```

`resume` 不会重启进程或环境。修复 CLIProxyAPI 的上游额度/账号后可直接发出恢复信号。原进程继承的环境变量不会随其他终端中的 `export` 改变；混合入口使用 `--api-key-file` 时会在下一次尝试重新读文件。

key 文件暂时不可读、为空或编码无效时，同样按请求故障重试并暂停，修复文件后再恢复。恢复文件内容异常或令牌过期时忽略该信号，继续保持暂停。

每次暂停都有独立令牌，旧的恢复信号不能解除下一次暂停。`events.jsonl` 记录尝试次数、HTTP 状态和上游错误码，不记录 API key、请求正文或错误正文。API 超时可能意味着服务端已处理请求，重试可能产生额外上游费用；客户端只执行一次获得的成功响应，已执行的机器人代码块不重放。

仅保证原进程持续存活时的继续执行。退出 screen 中的程序、杀进程、服务器重启后不能靠此机制重建场景；要从 screen 离开请使用 Ctrl+A、D。

## 验证

`tests/test_api_pause.py` 验证三次重试后阻塞、手动恢复、原请求不变、过期恢复信号被忽略、日志不包含异常正文以及 POSIX 轨迹计时暂停。

`hybrid/check_api_pause.py` 使用真实 LIBERO 与本地模拟 Responses 服务：先执行一个代码块，再注入连续四次额度不足；等待 33 秒（超过 30 秒恢复执行预算）后核对状态和步数不变，再发人工恢复信号。检查继续使用原请求、前一代码块未重放、共享动作预算依然生效。此验证不调用外部模型、不用于统计任务成功率。

`tests/test_hybrid_api_pause.py` 验证父进程正常执行路径、等待时间不消耗执行预算、恢复后执行超时仍生效、子进程退出可被检测，以及暂停期间禁止动作调用和提前返回。

`cliproxy_a800_setup/check_normal_execution.py` 使用真实 CAP-X 单轨迹入口和本地固定 API 响应，核对改动前后相同 8 个控制步的请求内容与仿真状态是否一致。它只检查执行逻辑，不用于评估任务成功率。
