# CAP-X fork: agent接手入口

本仓库是capgym/cap-x的修改版，官方基础提交为
`53e9966d7a8e2fa7494676772bccc35280f5c0ed`。
先读 `docs/local_changes.md`，再读官方README中的依赖和运行说明。

包含CAP-X源码、配置、测试、A800部署脚本和本地依赖源码。
视频、轨迹训练数据、模型权重、API密钥和已安装环境不在仓库中。
π0.5训练/评测适配在独立仓库：
https://github.com/Xverse-wsy/vla_recovery_self_evolving 。
WCM/π0.5共享环境接管控制器在A800的CAP-X仓库外：
`/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/wcm_pi05_monitor/hybrid/`，
未随本仓库上传，不能只clone本仓库就认定完整混合pipeline已部署。

关键文件：

- `capx/integrations/franka/libero.py`：TCP约定、Molmo开关、抓取后端、候选IK筛选。
- `capx/envs/simulators/libero.py`：TCP观测、单次关节运动默认200控制步。
- `capx/envs/trial.py`：多轮代码生成默认20轮。
- `capx/integrations/vision/graspgen.py`、`capx/serving/launch_graspgen_server.py`：GraspGen接口/服务。
- `capx/llm/api_pause.py`、`docs/api_pause.md`：API重试、阻塞、人工恢复。
- `.setup/run_openai_libero.py`：Responses入口、OPENAI_BASE_URL、prompt与思考强度；
  当前还有硬编码GPU和感知开关，启动前必须检查。
- `env_configs/libero/`：原版任务配置及另存的子任务prompt。
- `.setup/`：实际A800部署记录，包含机器绝对路径、GPU号、CUDA架构；不是已验证
  的跨机器一键安装包。安装前按 `docs/local_changes.md` 修改机器相关设置。

用户只要求检查/部署/上传时，不启动长评测、付费API或训练，不kill他人进程。
密钥通过环境变量/私有文件提供，不写入跟踪文件。任务成功以LIBERO判定为准，
不能以“程序没报错”代替。候选IK可达性不保证整个机械臂运动过程无碰撞。
按改动范围验证，准确报告实际验证范围；不能把源码同步写成新机器运行已通过。
