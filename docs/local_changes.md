# CAP-X修改版：部署和运行说明

官方基础提交：`53e9966d7a8e2fa7494676772bccc35280f5c0ed`。
上传前与A800的 `/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x` 同步过源码。

## 主要改动

| 功能 | 内容 |
| --- | --- |
| TCP | 去掉观测额外107mm平移；Franka手部/TCP偏移97mm |
| 执行预算 | 单次关节运动默认200控制步，代码生成默认20轮 |
| GraspGen | 可选抓取后端，抓取/预抓取IK候选筛选；不是全程无碰撞保证 |
| Molmo | CAPX_LIBERO_SAM3_TEXT_ONLY=1允许SAM3文字分割并跳过Molmo |
| Prompt | 新增子任务版，保留原版任务配置 |
| API | OPENAI_BASE_URL、medium思考强度；失败重试3次后阻塞，人工恢复 |

详见 `docs/graspgen.md`、`docs/api_pause.md`、`docs/subtask_prompt.md`。

## Clone与环境

```bash
git clone --recurse-submodules https://github.com/Xverse-wsy/real_world_rsi.git
cd real_world_rsi
```

官方子模块版本由gitlink固定。额外GraspGen直接放在
`capx/third_party/GraspGen/`，来源提交为
`2dd8852e1be60f5f9d277fafcc621835cdf59110`，保留原许可证。
`.setup/vendor/pyroki`与`.setup/vendor/jaxls`保留A800运行源码，原始archive提交分别为
`95afccc22658c461ab1042a048ae4e9c24bc2a47`、
`6fe7cf9d56223736b2c0272d080ec7346203c648`；见 `.setup/prepare_gitdeps.sh`。

主LIBERO环境与GraspGen是独立环境，A800分别使用Python3.12、3.10。
安装入口为 `.setup/install.sh`、`.setup/install_packages.sh`、
`.setup/setup_graspgen.sh`；固定依赖见 `uv.lock`、`.setup/requirements.lock.txt`。
这些是实际A800部署脚本，迁移前须检查：

1. `.setup/*.sh`的 `cd /home/wenchaoxu/.../cap-x`，换成本机仓库路径。
2. `.setup/env.sh`中的缓存、LIBERO_CONFIG_PATH、Node目录及GPU/EGL号。
3. `.setup/requirements.local.txt`中的源码绝对路径。
4. `.setup/setup_graspgen.sh`中的CUDA_HOME及TORCH_CUDA_ARCH_LIST；A800的8.0
   不能原样当作H100编译目标。不要混装两个环境。
5. `.setup/run_openai_libero.py`当前显式设置GPU3及
   `CAPX_LIBERO_SAM3_TEXT_ONLY=0`，会覆盖shell同名变量；改设备/感知模式须改这些行。
6. `.setup/run_medium_one.sh`引用A800私有CLIProxyAPI环境文件，新机自行配置
   OPENAI_API_KEY与可选OPENAI_BASE_URL，密钥不在仓库中。

模型权重与LIBERO场景资源需另备。`.setup/README.md`是2026-10-14历史安装记录，
不能据其中“服务已启动”等文字认定新机器已就绪。源代码上传未验证新机完整安装。

## 单轨迹入口

先准备资源与服务。A800使用SAM3 8114、Pyroki 8116、GraspGen 8117、Molmo2-8B
8122，实际端点须核对当前配置。完成上述路径/GPU适配后：

```bash
source .venv-libero/bin/activate
# OPENAI_API_KEY从本机安全环境加载；官方API可省略OPENAI_BASE_URL。
export OPENAI_BASE_URL='https://your-compatible-endpoint/v1'
python .setup/run_openai_libero.py \
  --model YOUR_MODEL_ID \
  --reasoning-effort medium \
  --prompt-profile original \
  --grasp-backend graspgen \
  --config-path env_configs/libero/franka_libero_spatial_0.yaml
```

入口默认prompt是subtasks，复现原版须显式传original。API阻塞后按日志目录使用
`capx/llm/api_pause.py resume`；仅原进程仍存活时能保持原场景继续执行。

π0.5训练/评测是独立项目：
https://github.com/Xverse-wsy/vla_recovery_self_evolving 。
WCM接管控制器在A800的CAP-X目录外，未包含在本仓库。
此次仅做源码/语法/Git检查，未为上传启动训练、仿真或付费API请求。
